<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import MediaGrid from './MediaGrid.svelte';
  import MediaList from './MediaList.svelte';
  import type { MediaFile, ViewMode, SortBy, SortDir } from '$lib/types/media';

  export let visibleData: MediaFile[] = [];
  export let filteredData: MediaFile[] = [];
  export let deleting: Record<string, boolean> = {};
  export let viewMode: ViewMode = 'grid';
  export let sortBy: SortBy = 'updated';
  export let sortDir: SortDir = 'desc';
  export let selectedChatTitle: string = '';
  export let selectedChatFolderId: string | null = null;
  export let selectedFolderName: string = '';
  export let selectedMap: Record<string, boolean> = {};

  const dispatch = createEventDispatcher<{
    'enter-overview': void;
    'enter-folder': string;
    'preview': MediaFile;
    'chat-with': MediaFile;
    'delete': MediaFile;
    'load-more': void;
    'sort-change': { sortBy: SortBy; sortDir: SortDir };
    'toggle-select': string;
    'select-all-visible': boolean;
  }>();

  const enterOverview = () => {
    dispatch('enter-overview');
  };

  const enterFolder = (folderId: string) => {
    dispatch('enter-folder', folderId);
  };

  const handlePreview = (e: CustomEvent<MediaFile>) => {
    dispatch('preview', e.detail);
  };

  const handleChatWith = (e: CustomEvent<MediaFile>) => {
    dispatch('chat-with', e.detail);
  };

  const handleDelete = (e: CustomEvent<MediaFile>) => {
    dispatch('delete', e.detail);
  };

  const handleLoadMore = () => {
    dispatch('load-more');
  };

  const handleToggleSelect = (e: CustomEvent<string>) => {
    dispatch('toggle-select', e.detail);
  };

  const onKeyActivate = (e: KeyboardEvent, fn: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fn();
    }
  };

  const handleSortChange = (e: CustomEvent<{ sortBy: SortBy; sortDir: SortDir }>) => {
    dispatch('sort-change', e.detail);
  };
</script>

<div class="mt-2 mb-3 text-xs text-gray-500 dark:text-gray-400">
  <span role="link" tabindex="0" class="underline cursor-pointer" on:click={enterOverview} on:keydown={(e) => onKeyActivate(e, enterOverview)}>Overview</span>
  {#if selectedChatFolderId}
    <span> / </span>
    <span role="link" tabindex="0" class="underline cursor-pointer" on:click={() => enterFolder(selectedChatFolderId)} on:keydown={(e) => onKeyActivate(e, () => enterFolder(selectedChatFolderId))}>
      {selectedFolderName || 'Folder'}
    </span>
  {/if}
  <span> / </span>
  <span class="font-medium text-gray-700 dark:text-gray-300">{selectedChatTitle}</span>
</div>

{#if filteredData.length === 0}
  <div class="mt-6 text-gray-500 text-sm">No media found for this chat.</div>
{:else}
  {#if viewMode === 'grid'}
    <MediaGrid 
      items={visibleData} 
      {deleting}
      {selectedMap}
      on:preview={handlePreview}
      on:chat-with={handleChatWith}
      on:delete={handleDelete}
      on:toggle-select={handleToggleSelect}
    />
  {:else}
    <MediaList 
      items={visibleData} 
      {deleting}
      {sortBy}
      {sortDir}
      {selectedMap}
      on:preview={handlePreview}
      on:chat-with={handleChatWith}
      on:delete={handleDelete}
      on:sort-change={handleSortChange}
      on:toggle-select={handleToggleSelect}
      on:select-all-visible={(e) => dispatch('select-all-visible', e.detail)}
    />
  {/if}

  {#if visibleData.length < filteredData.length}
    <div class="flex justify-center my-6">
      <button 
        class="px-4 py-2 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 text-sm" 
        on:click={handleLoadMore}
      >
        Load more
      </button>
    </div>
  {/if}
{/if}
