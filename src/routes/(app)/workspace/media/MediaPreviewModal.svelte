<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { classify, contentUrl, copyText, extractAssistantPrompt } from '$lib/utils/media';
  import { getAllUserChats, getChatById, getChatListBySearchText } from '$lib/apis/chats';
  import type { MediaFile } from '$lib/types/media';

  export let previewItem: MediaFile | null = null;
  export let items: MediaFile[] = [];
  export let currentIndex: number = -1;

  const dispatch = createEventDispatcher<{
    close: void;
    navigate: number;
  }>();

  $: hasPrev = currentIndex > 0;
  $: hasNext = currentIndex < items.length - 1;

  let promptLoading = false;
  let resolvedPrompt: string | null = null;
  let copied = false;

  $: if (previewItem && !previewItem?.meta?.prompt) {
    resolvedPrompt = null;
    promptLoading = false;
    // Don't auto-fetch, let user click the button
  }

  const closePreview = () => {
    dispatch('close');
  };

  const goToPrev = () => {
    if (hasPrev) {
      dispatch('navigate', currentIndex - 1);
    }
  };

  const goToNext = () => {
    if (hasNext) {
      dispatch('navigate', currentIndex + 1);
    }
  };

  const handleCopyText = async (text: string) => {
    const success = await copyText(text);
    if (success) {
      copied = true;
      setTimeout(() => (copied = false), 1200);
    }
  };

  const fetchPromptFromChat = async (item: MediaFile) => {
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
  };

  const handleKeydown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      closePreview();
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      goToPrev();
    } else if (e.key === 'ArrowRight') {
      e.preventDefault();
      goToNext();
    }
  };
</script>

<svelte:window on:keydown={handleKeydown} />

{#if previewItem}
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <div
      class="absolute inset-0 bg-black/60"
      role="button"
      tabindex="0"
      aria-label="Close preview"
      on:click={closePreview}
      on:keydown={(e) => { if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); closePreview(); } }}
    ></div>
    
    <!-- Previous button -->
    {#if hasPrev}
      <button
        class="absolute left-4 z-20 w-12 h-12 rounded-full bg-white/90 dark:bg-gray-900/90 hover:bg-white dark:hover:bg-gray-800 shadow-lg flex items-center justify-center transition"
        on:click={goToPrev}
        aria-label="Previous"
      >
        <svg class="w-6 h-6 text-gray-800 dark:text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
      </button>
    {/if}
    
    <!-- Next button -->
    {#if hasNext}
      <button
        class="absolute right-4 z-20 w-12 h-12 rounded-full bg-white/90 dark:bg-gray-900/90 hover:bg-white dark:hover:bg-gray-800 shadow-lg flex items-center justify-center transition"
        on:click={goToNext}
        aria-label="Next"
      >
        <svg class="w-6 h-6 text-gray-800 dark:text-gray-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    {/if}
    
    <div class="relative z-10 max-w-[90vw] max-h-[90vh] w-full md:w-auto bg-white dark:bg-gray-900 rounded-xl overflow-hidden shadow-xl">
      <div class="flex items-center justify-between px-3 py-2 border-b border-gray-200 dark:border-gray-800">
        <div class="text-sm truncate pr-2">{previewItem.filename}</div>
        <button class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800" on:click={closePreview}>Close</button>
      </div>
      <div class="p-3">
        {#if classify(previewItem) === 'image'}
          <img src={contentUrl(previewItem.id)} alt={previewItem.filename} class="max-w-full max-h-[75vh] object-contain" />
        {:else if classify(previewItem) === 'video'}
          <video controls src={contentUrl(previewItem.id)} class="max-w-full max-h-[75vh]" preload="metadata">
            <track kind="captions" srclang="en" label="captions" />
          </video>
        {:else if classify(previewItem) === 'audio'}
          <audio controls src={contentUrl(previewItem.id)} class="w-full"></audio>
        {:else}
          <a class="text-sm underline" href={contentUrl(previewItem.id)} target="_blank" rel="noopener">Open file</a>
        {/if}

        {#if previewItem?.meta?.prompt}
          <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-800">
            <div class="text-xs text-gray-500 dark:text-gray-400 mb-1">Prompt</div>
            <div class="flex items-start gap-2">
              <pre class="flex-1 text-sm text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-950 rounded-md p-2 whitespace-pre-wrap break-words max-h-48 overflow-auto">{previewItem.meta.prompt}</pre>
              <button class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 shrink-0" on:click={() => handleCopyText(previewItem.meta?.prompt || '')}>{copied ? 'Copied' : 'Copy'}</button>
            </div>
          </div>
        {:else}
          <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-800">
            <div class="text-xs text-gray-500 dark:text-gray-400 mb-2">Prompt</div>
            {#if resolvedPrompt}
              <div class="flex items-start gap-2">
                <pre class="flex-1 text-sm text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-950 rounded-md p-2 whitespace-pre-wrap break-words max-h-48 overflow-auto">{resolvedPrompt}</pre>
                <button class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 shrink-0" on:click={() => handleCopyText(resolvedPrompt || '')}>{copied ? 'Copied' : 'Copy'}</button>
              </div>
            {:else}
              <button class="text-xs px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800" on:click={() => fetchPromptFromChat(previewItem)} disabled={promptLoading}>
                {#if promptLoading}Fetching…{/if}
                {#if !promptLoading}Fetch from chat{/if}
              </button>
            {/if}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}
