<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import { getAllUserChats, getChatById, getChatListBySearchText } from '$lib/apis/chats';
  import { getFiles, getMediaOverview, deleteFileById } from '$lib/apis/files';
  import { getFolders } from '$lib/apis/folders';
  import Spinner from '$lib/components/common/Spinner.svelte';
  
  // Import components
  import MediaControls from './MediaControls.svelte';
  import MediaOverview from './MediaOverview.svelte';
  import MediaFolderView from './MediaFolderView.svelte';
  import MediaChatView from './MediaChatView.svelte';
  import MediaOrphansView from './MediaOrphansView.svelte';
  import MediaPreviewModal from './MediaPreviewModal.svelte';
  
  // Import utilities and types
  import { classify, contentUrl, fileMetaUrl, toEpoch, formatDate, formatBytes } from './media-utils';
  import type { MediaType, Mode, ViewMode, GroupBy, SortBy, SortDir, MediaFile, Chat, Folder, MediaCounts } from './media-types';

  let loading = true;
  let error: string | null = null;
  let files: MediaFile[] = [];

  // Navigation state
  let mode: Mode = 'overview';
  let selectedFolderId: string | null = null;
  let selectedChatId: string | null = null;
  let initialFilesLoaded = false; // lazy-load files only after entering chat

  // UI state
  let activeTab: MediaType = 'all';
  let query = '';
  let pageSize = 24; // items per "page" (client-side)
  let visibleCount = pageSize;
  let viewMode: ViewMode = 'grid';
  let groupBy: GroupBy = 'none';
  // Sorting state
  let sortBy: SortBy = 'updated';
  let sortDir: SortDir = 'desc';

  // Preview modal state
  let previewItem: any | null = null;
  // Declare prompt resolution state early to satisfy TS references
  let promptLoading = false;
  let resolvedPrompt: string | null = null;
  const openPreview = async (item: any) => {
    previewItem = item;
    resolvedPrompt = null;
    promptLoading = false;
    // Ensure this file's chat is resolved
    if (item?.id) {
      await resolveFileChat(item.id);
    }
    if (!previewItem?.meta?.prompt) {
      // Fire and forget; UI shows spinner state
      fetchPromptFromChat(previewItem);
    }
  };

  function selectAllVisible(checked: boolean) {
    const next: Record<string, boolean> = { ...selectedMap };
    for (const it of visibleData) {
      if (it?.id) next[it.id] = checked;
    }
    selectedMap = next;
  }

  // Navigation helpers (defined after support functions)

  // Delete file handler
  let deleting: Record<string, boolean> = {};
  async function deleteFile(item: any) {
    try {
      const id = item?.id;
      if (!id) return;
      if (!confirm(`Delete file "${item?.filename || id}"? This action cannot be undone.`)) return;
      deleting[id] = true;
      const token = localStorage.token;
      await deleteFileById(token, id);
      // Remove locally
      files = files.filter((f) => f.id !== id);
      // Remove from cache
      delete fileToChat[id];
    } catch (e) {
      console.error('Failed to delete file', e);
    }
  }
  const closePreview = () => {
    previewItem = null;
  };

  // Multi-select state for bulk actions
  let selectedMap: Record<string, boolean> = {};
  const isSelected = (id: string) => !!selectedMap[id];
  const toggleSelect = (id: string) => {
    selectedMap = { ...selectedMap, [id]: !selectedMap[id] };
  };
  const clearSelection = () => {
    selectedMap = {};
  };
  $: selectedCount = Object.values(selectedMap).filter(Boolean).length;

  async function deleteSelected() {
    const ids = Object.entries(selectedMap).filter(([, v]) => v).map(([k]) => k);
    if (ids.length === 0) return;
    if (!confirm(`Delete ${ids.length} selected file(s)? This action cannot be undone.`)) return;
    const token = localStorage.token;
    loading = true;
    try {
      for (const id of ids) {
        try {
          deleting[id] = true;
          await deleteFileById(token, id);
          files = files.filter((f) => f.id !== id);
        } catch (e) {
          console.error('Failed to delete file', id, e);
        } finally {
          deleting[id] = false;
        }
      }
    } finally {
      loading = false;
      clearSelection();
    }
  }

  // Grouping helpers state
  let chatsById: Record<string, Chat> = {};
  let foldersById: Record<string, Folder> = {};
  let fileToChat: Record<string, string | null> = {};
  let linking = false; // resolving file->chat links
  let linkingErrors = 0;

  // Derived collections for overview/folder screens
  $: allFolders = Object.values(foldersById);
  $: allChats = Object.values(chatsById);
  $: folderChats = selectedFolderId
    ? allChats.filter((c: any) => (c?.folder_id || c?.folderId) === selectedFolderId)
    : [];

  // Selected chat's folder id for breadcrumbs
  let selectedChatFolderId: string | null = null;
  $: selectedChatFolderId = selectedChatId
    ? (chatsById[selectedChatId]?.folder_id || chatsById[selectedChatId]?.folderId || null)
    : null;

  // Breadcrumb helpers
  function getSelectedFolderName(): string {
    return (selectedFolderId && foldersById[selectedFolderId]?.name) || '(Untitled folder)';
  }
  function getSelectedChatTitle(): string {
    return (selectedChatId && chatsById[selectedChatId]?.title) || '(Untitled chat)';
  }

  const ensureFoldersLoaded = async () => {
    try {
      const token = localStorage.token;
      const res = await getFolders(token);
      if (Array.isArray(res)) {
        const map: Record<string, any> = {};
        for (const f of res) map[f.id] = f;
        foldersById = map;
      }
    } catch (e) {
      console.warn('Failed to load folders', e);
    }
  };

  const ensureChatsIndex = async () => {
    try {
      const token = localStorage.token;
      const res = await getAllUserChats(token);
      if (Array.isArray(res)) {
        const map: Record<string, any> = {};
        for (const c of res) map[c.id] = c;
        chatsById = map;
      }
    } catch (e) {
      console.warn('Failed to load chats list', e);
    }
  };

  // Resolve single file's chat association
  const resolveFileChat = async (fileId: string): Promise<string | null> => {
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
      const token = localStorage.token;
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

  // Resolve multiple files in parallel (only when needed for grouping/orphans)
  const resolveFileChatLinks = async (items: any[]) => {
    linking = true;
    linkingErrors = 0;
    try {
      const batch = [...items];
      // Resolve in parallel for better performance
      await Promise.all(batch.map(f => resolveFileChat(f?.id).catch(() => null)));
    } finally {
      linking = false;
    }
  };

  // Navigation helpers
  function enterOverview() {
    mode = 'overview';
    selectedFolderId = null;
    selectedChatId = null;
  }

  function enterFolder(folderId: string) {
    selectedFolderId = folderId;
    selectedChatId = null;
    mode = 'folder';
  }

  async function enterChat(chatId: string) {
    selectedChatId = chatId;
    mode = 'chat';
    // Data is already loaded from media-overview endpoint
  }

  async function enterOrphans() {
    selectedFolderId = null;
    selectedChatId = null;
    mode = 'orphans';
    // Data is already loaded from media-overview endpoint
    // Orphans are files with null chat_id, already determined in fileToChat map
  }

  const resetPagination = () => {
    visibleCount = pageSize;
  };

  // classify function is now imported from media-utils

  // URL helpers are now imported from media-utils

  // formatBytes function is now imported from media-utils

  // toEpoch and formatDate functions are now imported from media-utils

  const chatWith = (item: any) => {
    try {
      const isImage = classify(item) === 'image';
      const chatInput = {
        prompt: '',
        files: [
          {
            type: isImage ? 'image' : 'file',
            id: item.id,
            name: item?.filename || item?.meta?.name || 'file',
            url: isImage ? contentUrl(item.id) : fileMetaUrl(item.id),
            collection_name: item?.meta?.collection_name || item?.collection_name || '',
            status: 'uploaded',
            ...(isImage ? {} : { file: { id: item.id } })
          }
        ],
        selectedToolIds: [],
        selectedFilterIds: [],
        webSearchEnabled: false,
        imageGenerationEnabled: false,
        codeInterpreterEnabled: false
      };

      sessionStorage.setItem('chat-input', JSON.stringify(chatInput));
      goto('/');
    } catch (e) {
      console.error('Failed to start chat with file', e);
    }
  };

  // Reactive filtered data
  $: filteredData = (() => {
    // In overview/folder modes, we don't list files
    if (mode !== 'chat' && mode !== 'orphans') return [] as any[];
    let data = [...files];

    // Tab filtering
    if (activeTab !== 'all') {
      data = data.filter((f) => classify(f) === activeTab);
    }

    // Search filtering
    if (query?.trim()) {
      const q = query.trim().toLowerCase();
      data = data.filter((f) => {
        const fname = (f.filename || '').toString().toLowerCase();
        const mname = (f?.meta?.name || '').toString().toLowerCase();
        return fname.includes(q) || mname.includes(q);
      });
    }

    // Sorting
    const getName = (it: any) => (it?.filename || it?.meta?.name || '').toString().toLowerCase();
    const getType = (it: any) => classify(it);
    const getSize = (it: any) => (typeof it?.meta?.size === 'number' ? it.meta.size : 0);
    const getUpdated = (it: any) => toEpoch(it?.updated_at);

    const cmp = (a: any, b: any) => {
      let va: any, vb: any;
      if (sortBy === 'name') {
        va = getName(a); vb = getName(b);
      } else if (sortBy === 'type') {
        va = getType(a); vb = getType(b);
      } else if (sortBy === 'size') {
        va = getSize(a); vb = getSize(b);
      } else {
        va = getUpdated(a); vb = getUpdated(b);
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      // Secondary sort by updated desc for stability
      const s = getUpdated(a) - getUpdated(b);
      return sortDir === 'asc' ? -s : s;
    };
    data.sort(cmp);

    // If in chat mode, restrict to the selected chat's files
    if (mode === 'chat' && selectedChatId) {
      data = data.filter((f) => {
        const chatId = fileToChat[f.id];
        return chatId === selectedChatId;
      });
    }
    // If in orphans mode, show files with no associated chat
    if (mode === 'orphans') {
      data = data.filter((f) => fileToChat[f.id] === null);
    }
    return data;
  })();

  // Reactive visible slice
  $: visibleData = filteredData.slice(0, visibleCount);

  // Grouping utilities
  function getChatForFile(it: any): any | null {
    const id = it?.id;
    if (!id) return null;
    const chatId = fileToChat[id];
    return chatId ? (chatsById[chatId] || null) : null;
  }

  function getFolderForFile(it: any): any | null {
    const chat = getChatForFile(it);
    if (!chat) return null;
    const fid = chat?.folder_id || chat?.folderId;
    return fid ? (foldersById[fid] || null) : null;
  }

  type Grouped = Record<string, { key: string; label: string; items: any[] }>;

  function groupItems(items: any[]): Grouped {
    const groups: Grouped = {};
    if (groupBy === 'none') {
      groups['__all__'] = { key: '__all__', label: 'All Media', items };
      return groups;
    }
    for (const it of items) {
      let key = '';
      let label = '';
      if (groupBy === 'chat') {
        const chat = getChatForFile(it);
        if (chat) {
          key = `chat:${chat.id}`;
          label = chat.title || '(Untitled chat)';
        } else {
          key = linking ? 'chat:resolving' : 'chat:none';
          label = linking ? 'Resolving chat…' : 'No chat found';
        }
      } else if (groupBy === 'folder') {
        const folder = getFolderForFile(it);
        if (folder) {
          key = `folder:${folder.id}`;
          label = folder.name || '(Untitled folder)';
        } else {
          key = linking ? 'folder:resolving' : 'folder:none';
          label = linking ? 'Resolving folders…' : 'No Folder';
        }
      }
      if (!groups[key]) groups[key] = { key, label, items: [] };
      groups[key].items.push(it);
    }
    return groups;
  }

  $: groupedVisible = groupItems(visibleData);

  const loadMore = () => {
    visibleCount += pageSize;
  };

  // Counts per type for tab badges
  $: counts = {
    all: files.length,
    image: files.filter((f) => classify(f) === 'image').length,
    video: files.filter((f) => classify(f) === 'video').length,
    audio: files.filter((f) => classify(f) === 'audio').length
  };

  onMount(async () => {
    try {
      loading = true;
      error = null;
      // Restore persisted UI state
      try {
        const savedView = localStorage.getItem('media:viewMode');
        if (savedView === 'grid' || savedView === 'list') viewMode = savedView;
        const savedQuery = localStorage.getItem('media:query');
        if (typeof savedQuery === 'string') query = savedQuery;
        const savedTab = localStorage.getItem('media:tab');
        if (savedTab === 'all' || savedTab === 'image' || savedTab === 'video' || savedTab === 'audio') activeTab = savedTab as MediaType;
        const savedSortBy = localStorage.getItem('media:sortBy') as SortBy | null;
        if (savedSortBy && ['name','type','size','updated'].includes(savedSortBy)) sortBy = savedSortBy as SortBy;
        const savedSortDir = localStorage.getItem('media:sortDir');
        if (savedSortDir === 'asc' || savedSortDir === 'desc') sortDir = savedSortDir;
        const savedGroupBy = localStorage.getItem('media:groupBy') as GroupBy | null;
        if (savedGroupBy && ['none','chat','folder'].includes(savedGroupBy)) groupBy = savedGroupBy as GroupBy;
      } catch {}

      // Use optimized media-overview endpoint
      const token = localStorage.token;
      const overview = await getMediaOverview(token);
      
      if (overview) {
        // Pre-populate files, chats, and folders from single API call
        files = Array.isArray(overview.files) ? overview.files : [];
        
        // Build chatsById map
        const chatsMap: Record<string, any> = {};
        if (Array.isArray(overview.chats)) {
          for (const c of overview.chats) chatsMap[c.id] = c;
        }
        chatsById = chatsMap;
        
        // Build foldersById map
        const foldersMap: Record<string, any> = {};
        if (Array.isArray(overview.folders)) {
          for (const f of overview.folders) foldersMap[f.id] = f;
        }
        foldersById = foldersMap;
        
        // Build fileToChat map from metadata (fast, no API calls needed)
        const fileChatMap: Record<string, string | null> = {};
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
          fileChatMap[f.id] = chatId ? String(chatId) : null;
        }
        fileToChat = fileChatMap;
        
        console.log('Media overview loaded:', {
          filesCount: files.length,
          chatsCount: Object.keys(chatsMap).length,
          foldersCount: Object.keys(foldersMap).length,
          filesWithChat: Object.values(fileChatMap).filter(c => c !== null).length,
          orphanFiles: Object.values(fileChatMap).filter(c => c === null).length
        });
        
        initialFilesLoaded = true;
      }
    } catch (e: any) {
      console.error(e);
      error = e?.message || 'Failed to load media overview';
    } finally {
      loading = false;
    }
  });

  // Persist UI state
  $: localStorage.setItem('media:viewMode', viewMode);
  $: localStorage.setItem('media:query', query);
  $: localStorage.setItem('media:tab', activeTab);
  $: localStorage.setItem('media:sortBy', sortBy);
  $: localStorage.setItem('media:sortDir', sortDir);
  $: localStorage.setItem('media:groupBy', groupBy);

  // Debounced search input
  let searchTimer: any;
  function onSearchInput(v: string) {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      query = v;
      resetPagination();
    }, 200);
  }
  function handleSearchInput(e: Event) {
    const target = e.target as HTMLInputElement | null;
    onSearchInput(target?.value ?? '');
  }

  // Infinite scroll sentinel
  let sentinel: HTMLDivElement | undefined;
  let observer: IntersectionObserver | undefined;
  onMount(() => {
    observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          if (visibleData.length < filteredData.length) {
            loadMore();
          }
        }
      },
      { root: null, rootMargin: '800px', threshold: 0 }
    );
    if (sentinel) observer.observe(sentinel);
  });
  onDestroy(() => {
    observer?.disconnect();
  });

  // Copy-to-clipboard helper for prompt
  let copied = false;
  async function copyText(text: string) {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        // Fallback for older browsers
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      copied = true;
      setTimeout(() => (copied = false), 1200);
    } catch (e) {
      console.error('Failed to copy text', e);
    }
  }

  // Resolve prompt from chat history when not saved in meta
  function extractAssistantPrompt(text: string): string | null {
    if (!text) return null;
    // Common patterns: "**Prompt:**\n..." or "Prompt:\n..."
    const idx = text.toLowerCase().indexOf('prompt:');
    if (idx === -1) return null;
    let slice = text.slice(idx + 'prompt:'.length);
    // Trim leading formatting characters and whitespace
    slice = slice.replace(/^\s*\*+\s*/i, '').trimStart();
    // Stop at typical separators or headings
    const stopMarkers = [
      '\n---',
      '\n**aspect ratio',
      '\n**parameters',
      '\n**model',
      '\n**notes',
      '\n\n',
    ];
    let end = slice.length;
    for (const mark of stopMarkers) {
      const p = slice.toLowerCase().indexOf(mark);
      if (p !== -1 && p < end) end = p;
    }
    const extracted = slice.slice(0, end).trim();
    return extracted || null;
  }
  async function fetchPromptFromChat(item: any) {
    try {
      promptLoading = true;
      resolvedPrompt = null;
      const token = localStorage.token;
      if (!token) {
        promptLoading = false;
        return;
      }

      const fileId = item?.id;
      const fileUrlPart = `/files/${fileId}`;

      // Prefilter chats by searching for the file id text to improve hit rate
      let chats = await getChatListBySearchText(token, fileId, 1).catch(() => null);
      if (!Array.isArray(chats) || chats.length === 0) {
        // Fallback: fetch all user chats
        chats = await getAllUserChats(token);
      }
      if (!Array.isArray(chats)) {
        promptLoading = false;
        return;
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
        // Find assistant/tool message that mentions this file by scanning all messages (dict or array)
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
            // Markdown image/file link patterns: ![...]](/api/v1/files/{id}/content)
            const mdMatches = text.match(/\/files\/(.*?)\//);
            if (mdMatches && mdMatches[1] && mdMatches[1] === fileId) {
              matchedMsg = m;
              break;
            }
          }

          // 2) Files array like: m.files = [{ id, type, url, ... }]
          const filesArr = Array.isArray(m?.files) ? m.files : [];
          if (filesArr.some((f: any) => f?.id === fileId)) {
            matchedMsg = m;
            break;
          }

          // 3) Content parts array: [{type:'image', id}, {type:'file', file:{id}}, {image_url:{url}}, etc.
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
              if (extracted) { resolvedPrompt = extracted; break; }
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
          if (!resolvedPrompt && userFallback) {
            resolvedPrompt = userFallback;
          }
          // If lineage failed for any reason, fall back to nearest assistant/user in chronological array
          if (!resolvedPrompt) {
            for (let j = allMsgs.length - 1; j >= 0; j--) {
              const am = allMsgs[j];
              if (am?.role !== 'assistant') continue;
              const atxt = typeof am?.content === 'string' ? am.content : JSON.stringify(am?.content ?? '');
              const extracted = extractAssistantPrompt(atxt || '');
              if (extracted) { resolvedPrompt = extracted; break; }
            }
            if (!resolvedPrompt) {
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
                  resolvedPrompt = promptText?.trim() || null;
                  break;
                }
              }
            }
          }
        }

        // Second pass: if not resolved yet, try direct scan of all assistant contents for a markdown file link to this id
        if (!resolvedPrompt) {
          for (let i = allMsgs.length - 1; i >= 0; i--) {
            const m = allMsgs[i];
            if (m?.role !== 'assistant' && m?.role !== 'tool') continue;
            const txt = typeof m?.content === 'string' ? m.content : JSON.stringify(m?.content ?? '');
            if (!txt) continue;
            if (txt.includes(`/files/${fileId}`)) {
              // Try the same assistant Prompt extraction preference
              for (let j = i; j >= 0; j--) {
                const am = allMsgs[j];
                if (am?.role !== 'assistant') continue;
                const atxt = typeof am?.content === 'string' ? am.content : JSON.stringify(am?.content ?? '');
                const extracted = extractAssistantPrompt(atxt || '');
                if (extracted) { resolvedPrompt = extracted; break; }
              }
              if (!resolvedPrompt) {
                // fallback to nearest user
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
                    resolvedPrompt = promptText?.trim() || null;
                    break;
                  }
                }
              }
              break;
            }
          }
        }

        if (resolvedPrompt) break;
      }
    } catch (e) {
      console.error('Failed to fetch prompt from chat', e);
    } finally {
      promptLoading = false;
    }
  }
</script>

<div class="p-4 md:p-6 lg:p-8 mx-auto max-w-[1400px]">
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
    <div class="text-xl md:text-2xl font-semibold">Your Media</div>

    <MediaControls 
      bind:activeTab
      bind:query
      bind:viewMode
      bind:groupBy
      {mode}
      {linking}
      on:tab-change={() => resetPagination()}
      on:search-input={() => resetPagination()}
      on:view-mode-change
      on:group-by-change={() => resetPagination()}
    />
  </div>

  {#if loading}
    <div class="w-full h-[50vh] flex items-center justify-center"><Spinner className="size-5" /></div>
  {:else if error}
    <div class="mt-6 text-red-500 text-sm">{error}</div>
  {:else}
    {#if mode === 'overview'}
      <MediaOverview 
        {allFolders}
        {allChats}
        on:enter-folder={(e) => enterFolder(e.detail)}
        on:enter-chat={(e) => enterChat(e.detail)}
        on:enter-orphans={enterOrphans}
      />
    {:else if mode === 'folder'}
      <MediaFolderView 
        {folderChats}
        selectedFolderName={getSelectedFolderName()}
        on:enter-overview={enterOverview}
        on:enter-chat={(e) => enterChat(e.detail)}
      />
    {:else if mode === 'chat'}
      {#if selectedCount > 0}
        <div class="mt-3 mb-2 flex items-center gap-2">
          <div class="text-sm">{selectedCount} selected</div>
          <button class="px-3 py-1.5 text-sm rounded-full bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/40" on:click={deleteSelected} disabled={loading}>Delete Selected</button>
          <button class="px-3 py-1.5 text-sm rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800" on:click={clearSelection}>Clear</button>
        </div>
      {/if}
      <MediaChatView 
        {visibleData}
        {filteredData}
        {deleting}
        {viewMode}
        {sortBy}
        {sortDir}
        selectedChatTitle={getSelectedChatTitle()}
        {selectedChatFolderId}
        selectedFolderName={selectedChatFolderId ? (foldersById[selectedChatFolderId]?.name || 'Folder') : ''}
        selectedMap={selectedMap}
        on:enter-overview={enterOverview}
        on:enter-folder={(e) => enterFolder(e.detail)}
        on:preview={(e) => openPreview(e.detail)}
        on:chat-with={(e) => chatWith(e.detail)}
        on:delete={(e) => deleteFile(e.detail)}
        on:toggle-select={(e) => toggleSelect(e.detail)}
        on:select-all-visible={(e) => selectAllVisible(e.detail)}
        on:load-more={loadMore}
        on:sort-change={(e) => { sortBy = e.detail.sortBy; sortDir = e.detail.sortDir; }}
      />
    {:else if mode === 'orphans'}
      {#if selectedCount > 0}
        <div class="mt-3 mb-2 flex items-center gap-2">
          <div class="text-sm">{selectedCount} selected</div>
          <button class="px-3 py-1.5 text-sm rounded-full bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/40" on:click={deleteSelected} disabled={loading}>Delete Selected</button>
          <button class="px-3 py-1.5 text-sm rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800" on:click={clearSelection}>Clear</button>
        </div>
      {/if}
      <MediaOrphansView 
        {visibleData}
        {filteredData}
        {deleting}
        {viewMode}
        {sortBy}
        {sortDir}
        selectedMap={selectedMap}
        on:enter-overview={enterOverview}
        on:preview={(e) => openPreview(e.detail)}
        on:chat-with={(e) => chatWith(e.detail)}
        on:delete={(e) => deleteFile(e.detail)}
        on:toggle-select={(e) => toggleSelect(e.detail)}
        on:select-all-visible={(e) => selectAllVisible(e.detail)}
        on:load-more={loadMore}
        on:sort-change={(e) => { sortBy = e.detail.sortBy; sortDir = e.detail.sortDir; }}
      />
    {/if}
  {/if}

  <!-- Infinite scroll sentinel -->
  <div bind:this={sentinel} class="h-1"></div>
</div>

<MediaPreviewModal 
  {previewItem}
  on:close={closePreview}
/>