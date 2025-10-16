<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { MediaType, ViewMode, GroupBy, Mode } from '$lib/types/media';

  export let activeTab: MediaType = 'all';
  export let query: string = '';
  export let viewMode: ViewMode = 'grid';
  export let groupBy: GroupBy = 'none';
  export let mode: Mode = 'overview';
  export let linking: boolean = false;

  const dispatch = createEventDispatcher<{
    'tab-change': MediaType;
    'search-input': string;
    'view-mode-change': ViewMode;
    'group-by-change': GroupBy;
  }>();

  let searchTimer: any;

  const handleTabChange = (tab: MediaType) => {
    activeTab = tab;
    dispatch('tab-change', tab);
  };

  const handleSearchInput = (e: Event) => {
    const target = e.target as HTMLInputElement | null;
    const value = target?.value ?? '';
    
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      query = value;
      dispatch('search-input', value);
    }, 200);
  };

  const handleViewModeChange = (mode: ViewMode) => {
    viewMode = mode;
    dispatch('view-mode-change', mode);
  };

  const handleGroupByChange = (mode: GroupBy) => {
    groupBy = mode;
    dispatch('group-by-change', groupBy);
  };
</script>

<div class="flex flex-wrap items-center gap-2">
  <div class="inline-flex rounded-full border border-gray-200 dark:border-gray-800 overflow-hidden" role="tablist" aria-label="Media type">
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'all'} 
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'all' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('all')}
    >
      All
    </button>
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'image'} 
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'image' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('image')}
    >
      <span class="hidden xs:inline">Images</span>
      <span class="xs:hidden">Img</span>
    </button>
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'video'} 
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'video' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('video')}
    >
      <span class="hidden xs:inline">Videos</span>
      <span class="xs:hidden">Vid</span>
    </button>
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'audio'} 
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'audio' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('audio')}
    >
      <span class="hidden xs:inline">Audio</span>
      <span class="xs:hidden">Aud</span>
    </button>
  </div>

  <input
    class="flex-1 min-w-[120px] sm:min-w-[160px] rounded-full px-3 sm:px-4 py-1.5 text-xs sm:text-sm bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-800"
    placeholder="Search..."
    value={query}
    on:input={handleSearchInput}
  />

  <!-- View mode toggle -->
  <div class="inline-flex rounded-full border border-gray-200 dark:border-gray-800 overflow-hidden">
    <button
      type="button"
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {viewMode === 'grid' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}"
      on:click={() => handleViewModeChange('grid')}
      title="Grid view"
      aria-label="Grid view"
    >
      <span class="hidden sm:inline">Grid</span>
      <span class="sm:hidden">⊞</span>
    </button>
    <button
      type="button"
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {viewMode === 'list' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}"
      on:click={() => handleViewModeChange('list')}
      title="List view"
      aria-label="List view"
    >
      <span class="hidden sm:inline">List</span>
      <span class="sm:hidden">☰</span>
    </button>
  </div>

  <!-- View mode toggle (overview mode only) -->
  {#if mode === 'overview'}
    <div class="inline-flex rounded-full border border-gray-200 dark:border-gray-800 overflow-hidden">
      <button
        type="button"
        class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {groupBy === 'hierarchy' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}"
        on:click={() => handleGroupByChange('hierarchy')}
        title="Browse by folders and chats"
      >
        Browse
      </button>
      <button
        type="button"
        class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {groupBy === 'none' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}"
        on:click={() => handleGroupByChange('none')}
        title="View all media"
      >
        Gallery
      </button>
    </div>
  {/if}

  {#if linking}
    <div class="ml-1 text-[11px] text-gray-500 dark:text-gray-400">Resolving links…</div>
  {/if}
</div>
