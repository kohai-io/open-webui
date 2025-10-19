<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import Spinner from '$lib/components/common/Spinner.svelte';
  import { fetchMediaOverview, resolveFileChat, deleteFile as deleteFileFn, deleteFiles, fetchPromptFromChat as fetchPromptFn } from '$lib/services/media';
  
  // Import components
  import MediaControls from './MediaControls.svelte';
  import MediaOverview from './MediaOverview.svelte';
  import MediaFolderView from './MediaFolderView.svelte';
  import MediaChatView from './MediaChatView.svelte';
  import MediaOrphansView from './MediaOrphansView.svelte';
  import MediaPreviewModal from './MediaPreviewModal.svelte';
  import MediaSelectionBar from '$lib/components/workspace/MediaSelectionBar.svelte';
  
  // Import utilities and types
  import { classify, contentUrl, fileMetaUrl, filterFiles, sortFiles, groupFiles, calculateCounts } from '$lib/utils/media';
  import type { MediaType, Mode, ViewMode, GroupBy, SortBy, SortDir, MediaFile, Chat, Folder } from '$lib/types/media';

  let loading = true;
  let error: string | null = null;
  let files: MediaFile[] = [];
  
  // Server-side pagination state
  let totalFiles = 0;
  let loadedFiles = 0;
  let usePagination = false;
  const SERVER_PAGE_SIZE = 100; // Load 100 files per API call
  let loadingMore = false;

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
  let groupBy: GroupBy = 'none'; // Default to gallery view (faster for large libraries)
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
    const token = localStorage.token;
    if (item?.id) {
      await resolveFileChat(item.id, files, fileToChat, chatsById, token);
    }
    if (!previewItem?.meta?.prompt) {
      fetchPromptFromChat(previewItem);
    }
  };

  const handlePreviewNavigate = (e: CustomEvent<number>) => {
    const newIndex = e.detail;
    if (newIndex >= 0 && newIndex < visibleData.length) {
      openPreview(visibleData[newIndex]);
    }
  };

  $: previewIndex = previewItem ? visibleData.findIndex(item => item.id === previewItem.id) : -1;

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
      await deleteFileFn(id, token);
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
      const failed = await deleteFiles(ids, token);
      // Remove successfully deleted files
      const failedSet = new Set(failed);
      files = files.filter((f) => !ids.includes(f.id) || failedSet.has(f.id));
      // Clean up fileToChat for deleted files
      for (const id of ids) {
        if (!failedSet.has(id)) {
          delete fileToChat[id];
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

  // These functions are now handled by the service module

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
      goto('/?chat=true');
    } catch (e) {
      console.error('Failed to start chat with file', e);
    }
  };

  // Reactive filtered and sorted data
  $: filteredData = (() => {
    // In overview mode with hierarchy grouping, or in folder mode, we don't list files
    if (mode === 'folder' || (mode === 'overview' && groupBy === 'hierarchy')) {
      return [] as MediaFile[];
    }
    
    // For overview mode with non-hierarchy grouping, show all files
    // For chat/orphans mode, use the existing filtering
    const modeForFilter = mode === 'overview' ? 'chat' : mode; // Treat overview as showing all chats
    const chatIdForFilter = mode === 'overview' ? null : selectedChatId; // No specific chat filter in overview
    
    // Filter files
    const filtered = filterFiles(files, activeTab, query, modeForFilter as Mode, chatIdForFilter, fileToChat);
    
    // Sort files
    return sortFiles(filtered, sortBy, sortDir);
  })();

  // Reactive visible slice
  $: visibleData = filteredData.slice(0, visibleCount);

  // Grouping and counts using utility functions
  $: groupedVisible = groupFiles(visibleData, groupBy, fileToChat, chatsById, foldersById, linking);

  // Load more files from server (server-side pagination)
  const loadMoreFromServer = async () => {
    if (loadingMore || !usePagination || loadedFiles >= totalFiles) return;
    
    try {
      loadingMore = true;
      const token = localStorage.token;
      const nextBatch = await fetchMediaOverview(token, loadedFiles, SERVER_PAGE_SIZE);
      
      // Append new files
      files = [...files, ...nextBatch.files];
      loadedFiles = files.length;
      
      // Merge chats and folders
      chatsById = { ...chatsById, ...nextBatch.chatsById };
      foldersById = { ...foldersById, ...nextBatch.foldersById };
      fileToChat = { ...fileToChat, ...nextBatch.fileToChat };
      
      console.log(`Loaded more files: ${nextBatch.files.length}, total: ${loadedFiles}/${totalFiles}`);
    } catch (e) {
      console.error('Failed to load more files', e);
    } finally {
      loadingMore = false;
    }
  };
  
  // Load more visible items (client-side pagination)
  const loadMore = () => {
    visibleCount += pageSize;
  };

  // Counts per type for tab badges
  $: counts = calculateCounts(files);

  onMount(async () => {
    try {
      const startTime = performance.now();
      loading = true;
      error = null;
      console.log('[PERF] Media page mount started');
      
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
        if (savedGroupBy && ['hierarchy','none'].includes(savedGroupBy)) groupBy = savedGroupBy as GroupBy;
      } catch {}

      // Use optimized media-overview endpoint via service
      const token = localStorage.token;
      
      // First, check total count to decide on pagination strategy
      console.log('[PERF] Fetching initial file count...');
      const t1 = performance.now();
      const initialCheck = await fetchMediaOverview(token, 0, 1);
      console.log(`[PERF] Initial count fetch: ${(performance.now() - t1).toFixed(0)}ms`);
      
      totalFiles = initialCheck.total || 0;
      usePagination = totalFiles > 100;
      
      console.log(`[PERF] Total media files: ${totalFiles}, using ${usePagination ? 'server-side' : 'client-side'} pagination`);
      
      // Load initial data
      console.log(`[PERF] Fetching ${usePagination ? SERVER_PAGE_SIZE : 'all'} files...`);
      const t2 = performance.now();
      const overview = usePagination
        ? await fetchMediaOverview(token, 0, SERVER_PAGE_SIZE)
        : await fetchMediaOverview(token);
      console.log(`[PERF] Main data fetch: ${(performance.now() - t2).toFixed(0)}ms`);
      
      const t3 = performance.now();
      files = overview.files;
      loadedFiles = files.length;
      chatsById = overview.chatsById;
      foldersById = overview.foldersById;
      fileToChat = overview.fileToChat;
      console.log(`[PERF] State assignment: ${(performance.now() - t3).toFixed(0)}ms`);
      
      const t4 = performance.now();
      console.log('[PERF] Media overview loaded:', {
        filesCount: files.length,
        totalFiles,
        usePagination,
        chatsCount: Object.keys(chatsById).length,
        foldersCount: Object.keys(foldersById).length,
        filesWithChat: Object.values(fileToChat).filter(c => c !== null).length,
        orphanFiles: Object.values(fileToChat).filter(c => c === null).length
      });
      
      initialFilesLoaded = true;
      console.log(`[PERF] Set initialFilesLoaded: ${(performance.now() - t4).toFixed(0)}ms`);
      
      const totalTime = performance.now() - startTime;
      console.log(`[PERF] ✅ TOTAL FRONTEND LOAD: ${totalTime.toFixed(0)}ms`);
    } catch (e: any) {
      console.error('[PERF] ❌ ERROR:', e);
      error = e?.message || 'Failed to load media overview';
    } finally {
      loading = false;
    }
  });

  // Persist UI state (debounced to reduce I/O)
  let storageTimer: any;
  $: {
    // Bundle all state changes together
    const state = { viewMode, query, activeTab, sortBy, sortDir, groupBy };
    clearTimeout(storageTimer);
    storageTimer = setTimeout(() => {
      try {
        localStorage.setItem('media:viewMode', state.viewMode);
        localStorage.setItem('media:query', state.query);
        localStorage.setItem('media:tab', state.activeTab);
        localStorage.setItem('media:sortBy', state.sortBy);
        localStorage.setItem('media:sortDir', state.sortDir);
        localStorage.setItem('media:groupBy', state.groupBy);
      } catch (e) {
        console.warn('Failed to persist media UI state', e);
      }
    }, 500);
  }

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
      async (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          // Check if we need more data from client-side pagination
          if (visibleData.length < filteredData.length) {
            loadMore();
          }
          // If using server-side pagination and approaching end of loaded data
          else if (usePagination && loadedFiles < totalFiles) {
            // Load more from server when we're near the end of currently loaded files
            const filtered = files.filter((f) => {
              const contentType = f.meta?.content_type || '';
              if (activeTab === 'all') return true;
              if (activeTab === 'image') return contentType.startsWith('image/');
              if (activeTab === 'video') return contentType.startsWith('video/');
              if (activeTab === 'audio') return contentType.startsWith('audio/');
              return true;
            });
            
            // Trigger server load when we've shown most of the loaded files
            if (visibleData.length >= filtered.length * 0.7) {
              await loadMoreFromServer();
            }
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

  // Fetch prompt from chat history using service module
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
      resolvedPrompt = await fetchPromptFn(fileId, chatsById, token);
    } catch (e) {
      console.error('Failed to fetch prompt from chat', e);
    } finally {
      promptLoading = false;
    }
  }
</script>

<div class="p-4 md:p-6 lg:p-8 mx-auto max-w-[1400px]">
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
    <div class="flex items-center gap-2">
      <div class="text-xl md:text-2xl font-semibold">Your Media</div>
      {#if usePagination && loadedFiles < totalFiles}
        <span class="text-xs text-gray-500 dark:text-gray-400">
          ({loadedFiles} of {totalFiles} loaded)
        </span>
      {/if}
    </div>

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
    {#if mode === 'overview' && groupBy === 'hierarchy'}
      <MediaOverview 
        {allFolders}
        {allChats}
        on:enter-folder={(e) => enterFolder(e.detail)}
        on:enter-chat={(e) => enterChat(e.detail)}
        on:enter-orphans={enterOrphans}
      />
    {:else if mode === 'overview'}
      <!-- All media view with grouping -->
      <MediaSelectionBar 
        {selectedCount}
        {loading}
        on:delete={deleteSelected}
        on:clear={clearSelection}
      />
      <MediaOrphansView 
        {visibleData}
        {filteredData}
        {deleting}
        {viewMode}
        {sortBy}
        {sortDir}
        selectedMap={selectedMap}
        showBreadcrumb={false}
        on:enter-overview={enterOverview}
        on:preview={(e) => openPreview(e.detail)}
        on:chat-with={(e) => chatWith(e.detail)}
        on:delete={(e) => deleteFile(e.detail)}
        on:toggle-select={(e) => toggleSelect(e.detail)}
        on:select-all-visible={(e) => selectAllVisible(e.detail)}
        on:load-more={loadMore}
        on:sort-change={(e) => { sortBy = e.detail.sortBy; sortDir = e.detail.sortDir; }}
      />
    {:else if mode === 'folder'}
      <MediaFolderView 
        {folderChats}
        selectedFolderName={getSelectedFolderName()}
        on:enter-overview={enterOverview}
        on:enter-chat={(e) => enterChat(e.detail)}
      />
    {:else if mode === 'chat'}
      <MediaSelectionBar 
        {selectedCount}
        {loading}
        on:delete={deleteSelected}
        on:clear={clearSelection}
      />
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
      <MediaSelectionBar 
        {selectedCount}
        {loading}
        on:delete={deleteSelected}
        on:clear={clearSelection}
      />
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

  <!-- Loading indicator for server-side pagination -->
  {#if loadingMore}
    <div class="flex justify-center items-center py-6">
      <Spinner className="size-5" />
      <span class="ml-2 text-sm text-gray-500">Loading more files...</span>
    </div>
  {/if}

  <!-- Infinite scroll sentinel -->
  <div bind:this={sentinel} class="h-1"></div>
</div>

<MediaPreviewModal 
  {previewItem}
  items={visibleData}
  currentIndex={previewIndex}
  on:close={closePreview}
  on:navigate={handlePreviewNavigate}
/>