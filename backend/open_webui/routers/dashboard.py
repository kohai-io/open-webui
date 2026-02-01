"""
Admin Dashboard API Router
Provides statistics and analytics for the admin dashboard page.
"""

import logging
import time
from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from datetime import datetime, timezone

from open_webui.models.users import Users
from open_webui.models.chats import Chats
from open_webui.models.feedbacks import Feedbacks
from open_webui.models.files import Files
from open_webui.models.models import Models
from open_webui.models.groups import Groups
from open_webui.models.knowledge import Knowledges

from open_webui.socket.main import get_active_user_ids
from open_webui.utils.auth import get_admin_user
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

router = APIRouter()


class DashboardStatsResponse(BaseModel):
    users: dict
    chats: dict
    models: dict
    tokens: dict
    files: dict
    groups: dict
    feedback: dict
    knowledge: dict


def calc_comparison(current: float, previous: float) -> dict:
    """Calculate delta and percentage change between current and previous period"""
    delta = current - previous
    pct_change = (
        (delta / previous * 100)
        if previous > 0
        else (100.0 if current > 0 else 0.0)
    )
    return {
        "current": current,
        "previous": previous,
        "delta": delta,
        "delta_pct": round(pct_change, 1),
    }


async def fetch_litellm_spend(base_url: str, master_key: str, user_ids: list) -> dict:
    """
    Fetch spend data from LiteLLM for given user IDs.
    Tries /customer/info first (end_user_id tracking), then falls back to /user/info.
    Returns dict mapping user_id -> {spend: float, ...}
    """
    cost_data = {}
    
    if not base_url or not master_key:
        return cost_data
    
    # Strip trailing slash and /v1 suffix (management API is at root, not /v1)
    base_url = base_url.rstrip('/')
    if base_url.endswith('/v1'):
        base_url = base_url[:-3]
    
    log.info(f"[DASHBOARD] Fetching spend for {len(user_ids)} users from {base_url}")
    
    headers = {"Authorization": f"Bearer {master_key}"}
    
    async with aiohttp.ClientSession() as session:
        for user_id in user_ids:
            try:
                # Try /customer/info first (for end_user_id tracking)
                async with session.get(
                    f"{base_url}/customer/info",
                    params={"end_user_id": user_id},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        spend = data.get("spend", 0.0)
                        log.debug(f"[DASHBOARD] /customer/info for {user_id[:8]}...: spend={spend}")
                        cost_data[user_id] = {
                            "spend": spend,
                            "max_budget": data.get("max_budget"),
                        }
                        continue
                    elif response.status == 500:
                        # 500 might mean user not found in customer tracking, try /user/info
                        log.debug(f"[DASHBOARD] /customer/info returned 500 for {user_id}, trying /user/info")
                    else:
                        log.debug(f"[DASHBOARD] /customer/info returned {response.status} for {user_id}")
                
                # Fallback: Try /user/info (for user_id on keys)
                async with session.get(
                    f"{base_url}/user/info",
                    params={"user_id": user_id},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        user_info = data.get("user_info", {})
                        spend = user_info.get("spend", 0.0) if isinstance(user_info, dict) else 0.0
                        log.debug(f"[DASHBOARD] /user/info for {user_id[:8]}...: spend={spend}")
                        cost_data[user_id] = {
                            "spend": spend,
                            "max_budget": user_info.get("max_budget") if isinstance(user_info, dict) else None,
                        }
                    else:
                        log.debug(f"[DASHBOARD] Both LiteLLM endpoints failed for {user_id}")
            except Exception as e:
                log.warning(f"[DASHBOARD] Failed to fetch LiteLLM spend for {user_id}: {e}")
                continue
    
    log.info(f"[DASHBOARD] Retrieved spend data for {len(cost_data)} users")
    
    return cost_data


@router.get("/stats")
async def get_dashboard_stats(
    request: Request,
    user=Depends(get_admin_user),
) -> dict:
    """
    Get comprehensive dashboard statistics for admin users.
    Returns user, chat, model, token, file, group, feedback, and knowledge stats.
    """
    
    now = int(time.time())
    
    # Time boundaries
    day_ago = now - 86400
    week_ago = now - 604800
    month_ago = now - 2592000
    quarter_ago = now - (86400 * 90)
    half_year_ago = now - (86400 * 180)
    year_ago = now - (86400 * 365)
    
    # Previous period boundaries
    two_days_ago = now - (86400 * 2)
    two_weeks_ago = now - (604800 * 2)
    two_months_ago = now - (2592000 * 2)
    two_quarters_ago = now - (86400 * 180)
    one_year_ago = now - (86400 * 365)
    two_years_ago = now - (86400 * 730)
    
    # ===== USER STATS =====
    all_users_data = Users.get_users()
    all_users = all_users_data.get("users", [])
    total_users = all_users_data.get("total", 0)
    
    # User registration metrics
    users_today = sum(1 for u in all_users if u.created_at >= day_ago)
    users_this_week = sum(1 for u in all_users if u.created_at >= week_ago)
    users_this_month = sum(1 for u in all_users if u.created_at >= month_ago)
    users_this_quarter = sum(1 for u in all_users if u.created_at >= quarter_ago)
    users_this_half_year = sum(1 for u in all_users if u.created_at >= half_year_ago)
    users_this_year = sum(1 for u in all_users if u.created_at >= year_ago)
    
    # Active users
    active_last_24h = sum(1 for u in all_users if u.last_active_at >= day_ago)
    active_last_week = sum(1 for u in all_users if u.last_active_at >= week_ago)
    active_last_month = sum(1 for u in all_users if u.last_active_at >= month_ago)
    active_all_time = sum(1 for u in all_users if u.last_active_at > 0)
    active_last_quarter = sum(1 for u in all_users if u.last_active_at >= quarter_ago)
    active_last_half_year = sum(1 for u in all_users if u.last_active_at >= half_year_ago)
    active_last_year = sum(1 for u in all_users if u.last_active_at >= year_ago)
    
    # Active now
    active_now_count = 0
    try:
        active_user_ids = get_active_user_ids()
        active_now_count = len(active_user_ids)
    except:
        pass
    
    # User roles
    admin_count = sum(1 for u in all_users if u.role == "admin")
    user_count = sum(1 for u in all_users if u.role == "user")
    pending_count = sum(1 for u in all_users if u.role == "pending")
    
    # Previous period metrics
    users_previous_day = sum(1 for u in all_users if two_days_ago <= u.created_at < day_ago)
    users_previous_week = sum(1 for u in all_users if two_weeks_ago <= u.created_at < week_ago)
    users_previous_month = sum(1 for u in all_users if two_months_ago <= u.created_at < month_ago)
    
    active_previous_day = sum(1 for u in all_users if two_days_ago <= u.last_active_at < day_ago)
    active_previous_week = sum(1 for u in all_users if two_weeks_ago <= u.last_active_at < week_ago)
    active_previous_month = sum(1 for u in all_users if two_months_ago <= u.last_active_at < month_ago)
    
    # ===== CHAT STATS =====
    all_chats = Chats.get_chats()
    total_chats = len(all_chats)
    
    # Build user_id → chats map
    user_chats_lookup = {}
    for chat in all_chats:
        uid = chat.user_id
        if uid not in user_chats_lookup:
            user_chats_lookup[uid] = []
        user_chats_lookup[uid].append(chat)
    
    inactive_users = sum(1 for u in all_users if u.id not in user_chats_lookup)
    
    total_chats_archived = sum(1 for c in all_chats if c.archived)
    total_chats_pinned = sum(1 for c in all_chats if c.pinned)
    chat_activity_today = sum(1 for c in all_chats if c.updated_at >= day_ago)
    chat_activity_week = sum(1 for c in all_chats if c.updated_at >= week_ago)
    chat_activity_month = sum(1 for c in all_chats if c.updated_at >= month_ago)
    
    # Previous period chat activity
    chat_activity_previous_day = sum(1 for c in all_chats if two_days_ago <= c.updated_at < day_ago)
    chat_activity_previous_week = sum(1 for c in all_chats if two_weeks_ago <= c.updated_at < week_ago)
    chat_activity_previous_month = sum(1 for c in all_chats if two_months_ago <= c.updated_at < month_ago)
    
    # ===== MODEL & TOKEN STATS =====
    model_usage = {}
    model_prompt_tokens = {}
    model_completion_tokens = {}
    total_prompt_tokens = 0
    total_completion_tokens = 0
    
    for chat in all_chats:
        chat_data = chat.chat if hasattr(chat, 'chat') else {}
        if isinstance(chat_data, dict):
            messages = chat_data.get("messages", [])
            for msg in messages:
                if isinstance(msg, dict):
                    model_id = msg.get("model") or msg.get("modelId")
                    if model_id:
                        model_usage[model_id] = model_usage.get(model_id, 0) + 1
                    
                    if "usage" in msg and isinstance(msg["usage"], dict):
                        usage = msg["usage"]
                        prompt_tokens = usage.get("prompt_tokens", 0)
                        completion_tokens = usage.get("completion_tokens", 0)
                        
                        total_prompt_tokens += prompt_tokens
                        total_completion_tokens += completion_tokens
                        
                        if model_id:
                            model_prompt_tokens[model_id] = model_prompt_tokens.get(model_id, 0) + prompt_tokens
                            model_completion_tokens[model_id] = model_completion_tokens.get(model_id, 0) + completion_tokens
    
    total_tokens = total_prompt_tokens + total_completion_tokens
    
    # Model metadata
    model_metadata = {}
    model_config_stats = {}
    try:
        all_db_models = Models.get_all_models()
        model_metadata = {m.id: m for m in all_db_models}
        
        hidden_models = [m for m in all_db_models if m.meta and getattr(m.meta, 'hidden', False)]
        visible_models = [m for m in all_db_models if not (m.meta and getattr(m.meta, 'hidden', False))]
        models_with_base = [m for m in all_db_models if m.base_model_id is not None]
        base_models = [m for m in all_db_models if m.base_model_id is None]
        
        model_config_stats = {
            'total_workspace_models': len(all_db_models),
            'hidden_models': len(hidden_models),
            'visible_models': len(visible_models),
            'custom_modelfiles': len(models_with_base),
            'base_models': len(base_models),
        }
    except Exception as e:
        log.warning(f"[DASHBOARD] Failed to fetch workspace models: {e}")
    
    # Build enhanced model lists
    all_models_enhanced = []
    for model_id, count in sorted(model_usage.items(), key=lambda x: x[1], reverse=True):
        model_meta = model_metadata.get(model_id)
        display_name = model_meta.name if model_meta else model_id
        is_hidden = getattr(model_meta.meta, 'hidden', False) if (model_meta and model_meta.meta) else False
        is_workspace = model_id in model_metadata
        is_modelfile = model_meta.base_model_id is not None if model_meta else False
        
        all_models_enhanced.append({
            'id': model_id,
            'name': display_name,
            'messages': count,
            'prompt_tokens': model_prompt_tokens.get(model_id, 0),
            'completion_tokens': model_completion_tokens.get(model_id, 0),
            'total_tokens': model_prompt_tokens.get(model_id, 0) + model_completion_tokens.get(model_id, 0),
            'is_workspace': is_workspace,
            'is_modelfile': is_modelfile,
            'is_hidden': is_hidden,
        })
    
    top_models = all_models_enhanced[:10]
    
    # ===== USER ACTIVITY WITH TOKENS =====
    user_chat_data = []
    for user in all_users:
        chats = user_chats_lookup.get(user.id, [])
        user_prompt_tokens = 0
        user_completion_tokens = 0
        
        for chat in chats:
            chat_data = chat.chat if hasattr(chat, 'chat') else {}
            if isinstance(chat_data, dict):
                messages = chat_data.get("messages", [])
                for msg in messages:
                    if isinstance(msg, dict) and "usage" in msg:
                        usage = msg.get("usage", {})
                        if isinstance(usage, dict):
                            user_prompt_tokens += usage.get("prompt_tokens", 0)
                            user_completion_tokens += usage.get("completion_tokens", 0)
        
        user_chat_data.append({
            'name': user.name,
            'chats': len(chats),
            'user_id': user.id,
            'prompt_tokens': user_prompt_tokens,
            'completion_tokens': user_completion_tokens,
            'total_tokens': user_prompt_tokens + user_completion_tokens,
            'created_at': user.created_at,
            'last_active_at': user.last_active_at
        })
    
    user_chat_data.sort(key=lambda x: x['chats'], reverse=True)
    top_users_by_chats = user_chat_data[:10]
    
    top_users_by_tokens = sorted(
        [u for u in user_chat_data if u['total_tokens'] > 0],
        key=lambda x: x['total_tokens'],
        reverse=True
    )[:10]
    
    # ===== FILE STATS =====
    all_files = Files.get_files()
    total_files = len(all_files)
    total_size_bytes = sum(f.meta.get("size", 0) if f.meta else 0 for f in all_files)
    total_size_gb = total_size_bytes / (1024 * 1024 * 1024)
    files_today = sum(1 for f in all_files if f.created_at >= day_ago)
    files_this_week = sum(1 for f in all_files if f.created_at >= week_ago)
    
    file_types = {}
    for f in all_files:
        content_type = f.meta.get("content_type", "unknown") if f.meta else "unknown"
        file_types[content_type] = file_types.get(content_type, 0) + 1
    top_file_types = sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # ===== GROUP STATS =====
    all_groups = Groups.get_groups()
    total_groups = len(all_groups)
    total_group_members = sum(len(g.user_ids) if g.user_ids else 0 for g in all_groups)
    
    groups_with_members = [
        {"name": g.name, "members": len(g.user_ids) if g.user_ids else 0}
        for g in all_groups
    ]
    groups_with_members.sort(key=lambda x: x['members'], reverse=True)
    top_groups = groups_with_members[:10]
    
    # ===== FEEDBACK STATS =====
    all_feedbacks = Feedbacks.get_all_feedbacks()
    total_feedbacks = len(all_feedbacks)
    feedbacks_today = sum(1 for f in all_feedbacks if f.created_at >= day_ago)
    feedbacks_this_week = sum(1 for f in all_feedbacks if f.created_at >= week_ago)
    
    rating_counts = {str(i): 0 for i in range(1, 11)}
    for f in all_feedbacks:
        if f.data and isinstance(f.data, dict):
            details = f.data.get('details')
            if details and isinstance(details, dict):
                rating = details.get('rating')
                if rating is not None:
                    try:
                        rating_int = int(rating)
                        if 1 <= rating_int <= 10:
                            rating_counts[str(rating_int)] += 1
                    except (ValueError, TypeError):
                        pass
    
    # ===== KNOWLEDGE BASE STATS =====
    all_knowledge_bases = Knowledges.get_knowledge_bases()
    total_knowledge_bases = len(all_knowledge_bases)
    knowledge_today = sum(1 for kb in all_knowledge_bases if kb.created_at >= day_ago)
    knowledge_this_week = sum(1 for kb in all_knowledge_bases if kb.created_at >= week_ago)
    
    total_kb_documents = 0
    for kb in all_knowledge_bases:
        if kb.data and isinstance(kb.data, dict):
            file_ids = kb.data.get('file_ids', [])
            if isinstance(file_ids, list):
                total_kb_documents += len(file_ids)
    
    # ===== LITELLM SPEND DATA =====
    spend_data = {}
    total_platform_spend = 0.0
    users_with_spend = 0
    top_users_by_spend = []
    litellm_enabled = request.app.state.config.ENABLE_LITELLM_SPEND
    
    log.info(f"[DASHBOARD] LiteLLM enabled: {litellm_enabled}")
    
    if litellm_enabled:
        litellm_base_url = request.app.state.config.LITELLM_BASE_URL
        litellm_master_key = request.app.state.config.LITELLM_MASTER_KEY
        
        log.info(f"[DASHBOARD] LiteLLM URL: {litellm_base_url}, Key set: {bool(litellm_master_key)}")
        
        if litellm_base_url and litellm_master_key:
            all_user_ids = [u.id for u in all_users]
            spend_data = await fetch_litellm_spend(litellm_base_url, litellm_master_key, all_user_ids)
            
            for user_id, cost_info in spend_data.items():
                spend = cost_info.get('spend', 0.0)
                total_platform_spend += spend
                if spend > 0:
                    users_with_spend += 1
            
            # Build top users by spend
            users_with_spend_data = []
            for u in user_chat_data:
                user_spend = spend_data.get(u['user_id'], {}).get('spend', 0.0)
                if user_spend > 0:
                    users_with_spend_data.append({
                        'name': u['name'],
                        'user_id': u['user_id'],
                        'spend': round(user_spend, 2),
                        'chats': u['chats'],
                    })
            
            top_users_by_spend = sorted(
                users_with_spend_data,
                key=lambda x: x['spend'],
                reverse=True
            )[:10]
    
    # ===== BUILD RESPONSE =====
    return {
        "users": {
            "total": total_users,
            "active_now": active_now_count,
            "inactive": inactive_users,
            "roles": {
                "admin": admin_count,
                "user": user_count,
                "pending": pending_count,
            },
            "registrations": {
                "today": users_today,
                "week": users_this_week,
                "month": users_this_month,
                "quarter": users_this_quarter,
                "half_year": users_this_half_year,
                "year": users_this_year,
            },
            "active": {
                "day": active_last_24h,
                "week": active_last_week,
                "month": active_last_month,
                "quarter": active_last_quarter,
                "half_year": active_last_half_year,
                "year": active_last_year,
                "all_time": active_all_time,
            },
            "comparison": {
                "registrations": {
                    "day": calc_comparison(users_today, users_previous_day),
                    "week": calc_comparison(users_this_week, users_previous_week),
                    "month": calc_comparison(users_this_month, users_previous_month),
                },
                "active": {
                    "day": calc_comparison(active_last_24h, active_previous_day),
                    "week": calc_comparison(active_last_week, active_previous_week),
                    "month": calc_comparison(active_last_month, active_previous_month),
                },
            },
            "top_by_chats": top_users_by_chats,
            "top_by_tokens": top_users_by_tokens,
        },
        "chats": {
            "total": total_chats,
            "archived": total_chats_archived,
            "pinned": total_chats_pinned,
            "activity": {
                "today": chat_activity_today,
                "week": chat_activity_week,
                "month": chat_activity_month,
            },
            "comparison": {
                "day": calc_comparison(chat_activity_today, chat_activity_previous_day),
                "week": calc_comparison(chat_activity_week, chat_activity_previous_week),
                "month": calc_comparison(chat_activity_month, chat_activity_previous_month),
            },
        },
        "models": {
            "total_used": len(model_usage),
            "config": model_config_stats,
            "top_models": top_models,
        },
        "tokens": {
            "total": total_tokens,
            "prompt": total_prompt_tokens,
            "completion": total_completion_tokens,
        },
        "files": {
            "total": total_files,
            "size_bytes": total_size_bytes,
            "size_gb": round(total_size_gb, 2),
            "today": files_today,
            "week": files_this_week,
            "top_types": [{"type": t[0], "count": t[1]} for t in top_file_types],
        },
        "groups": {
            "total": total_groups,
            "total_members": total_group_members,
            "top_groups": top_groups,
        },
        "feedback": {
            "total": total_feedbacks,
            "today": feedbacks_today,
            "week": feedbacks_this_week,
            "ratings": rating_counts,
        },
        "knowledge": {
            "total_bases": total_knowledge_bases,
            "total_documents": total_kb_documents,
            "today": knowledge_today,
            "week": knowledge_this_week,
        },
        "spend": {
            "enabled": request.app.state.config.ENABLE_LITELLM_SPEND,
            "total": round(total_platform_spend, 2),
            "users_with_spend": users_with_spend,
            "top_users": top_users_by_spend,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/users")
async def get_dashboard_users(
    request: Request,
    user=Depends(get_admin_user),
    page: int = 1,
    limit: int = 50,
    sort_by: str = "chats",
    order: str = "desc",
) -> dict:
    """
    Get paginated list of users with their stats for drill-down view.
    """
    now = int(time.time())
    day_ago = now - 86400
    week_ago = now - 604800
    month_ago = now - 2592000
    
    # Get all users
    all_users_data = Users.get_users()
    all_users = all_users_data.get("users", [])
    
    # Get all chats for stats
    all_chats = Chats.get_chats()
    
    # Fetch LiteLLM spend data if enabled
    spend_data = {}
    litellm_enabled = request.app.state.config.ENABLE_LITELLM_SPEND
    if litellm_enabled:
        litellm_base_url = request.app.state.config.LITELLM_BASE_URL
        litellm_master_key = request.app.state.config.LITELLM_MASTER_KEY
        if litellm_base_url and litellm_master_key:
            all_user_ids = [u.id for u in all_users]
            spend_data = await fetch_litellm_spend(litellm_base_url, litellm_master_key, all_user_ids)
    
    # Build user stats
    user_stats = []
    for u in all_users:
        user_chats = [c for c in all_chats if c.user_id == u.id]
        total_chats = len(user_chats)
        
        # Count messages and tokens
        total_messages = 0
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        models_used = {}
        
        for chat in user_chats:
            if chat.chat and "messages" in chat.chat:
                messages = chat.chat["messages"]
                total_messages += len(messages)
                for msg in messages:
                    if "usage" in msg:
                        usage = msg["usage"]
                        total_tokens += usage.get("total_tokens", 0)
                        input_tokens += usage.get("prompt_tokens", 0)
                        output_tokens += usage.get("completion_tokens", 0)
                    if msg.get("role") == "assistant" and "model" in msg:
                        model = msg["model"]
                        models_used[model] = models_used.get(model, 0) + 1
        
        # Recent activity
        chats_today = sum(1 for c in user_chats if c.created_at >= day_ago)
        chats_week = sum(1 for c in user_chats if c.created_at >= week_ago)
        chats_month = sum(1 for c in user_chats if c.created_at >= month_ago)
        
        user_stats.append({
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at,
            "last_active_at": u.last_active_at,
            "chats": total_chats,
            "messages": total_messages,
            "tokens": total_tokens,
            "tokens_in": input_tokens,
            "tokens_out": output_tokens,
            "models_count": len(models_used),
            "spend": round(spend_data.get(u.id, {}).get("spend", 0.0), 2),
            "activity": {
                "today": chats_today,
                "week": chats_week,
                "month": chats_month,
            },
        })
    
    # Sort
    reverse = order == "desc"
    if sort_by == "chats":
        user_stats.sort(key=lambda x: x["chats"], reverse=reverse)
    elif sort_by == "messages":
        user_stats.sort(key=lambda x: x["messages"], reverse=reverse)
    elif sort_by == "tokens":
        user_stats.sort(key=lambda x: x["tokens"], reverse=reverse)
    elif sort_by == "name":
        user_stats.sort(key=lambda x: x["name"].lower(), reverse=reverse)
    elif sort_by == "last_active":
        user_stats.sort(key=lambda x: x["last_active_at"], reverse=reverse)
    elif sort_by == "created":
        user_stats.sort(key=lambda x: x["created_at"], reverse=reverse)
    elif sort_by == "tokens_in":
        user_stats.sort(key=lambda x: x["tokens_in"], reverse=reverse)
    elif sort_by == "tokens_out":
        user_stats.sort(key=lambda x: x["tokens_out"], reverse=reverse)
    elif sort_by == "spend":
        user_stats.sort(key=lambda x: x["spend"], reverse=reverse)
    
    # Paginate
    total = len(user_stats)
    start = (page - 1) * limit
    end = start + limit
    paginated = user_stats[start:end]
    
    return {
        "users": paginated,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/users/{user_id}")
async def get_dashboard_user_detail(
    request: Request,
    user_id: str,
    user=Depends(get_admin_user),
) -> dict:
    """
    Get detailed stats for a single user.
    """
    now = int(time.time())
    day_ago = now - 86400
    week_ago = now - 604800
    month_ago = now - 2592000
    quarter_ago = now - (86400 * 90)
    
    # Get user
    target_user = Users.get_user_by_id(user_id)
    if not target_user:
        return {"error": "User not found"}
    
    # Get user's chats
    user_chats = Chats.get_chats_by_user_id(user_id)
    total_chats = len(user_chats)
    
    # Analyze chats
    total_messages = 0
    total_tokens = 0
    input_tokens = 0
    output_tokens = 0
    models_used = {}
    recent_chats = []
    
    for chat in user_chats:
        chat_messages = 0
        chat_tokens = 0
        chat_models = set()
        
        if chat.chat and "messages" in chat.chat:
            messages = chat.chat["messages"]
            chat_messages = len(messages)
            total_messages += chat_messages
            
            for msg in messages:
                if "usage" in msg:
                    usage = msg["usage"]
                    tokens = usage.get("total_tokens", 0)
                    total_tokens += tokens
                    chat_tokens += tokens
                    input_tokens += usage.get("prompt_tokens", 0)
                    output_tokens += usage.get("completion_tokens", 0)
                
                if msg.get("role") == "assistant" and "model" in msg:
                    model = msg["model"]
                    chat_models.add(model)
                    models_used[model] = models_used.get(model, 0) + 1
        
        # Add to recent chats (last 20)
        if len(recent_chats) < 20:
            recent_chats.append({
                "id": chat.id,
                "title": chat.title or "Untitled",
                "created_at": chat.created_at,
                "updated_at": chat.updated_at,
                "messages": chat_messages,
                "tokens": chat_tokens,
                "models": list(chat_models),
                "archived": chat.archived,
                "pinned": chat.pinned,
            })
    
    # Sort recent chats by updated_at
    recent_chats.sort(key=lambda x: x["updated_at"], reverse=True)
    
    # Activity breakdown
    chats_today = sum(1 for c in user_chats if c.created_at >= day_ago)
    chats_week = sum(1 for c in user_chats if c.created_at >= week_ago)
    chats_month = sum(1 for c in user_chats if c.created_at >= month_ago)
    chats_quarter = sum(1 for c in user_chats if c.created_at >= quarter_ago)
    
    # Top models
    top_models = sorted(
        [{"name": k, "messages": v} for k, v in models_used.items()],
        key=lambda x: x["messages"],
        reverse=True
    )[:10]
    
    # Get user's files
    user_files = Files.get_files_by_user_id(user_id)
    total_file_size = sum(f.meta.get("size", 0) if f.meta else 0 for f in user_files)
    
    # Get user's feedbacks
    all_feedbacks = Feedbacks.get_feedbacks()
    user_feedbacks = [f for f in all_feedbacks if f.user_id == user_id]
    
    # LiteLLM spend
    spend = 0.0
    if request.app.state.config.ENABLE_LITELLM_SPEND:
        litellm_base_url = request.app.state.config.LITELLM_BASE_URL
        litellm_master_key = request.app.state.config.LITELLM_MASTER_KEY
        if litellm_base_url and litellm_master_key:
            spend_data = await fetch_litellm_spend(litellm_base_url, litellm_master_key, [user_id])
            spend = spend_data.get(user_id, {}).get("spend", 0.0)
    
    # Get user's groups
    all_groups = Groups.get_groups()
    user_groups = [g for g in all_groups if user_id in (g.user_ids or [])]
    
    return {
        "user": {
            "id": target_user.id,
            "name": target_user.name,
            "email": target_user.email,
            "role": target_user.role,
            "profile_image_url": target_user.profile_image_url,
            "created_at": target_user.created_at,
            "last_active_at": target_user.last_active_at,
        },
        "stats": {
            "chats": total_chats,
            "messages": total_messages,
            "tokens": {
                "total": total_tokens,
                "input": input_tokens,
                "output": output_tokens,
            },
            "files": len(user_files),
            "file_size": total_file_size,
            "feedbacks": len(user_feedbacks),
            "spend": round(spend, 2),
        },
        "activity": {
            "today": chats_today,
            "week": chats_week,
            "month": chats_month,
            "quarter": chats_quarter,
        },
        "models": top_models,
        "recent_chats": recent_chats,
        "groups": [{"id": g.id, "name": g.name} for g in user_groups],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/groups")
async def get_dashboard_groups(
    request: Request,
    user=Depends(get_admin_user),
    page: int = 1,
    limit: int = 50,
    sort_by: str = "members",
    order: str = "desc",
) -> dict:
    """
    Get paginated list of groups with their stats for drill-down view.
    """
    all_groups = Groups.get_groups()
    all_chats = Chats.get_chats()
    
    # Fetch LiteLLM spend data if enabled
    spend_data = {}
    litellm_enabled = request.app.state.config.ENABLE_LITELLM_SPEND
    if litellm_enabled:
        litellm_base_url = request.app.state.config.LITELLM_BASE_URL
        litellm_master_key = request.app.state.config.LITELLM_MASTER_KEY
        if litellm_base_url and litellm_master_key:
            # Get all unique member IDs across all groups
            all_member_ids = set()
            for g in all_groups:
                all_member_ids.update(g.user_ids or [])
            if all_member_ids:
                spend_data = await fetch_litellm_spend(litellm_base_url, litellm_master_key, list(all_member_ids))
    
    # Build group stats
    group_stats = []
    for g in all_groups:
        member_ids = g.user_ids or []
        member_count = len(member_ids)
        
        # Get chats for all members
        group_chats = [c for c in all_chats if c.user_id in member_ids]
        total_chats = len(group_chats)
        
        # Count messages and tokens
        total_messages = 0
        total_tokens = 0
        input_tokens = 0
        output_tokens = 0
        
        for chat in group_chats:
            if chat.chat and "messages" in chat.chat:
                messages = chat.chat["messages"]
                total_messages += len(messages)
                for msg in messages:
                    if "usage" in msg:
                        usage = msg["usage"]
                        total_tokens += usage.get("total_tokens", 0)
                        input_tokens += usage.get("prompt_tokens", 0)
                        output_tokens += usage.get("completion_tokens", 0)
        
        # Calculate group spend
        group_spend = sum(spend_data.get(uid, {}).get("spend", 0.0) for uid in member_ids)
        
        group_stats.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "members": member_count,
            "chats": total_chats,
            "messages": total_messages,
            "tokens": total_tokens,
            "tokens_in": input_tokens,
            "tokens_out": output_tokens,
            "spend": round(group_spend, 2),
            "created_at": g.created_at,
            "updated_at": g.updated_at,
        })
    
    # Sort
    reverse = order == "desc"
    if sort_by == "members":
        group_stats.sort(key=lambda x: x["members"], reverse=reverse)
    elif sort_by == "chats":
        group_stats.sort(key=lambda x: x["chats"], reverse=reverse)
    elif sort_by == "messages":
        group_stats.sort(key=lambda x: x["messages"], reverse=reverse)
    elif sort_by == "tokens":
        group_stats.sort(key=lambda x: x["tokens"], reverse=reverse)
    elif sort_by == "name":
        group_stats.sort(key=lambda x: x["name"].lower(), reverse=reverse)
    elif sort_by == "tokens_in":
        group_stats.sort(key=lambda x: x["tokens_in"], reverse=reverse)
    elif sort_by == "tokens_out":
        group_stats.sort(key=lambda x: x["tokens_out"], reverse=reverse)
    elif sort_by == "spend":
        group_stats.sort(key=lambda x: x["spend"], reverse=reverse)
    
    # Paginate
    total = len(group_stats)
    start = (page - 1) * limit
    end = start + limit
    paginated = group_stats[start:end]
    
    return {
        "groups": paginated,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/groups/{group_id}")
async def get_dashboard_group_detail(
    request: Request,
    group_id: str,
    user=Depends(get_admin_user),
) -> dict:
    """
    Get detailed stats for a single group.
    """
    # Get group
    target_group = Groups.get_group_by_id(group_id)
    if not target_group:
        return {"error": "Group not found"}
    
    member_ids = target_group.user_ids or []
    
    # Get all members
    all_users_data = Users.get_users()
    all_users = all_users_data.get("users", [])
    members = [u for u in all_users if u.id in member_ids]
    
    # Get all chats
    all_chats = Chats.get_chats()
    group_chats = [c for c in all_chats if c.user_id in member_ids]
    
    # Aggregate stats
    total_messages = 0
    total_tokens = 0
    input_tokens = 0
    output_tokens = 0
    models_used = {}
    
    for chat in group_chats:
        if chat.chat and "messages" in chat.chat:
            messages = chat.chat["messages"]
            total_messages += len(messages)
            for msg in messages:
                if "usage" in msg:
                    usage = msg["usage"]
                    total_tokens += usage.get("total_tokens", 0)
                    input_tokens += usage.get("prompt_tokens", 0)
                    output_tokens += usage.get("completion_tokens", 0)
                if msg.get("role") == "assistant" and "model" in msg:
                    model = msg["model"]
                    models_used[model] = models_used.get(model, 0) + 1
    
    # Top models
    top_models = sorted(
        [{"name": k, "messages": v} for k, v in models_used.items()],
        key=lambda x: x["messages"],
        reverse=True
    )[:10]
    
    # Member stats
    member_stats = []
    for m in members:
        member_chats = [c for c in group_chats if c.user_id == m.id]
        m_messages = 0
        m_tokens = 0
        for chat in member_chats:
            if chat.chat and "messages" in chat.chat:
                m_messages += len(chat.chat["messages"])
                for msg in chat.chat["messages"]:
                    if "usage" in msg:
                        m_tokens += msg["usage"].get("total_tokens", 0)
        
        member_stats.append({
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "role": m.role,
            "chats": len(member_chats),
            "messages": m_messages,
            "tokens": m_tokens,
            "last_active_at": m.last_active_at,
        })
    
    # Sort members by chats
    member_stats.sort(key=lambda x: x["chats"], reverse=True)
    
    # LiteLLM spend for group
    total_spend = 0.0
    if request.app.state.config.ENABLE_LITELLM_SPEND and member_ids:
        litellm_base_url = request.app.state.config.LITELLM_BASE_URL
        litellm_master_key = request.app.state.config.LITELLM_MASTER_KEY
        if litellm_base_url and litellm_master_key:
            spend_data = await fetch_litellm_spend(litellm_base_url, litellm_master_key, member_ids)
            for uid in member_ids:
                total_spend += spend_data.get(uid, {}).get("spend", 0.0)
            # Add spend to member stats
            for ms in member_stats:
                ms["spend"] = round(spend_data.get(ms["id"], {}).get("spend", 0.0), 2)
    
    return {
        "group": {
            "id": target_group.id,
            "name": target_group.name,
            "description": target_group.description,
            "created_at": target_group.created_at,
            "updated_at": target_group.updated_at,
        },
        "stats": {
            "members": len(members),
            "chats": len(group_chats),
            "messages": total_messages,
            "tokens": {
                "total": total_tokens,
                "input": input_tokens,
                "output": output_tokens,
            },
            "spend": round(total_spend, 2),
        },
        "models": top_models,
        "members": member_stats,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
