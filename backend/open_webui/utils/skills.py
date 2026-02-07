"""
Agent Skills utility for parsing SKILL.md files and managing skill metadata.

Based on the Agent Skills specification: https://agentskills.io/specification

Skills are structured markdown instruction sets with YAML frontmatter that teach
LLMs how to perform specialized tasks. They integrate with Open WebUI's Knowledge
system, using `knowledge.meta.type = "skill"` to distinguish skills from regular KBs.
"""

import logging
import re
from typing import Optional

import yaml

from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

# Regex to match YAML frontmatter delimited by ---
FRONTMATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?",
    re.DOTALL,
)


class SkillMetadata:
    """Parsed metadata from a SKILL.md file."""

    def __init__(
        self,
        name: str,
        description: str,
        body: str,
        license: Optional[str] = None,
        compatibility: Optional[str] = None,
        metadata: Optional[dict] = None,
        allowed_tools: Optional[str] = None,
    ):
        self.name = name
        self.description = description
        self.body = body
        self.license = license
        self.compatibility = compatibility
        self.metadata = metadata or {}
        self.allowed_tools = allowed_tools

    def to_dict(self) -> dict:
        """Serialize to dict for storage in knowledge.meta.skill_metadata."""
        return {
            "name": self.name,
            "description": self.description,
            "license": self.license,
            "compatibility": self.compatibility,
            "metadata": self.metadata,
            "allowed_tools": self.allowed_tools,
        }

    def to_available_skill_xml(self) -> str:
        """Generate the lightweight XML representation for progressive disclosure."""
        return (
            f"<skill>\n"
            f"  <name>{self.name}</name>\n"
            f"  <description>{self.description}</description>\n"
            f"</skill>"
        )

    def to_full_prompt(self) -> str:
        """Generate the full skill content for system prompt injection."""
        return (
            f"<skill name=\"{self.name}\">\n"
            f"{self.body}\n"
            f"</skill>"
        )


def parse_skill_md(content: str) -> Optional[SkillMetadata]:
    """
    Parse a SKILL.md file content into SkillMetadata.

    Args:
        content: The raw text content of a SKILL.md file.

    Returns:
        SkillMetadata if parsing succeeds, None if the file is not a valid SKILL.md.
    """
    if not content or not content.strip():
        return None

    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        log.debug("No YAML frontmatter found in content")
        return None

    frontmatter_raw = match.group(1)
    body = content[match.end():].strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_raw)
    except yaml.YAMLError as e:
        log.warning(f"Failed to parse SKILL.md frontmatter: {e}")
        return None

    if not isinstance(frontmatter, dict):
        log.debug("Frontmatter is not a dict")
        return None

    name = frontmatter.get("name")
    description = frontmatter.get("description")

    if not name or not description:
        log.debug("SKILL.md missing required 'name' or 'description' fields")
        return None

    return SkillMetadata(
        name=str(name),
        description=str(description),
        body=body,
        license=frontmatter.get("license"),
        compatibility=frontmatter.get("compatibility"),
        metadata=frontmatter.get("metadata"),
        allowed_tools=frontmatter.get("allowed-tools"),
    )


def is_skill_file(filename: str) -> bool:
    """Check if a filename indicates a SKILL.md file."""
    return filename.upper() == "SKILL.MD"


def is_skill_knowledge(knowledge_model) -> bool:
    """Check if a knowledge base is a skill type."""
    if not knowledge_model or not knowledge_model.meta:
        return False
    return knowledge_model.meta.get("type") == "skill"


def build_available_skills_prompt(skills: list[dict]) -> str:
    """
    Build the <available_skills> XML block for system prompt injection.

    This is the lightweight representation (~100 tokens per skill) that gets
    injected at startup so the LLM knows what skills are available.

    Args:
        skills: List of skill metadata dicts (from knowledge.meta.skill_metadata).

    Returns:
        XML string to inject into the system prompt.
    """
    if not skills:
        return ""

    skills_xml = "\n".join(
        f"  <skill>\n"
        f"    <name>{s['name']}</name>\n"
        f"    <description>{s['description']}</description>\n"
        f"  </skill>"
        for s in skills
    )

    return (
        "<available_skills>\n"
        f"{skills_xml}\n"
        "</available_skills>\n\n"
        "You have access to the skills listed above. When a user's request matches "
        "a skill's description, call the `activate_skill` tool with the skill's exact "
        "name to load its full instructions. Do NOT attempt to perform the task without "
        "first activating the relevant skill. Once activated, follow the skill "
        "instructions carefully."
    )


def build_active_skill_prompt(skill_name: str, skill_body: str) -> str:
    """
    Build the full skill prompt for injection when a skill is activated.

    Args:
        skill_name: The skill's name identifier.
        skill_body: The full SKILL.md body content (instructions).

    Returns:
        Formatted string to inject into the system prompt.
    """
    return (
        f"<active_skill name=\"{skill_name}\">\n"
        f"{skill_body}\n"
        f"</active_skill>"
    )


# --------------------------------------------------------------------------- #
#  activate_skill tool — progressive disclosure                                #
# --------------------------------------------------------------------------- #

ACTIVATE_SKILL_TOOL_ID = "__builtin_activate_skill__"

ACTIVATE_SKILL_SPEC = {
    "name": "activate_skill",
    "description": (
        "Activate a skill by name to load its full instructions. "
        "Call this when the user's request matches one of the available skills. "
        "The skill's detailed instructions will then be provided to you."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "The exact name of the skill to activate, as listed in <available_skills>.",
            }
        },
        "required": ["skill_name"],
    },
}


def build_activate_skill_tool(skill_map: dict[str, dict]) -> dict:
    """
    Build the tools_dict entry for the activate_skill built-in tool.

    Args:
        skill_map: Dict mapping skill name -> {"name", "body", "kb_id"}.

    Returns:
        A tool dict compatible with tools_dict in the middleware.
    """

    async def activate_skill(skill_name: str, __messages__: list = None, **_kwargs) -> str:
        """Activate a skill by name, returning its full instruction body."""
        matched = skill_map.get(skill_name)
        if not matched:
            # Try case-insensitive match
            for name, data in skill_map.items():
                if name.lower() == skill_name.lower():
                    matched = data
                    break

        if not matched:
            available = ", ".join(skill_map.keys())
            return f"Skill '{skill_name}' not found. Available skills: {available}"

        skill_body = matched["body"]
        skill_name_resolved = matched["name"]

        log.info(f"activate_skill: Activating skill '{skill_name_resolved}'")

        # Return the skill body wrapped in XML.
        # The middleware tool_call_handler will detect this marker and inject
        # the content into the system prompt instead of the user message.
        return (
            f"__SKILL_ACTIVATION__\n"
            f"{build_active_skill_prompt(skill_name_resolved, skill_body)}"
        )

    return {
        "tool_id": ACTIVATE_SKILL_TOOL_ID,
        "callable": activate_skill,
        "spec": ACTIVATE_SKILL_SPEC,
        "metadata": {
            "file_handler": False,
            "citation": False,
            "skill_tool": True,
        },
    }
