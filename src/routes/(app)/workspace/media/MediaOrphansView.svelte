<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { classify, contentUrl } from './media-utils';
  import MediaList from './MediaList.svelte';
  import type { MediaFile, ViewMode, SortBy, SortDir } from './media-types';

  export let visibleData: MediaFile[] = [];
  export let filteredData: MediaFile[] = [];
  export let deleting: Record<string, boolean> = {};
  export let viewMode: ViewMode = 'grid';
  export let sortBy: SortBy = 'updated';
  export let sortDir: SortDir = 'desc';
  export let selectedMap: Record<string, boolean> = {};

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

<div class="mt-2 mb-3 text-xs text-gray-500 dark:text-gray-400">
  <span role="link" tabindex="0" class="underline cursor-pointer" on:click={enterOverview} on:keydown={(e) => onKeyActivate(e, enterOverview)}>Overview</span>
  <span> / </span>
  <span class="font-medium text-gray-700 dark:text-gray-300">Media not in chats</span>
</div>

{#if filteredData.length === 0}
  <div class="mt-6 text-gray-500 text-sm">No unlinked media found.</div>
{:else}
  {#if viewMode === 'grid'}
    <div class="mt-5 grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {#each visibleData as item (item.id)}
        {#if classify(item) === 'image'}
          <a 
            class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition" 
            href={contentUrl(item.id)} 
            target="_blank" 
            rel="noopener" 
            on:click|preventDefault={() => openPreview(item)}
          >
            <div class="aspect-video bg-gray-50 dark:bg-gray-950 flex items-center justify-center overflow-hidden cursor-zoom-in">
              <img 
                src={contentUrl(item.id)} 
                alt={item.filename} 
                loading="lazy" 
                decoding="async" 
              />
            </div>
            <div class="px-3 py-2 flex items-center justify-between gap-2">
          <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
          <div class="flex items-center gap-2 shrink-0">
            <input 
              type="checkbox" 
              class="h-4 w-4" 
              aria-label="Select item" 
              checked={!!selectedMap[item.id]} 
              on:click|preventDefault|stopPropagation={() => toggleSelect(item.id)} 
            />
            <button 
              class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 bg-red-50/70 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50" 
              title="Delete" 
              on:click|preventDefault|stopPropagation={() => deleteFile(item)} 
              disabled={!!deleting[item.id]}
            >
              {deleting[item.id] ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
          </a>
        {:else}
          <a 
            class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition" 
            href={contentUrl(item.id)} 
            target="_blank" 
            rel="noopener" 
            on:click|preventDefault={() => openPreview(item)}
          >
            <div class="aspect-video bg-gray-100 dark:bg-gray-950 flex items-center justify-center text-xs text-gray-500 cursor-zoom-in">
              File
            </div>
            <div class="px-3 py-2 flex items-center justify-between gap-2">
          <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
          <div class="flex items-center gap-2 shrink-0">
            <input 
              type="checkbox" 
              class="h-4 w-4" 
              aria-label="Select item" 
              checked={!!selectedMap[item.id]} 
              on:click|preventDefault|stopPropagation={() => toggleSelect(item.id)} 
            />
            <button 
              class="text-[11px] px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800" 
              on:click|preventDefault={() => chatWith(item)}
            >
              Chat
            </button>
          </div>
        </div>
          </a>
        {/if}
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
