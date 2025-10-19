/**
 * Service module for media management operations
 */

import { getAllUserChats, getChatById, getChatListBySearchText } from '$lib/apis/chats';
import { deleteFileById, getMediaOverview } from '$lib/apis/files';
import type { MediaFile, Chat, Folder } from '$lib/types/media';
import { extractAssistantPrompt } from '$lib/utils/media';

// Prompt cache to avoid repeated expensive fetches
const promptCache = new Map<string, string | null>();

export interface MediaOverviewData {
	files: MediaFile[];
	chatsById: Record<string, Chat>;
	foldersById: Record<string, Folder>;
	fileToChat: Record<string, string | null>;
	total?: number;
	skip?: number;
	limit?: number;
}

/**
 * Fetch all media data in a single optimized call
 * @param token - Auth token
 * @param skip - Number of files to skip (for pagination)
 * @param limit - Max files to return (0 = all)
 */
export const fetchMediaOverview = async (
	token: string,
	skip: number = 0,
	limit: number = 0
): Promise<MediaOverviewData> => {
	const overview = await getMediaOverview(token, skip, limit);

	if (!overview) {
		return {
			files: [],
			chatsById: {},
			foldersById: {},
			fileToChat: {}
		};
	}

	// Pre-populate files, chats, and folders from single API call
	const files = Array.isArray(overview.files) ? overview.files : [];

	// Build chatsById map
	const chatsById: Record<string, Chat> = {};
	if (Array.isArray(overview.chats)) {
		for (const c of overview.chats) chatsById[c.id] = c;
	}

	// Build foldersById map
	const foldersById: Record<string, Folder> = {};
	if (Array.isArray(overview.folders)) {
		for (const f of overview.folders) foldersById[f.id] = f;
	}

	// Build fileToChat map from metadata (fast, no API calls needed)
	const fileToChat: Record<string, string | null> = {};
	for (const f of files) {
		// Check multiple possible locations for chat_id
		let chatId = null;
		if (f.meta) {
			chatId = f.meta.chat_id || f.meta.source_chat_id;
		}
		// Fallback to top-level chat_id if exists
		if (!chatId && f.chat_id) {
			chatId = f.chat_id;
		}
		// Treat 'orphan' marker as null (files not in any chat)
		fileToChat[f.id] = chatId && chatId !== 'orphan' ? String(chatId) : null;
	}

	return {
		files,
		chatsById,
		foldersById,
		fileToChat,
		total: overview.total,
		skip: overview.skip,
		limit: overview.limit
	};
};

/**
 * Resolve a single file's chat association
 */
export const resolveFileChat = async (
	fileId: string,
	files: MediaFile[],
	fileToChat: Record<string, string | null>,
	chatsById: Record<string, Chat>,
	token: string
): Promise<string | null> => {
	if (!fileId) return null;

	// Skip if already known
	if (fileToChat[fileId] !== undefined) return fileToChat[fileId];

	const file = files.find(f => f.id === fileId);
	if (!file) return null;

	// 1) Meta hints
	const metaChatId = file?.meta?.chat_id || file?.meta?.source_chat_id || file?.chat_id;
	if (metaChatId) {
		fileToChat[fileId] = String(metaChatId);
		return fileToChat[fileId];
	}

	// 2) Fast server-side search by file id
	try {
		const hits = await getChatListBySearchText(token, fileId, 1);
		if (Array.isArray(hits) && hits.length > 0) {
			fileToChat[fileId] = hits[0].id;
			// cache minimal chat record if missing
			if (!chatsById[hits[0].id]) chatsById[hits[0].id] = hits[0];
			return fileToChat[fileId];
		}
	} catch (e) {
		console.warn('Failed to resolve chat for file', fileId, e);
	}

	// 3) Unknown
	fileToChat[fileId] = null;
	return null;
};

/**
 * Delete a single file
 */
export const deleteFile = async (fileId: string, token: string): Promise<void> => {
	await deleteFileById(token, fileId);
};

/**
 * Delete multiple files
 */
export const deleteFiles = async (fileIds: string[], token: string): Promise<string[]> => {
	const failed: string[] = [];

	for (const id of fileIds) {
		try {
			await deleteFileById(token, id);
		} catch (e) {
			console.error('Failed to delete file', id, e);
			failed.push(id);
		}
	}

	return failed;
};

/**
 * Extract prompt from chat history when not saved in file metadata
 */
export const fetchPromptFromChat = async (
	fileId: string,
	chatsById: Record<string, Chat>,
	token: string
): Promise<string | null> => {
	// Check cache first
	if (promptCache.has(fileId)) {
		return promptCache.get(fileId)!;
	}

	try {
		const fileUrlPart = `/files/${fileId}`;

		// Prefilter chats by searching for the file id text to improve hit rate
		let chats = await getChatListBySearchText(token, fileId, 1).catch(() => null);
		if (!Array.isArray(chats) || chats.length === 0) {
			// Fallback: fetch all user chats
			chats = await getAllUserChats(token);
		}
		if (!Array.isArray(chats)) {
			return null;
		}

		// Sort newest first if timestamps exist
		chats.sort((a, b) => (b?.updated_at ?? 0) - (a?.updated_at ?? 0));

		const maxChats = 100;
		for (const chat of chats.slice(0, maxChats)) {
			const full = await getChatById(token, chat.id);
			let messages = full?.chat?.messages;
			if (!Array.isArray(messages) || messages.length === 0) {
				const msgDict = full?.chat?.history?.messages;
				if (msgDict && typeof msgDict === 'object') {
					try {
						messages = Object.values(msgDict);
					} catch {
						messages = [];
					}
				}
			}
			if (!Array.isArray(messages) || messages.length === 0) continue;

			// Build a message lookup by id if possible
			const msgById: Record<string, any> = {};
			try {
				const msgDict = full?.chat?.history?.messages;
				if (msgDict && typeof msgDict === 'object') {
					for (const [k, v] of Object.entries(msgDict)) {
						const mv: any = v as any;
						msgById[k] = mv;
						if (!mv.id) mv.id = k;
					}
				} else {
					for (const m of messages) {
						if (m?.id) msgById[m.id] = m;
					}
				}
			} catch {}

			// Find assistant/tool message that mentions this file
			let matchedMsg: any = null;
			const allMsgs: any[] = Object.values(msgById).length ? Object.values(msgById) : messages;
			for (let i = allMsgs.length - 1; i >= 0; i--) {
				const m = allMsgs[i];
				const role = m?.role || '';
				if (role !== 'assistant' && role !== 'tool') continue;

				// 1) Textual content/JSON string
				const rawContent = m?.content;
				const text = typeof rawContent === 'string' ? rawContent : JSON.stringify(rawContent ?? '');
				if (text) {
					// Direct id/url match
					if (text.includes(fileId) || text.includes(fileUrlPart)) {
						matchedMsg = m;
						break;
					}
					// Markdown image/file link patterns
					const mdMatches = text.match(/\/files\/(.*?)\//);
					if (mdMatches && mdMatches[1] && mdMatches[1] === fileId) {
						matchedMsg = m;
						break;
					}
				}

				// 2) Files array
				const filesArr = Array.isArray(m?.files) ? m.files : [];
				if (filesArr.some((f: any) => f?.id === fileId)) {
					matchedMsg = m;
					break;
				}

				// 3) Content parts array
				if (Array.isArray(rawContent)) {
					const hit = rawContent.some((part: any) => {
						if (!part) return false;
						if (part?.id === fileId) return true;
						if (part?.file?.id === fileId) return true;
						const ptxt = JSON.stringify(part);
						return ptxt.includes(fileId) || ptxt.includes(fileUrlPart);
					});
					if (hit) {
						matchedMsg = m;
						break;
					}
				}

				// 4) Meta hints
				const genIds = m?.meta?.generated_file_ids;
				if (Array.isArray(genIds) && genIds.includes(fileId)) {
					matchedMsg = m;
					break;
				}
			}

			if (matchedMsg) {
				// Prefer lineage traversal via parentId chain
				let cur = matchedMsg;
				let userFallback: string | null = null;
				const seen = new Set<string>();
				while (cur && !seen.has(cur.id || '')) {
					if (cur?.id) seen.add(cur.id);
					if (cur?.role === 'assistant') {
						const atxt = typeof cur?.content === 'string' ? cur.content : JSON.stringify(cur?.content ?? '');
						const extracted = extractAssistantPrompt(atxt || '');
						if (extracted) {
							promptCache.set(fileId, extracted);
							return extracted;
						}
					} else if (cur?.role === 'user' && !userFallback) {
						const c = cur?.content;
						let promptText = '';
						if (typeof c === 'string') promptText = c;
						else if (Array.isArray(c)) {
							promptText = c
								.map((p: any) => (typeof p === 'string' ? p : p?.text || p?.content || ''))
								.filter(Boolean)
								.join('\n');
						} else if (typeof c === 'object' && c) {
							promptText = c?.text || c?.content || JSON.stringify(c);
						}
						userFallback = promptText?.trim() || null;
					}
					const pid = cur?.parentId;
					cur = pid ? msgById[pid] : null;
				}
				if (userFallback) {
					promptCache.set(fileId, userFallback);
					return userFallback;
				}

				// Fallback to nearest assistant/user in chronological array
				for (let j = allMsgs.length - 1; j >= 0; j--) {
					const am = allMsgs[j];
					if (am?.role !== 'assistant') continue;
					const atxt = typeof am?.content === 'string' ? am.content : JSON.stringify(am?.content ?? '');
					const extracted = extractAssistantPrompt(atxt || '');
					if (extracted) {
						promptCache.set(fileId, extracted);
						return extracted;
					}
				}
				for (let j = allMsgs.length - 1; j >= 0; j--) {
					const um = allMsgs[j];
					if (um?.role === 'user') {
						const c = um?.content;
						let promptText = '';
						if (typeof c === 'string') promptText = c;
						else if (Array.isArray(c)) {
							promptText = c
								.map((p: any) => (typeof p === 'string' ? p : p?.text || p?.content || ''))
								.filter(Boolean)
								.join('\n');
						} else if (typeof c === 'object' && c) {
							promptText = c?.text || c?.content || JSON.stringify(c);
						}
						const result = promptText?.trim() || null;
						promptCache.set(fileId, result);
						return result;
					}
				}
			}

			// Second pass: scan for markdown file links
			for (let i = allMsgs.length - 1; i >= 0; i--) {
				const m = allMsgs[i];
				if (m?.role !== 'assistant' && m?.role !== 'tool') continue;
				const txt = typeof m?.content === 'string' ? m.content : JSON.stringify(m?.content ?? '');
				if (!txt) continue;
				if (txt.includes(`/files/${fileId}`)) {
					// Try assistant prompt extraction
					for (let j = i; j >= 0; j--) {
						const am = allMsgs[j];
						if (am?.role !== 'assistant') continue;
						const atxt = typeof am?.content === 'string' ? am.content : JSON.stringify(am?.content ?? '');
						const extracted = extractAssistantPrompt(atxt || '');
						if (extracted) {
							promptCache.set(fileId, extracted);
							return extracted;
						}
					}
					// Fallback to nearest user
					for (let j = i - 1; j >= 0; j--) {
						const um = allMsgs[j];
						if (um?.role === 'user') {
							const c = um?.content;
							let promptText = '';
							if (typeof c === 'string') promptText = c;
							else if (Array.isArray(c)) {
								promptText = c
									.map((p: any) => (typeof p === 'string' ? p : p?.text || p?.content || ''))
									.filter(Boolean)
									.join('\n');
							} else if (typeof c === 'object' && c) {
								promptText = c?.text || c?.content || JSON.stringify(c);
							}
							const result = promptText?.trim() || null;
							promptCache.set(fileId, result);
							return result;
						}
					}
					break;
				}
			}
		}

		promptCache.set(fileId, null);
		return null;
	} catch (e) {
		console.error('Failed to fetch prompt from chat', e);
		promptCache.set(fileId, null);
		return null;
	}
};
