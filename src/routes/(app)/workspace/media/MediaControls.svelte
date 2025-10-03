<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { MediaType, ViewMode, GroupBy, Mode } from './media-types';

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

  const handleGroupByChange = (e: Event) => {
    const target = e.target as HTMLSelectElement;
    groupBy = target.value as GroupBy;
    dispatch('group-by-change', groupBy);
  };
</script>

<div class="flex items-center gap-2">
  <div class="inline-flex rounded-full border border-gray-200 dark:border-gray-800 overflow-hidden" role="tablist" aria-label="Media type">
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'all'} 
      class="px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'all' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('all')}
    >
      All
    </button>
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'image'} 
      class="px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'image' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('image')}
    >
      Images
    </button>
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'video'} 
      class="px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'video' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('video')}
    >
      Videos
    </button>
    <button 
      type="button" 
      role="tab" 
      aria-selected={activeTab === 'audio'} 
      class="px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {activeTab === 'audio' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}" 
      on:click={() => handleTabChange('audio')}
    >
      Audio
    </button>
  </div>

  <input
    class="ml-2 md:ml-3 rounded-full px-4 py-1.5 text-sm bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 outline-none focus:ring-2 focus:ring-gray-200 dark:focus:ring-gray-800"
    placeholder="Search filename..."
    value={query}
    on:input={handleSearchInput}
  />

  <!-- View mode toggle -->
  <div class="ml-2 inline-flex rounded-full border border-gray-200 dark:border-gray-800 overflow-hidden">
    <button
      type="button"
      class="px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {viewMode === 'grid' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}"
      on:click={() => handleViewModeChange('grid')}
      title="Grid view"
    >
      Grid
    </button>
    <button
      type="button"
      class="px-3 py-1.5 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 {viewMode === 'list' ? 'bg-gray-100 dark:bg-gray-850 font-medium' : ''}"
      on:click={() => handleViewModeChange('list')}
      title="List view"
    >
      List
    </button>
  </div>

  <!-- Group by selector (chat mode only) -->
  {#if mode === 'chat'}
    <div class="ml-2 inline-flex items-center gap-1">
      <label for="media-groupby" class="text-xs text-gray-500 dark:text-gray-400">Group</label>
      <select
        class="rounded-full px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 outline-none"
        id="media-groupby"
        bind:value={groupBy}
        on:change={handleGroupByChange}
      >
        <option value="none">None</option>
        <option value="chat">Chat</option>
        <option value="folder">Folder</option>
      </select>
    </div>
  {/if}

  {#if linking}
    <div class="ml-1 text-[11px] text-gray-500 dark:text-gray-400">Resolving links…</div>
  {/if}
</div>
