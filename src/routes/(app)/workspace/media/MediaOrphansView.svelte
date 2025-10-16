<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import MediaCard from '$lib/components/workspace/MediaCard.svelte';
  import MediaList from './MediaList.svelte';
  import type { MediaFile, ViewMode, SortBy, SortDir } from '$lib/types/media';

  export let visibleData: MediaFile[] = [];
  export let filteredData: MediaFile[] = [];
  export let deleting: Record<string, boolean> = {};
  export let viewMode: ViewMode = 'grid';
  export let sortBy: SortBy = 'updated';
  export let sortDir: SortDir = 'desc';
  export let selectedMap: Record<string, boolean> = {};
  export let showBreadcrumb: boolean = true;
  export let breadcrumbTitle: string = 'Media not in chats';

  const dispatch = createEventDispatcher<{
    'enter-overview': void;
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

  const handleSortChange = (e: CustomEvent<{ sortBy: SortBy; sortDir: SortDir }>) => {
    dispatch('sort-change', e.detail);
  };

  const openPreview = (item: MediaFile) => {
    dispatch('preview', item);
  };

  const chatWith = (item: MediaFile) => {
    dispatch('chat-with', item);
  };

  const deleteFile = (item: MediaFile) => {
    dispatch('delete', item);
  };

  const onKeyActivate = (e: KeyboardEvent, fn: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fn();
    }
  };
  const toggleSelect = (id: string) => {
    dispatch('toggle-select', id);
  };
</script>

{#if showBreadcrumb}
  <div class="mt-2 mb-3 text-xs text-gray-500 dark:text-gray-400">
    <span role="link" tabindex="0" class="underline cursor-pointer" on:click={enterOverview} on:keydown={(e) => onKeyActivate(e, enterOverview)}>Overview</span>
    <span> / </span>
    <span class="font-medium text-gray-700 dark:text-gray-300">{breadcrumbTitle}</span>
  </div>
{/if}

{#if filteredData.length === 0}
  <div class="mt-6 text-gray-500 text-sm">No unlinked media found.</div>
{:else}
  {#if viewMode === 'grid'}
    <div class="mt-5 grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {#each visibleData as item (item.id)}
        <MediaCard 
          {item}
          deleting={!!deleting[item.id]}
          selected={!!selectedMap[item.id]}
          on:preview
          on:chat-with
          on:delete
          on:toggle-select
        />
      {/each}
    </div>
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
      on:toggle-select={(e) => toggleSelect(e.detail)}
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
