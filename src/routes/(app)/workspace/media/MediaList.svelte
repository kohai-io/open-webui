<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { classify, contentUrl, formatBytes, formatDate } from '$lib/utils/media';
  import type { MediaFile, SortBy, SortDir } from '$lib/types/media';

  export let items: MediaFile[] = [];
  export let deleting: Record<string, boolean> = {};
  export let sortBy: SortBy = 'updated';
  export let sortDir: SortDir = 'desc';
  export let selectedMap: Record<string, boolean> = {};

  const dispatch = createEventDispatcher<{
    'preview': MediaFile;
    'chat-with': MediaFile;
    'delete': MediaFile;
    'sort-change': { sortBy: SortBy; sortDir: SortDir };
    'toggle-select': string;
    'select-all-visible': boolean;
  }>();

  const openPreview = (item: MediaFile) => {
    dispatch('preview', item);
  };

  const chatWith = (item: MediaFile) => {
    dispatch('chat-with', item);
  };

  const deleteFile = (item: MediaFile) => {
    dispatch('delete', item);
  };

  const handleSort = (newSortBy: SortBy) => {
    const was = sortBy === newSortBy;
    const newSortDir = was ? (sortDir === 'asc' ? 'desc' : 'asc') : (newSortBy === 'size' || newSortBy === 'updated' ? 'desc' : 'asc');
    
    sortBy = newSortBy;
    sortDir = newSortDir;
    
    dispatch('sort-change', { sortBy: newSortBy, sortDir: newSortDir });
  };

  // Master checkbox state
  let masterCb: HTMLInputElement | null = null;
  $: allSelected = items.length > 0 && items.every((it) => !!selectedMap[it.id]);
  $: someSelected = items.some((it) => !!selectedMap[it.id]);
  $: if (masterCb) {
    masterCb.indeterminate = !allSelected && someSelected;
  }
  const onToggleAll = (checked: boolean) => {
    dispatch('select-all-visible', checked);
  };

  function handleMasterChange(e: Event) {
    const target = e.currentTarget as HTMLInputElement | null;
    onToggleAll(!!target?.checked);
  }
</script>

<div class="mt-5 overflow-x-auto rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900">
  <table class="min-w-full text-sm">
    <thead class="text-left text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800">
      <tr>
        <th class="px-4 py-2 w-10">
          <input
            bind:this={masterCb}
            type="checkbox"
            class="h-4 w-4"
            aria-label="Select all visible"
            checked={allSelected}
            on:change={handleMasterChange}
          />
        </th>
        <th class="px-4 py-2" aria-sort={sortBy === 'name' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
          <button class="inline-flex items-center gap-1" on:click={() => handleSort('name')}>
            Name {#if sortBy === 'name'}<span>{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
          </button>
        </th>
        <th class="px-4 py-2" aria-sort={sortBy === 'type' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
          <button class="inline-flex items-center gap-1" on:click={() => handleSort('type')}>
            Type {#if sortBy === 'type'}<span>{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
          </button>
        </th>
        <th class="px-4 py-2" aria-sort={sortBy === 'size' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
          <button class="inline-flex items-center gap-1" on:click={() => handleSort('size')}>
            Size {#if sortBy === 'size'}<span>{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
          </button>
        </th>
        <th class="px-4 py-2" aria-sort={sortBy === 'updated' ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}>
          <button class="inline-flex items-center gap-1" on:click={() => handleSort('updated')}>
            Updated {#if sortBy === 'updated'}<span>{sortDir === 'asc' ? '▲' : '▼'}</span>{/if}
          </button>
        </th>
        <th class="px-4 py-2 text-right">Actions</th>
      </tr>
    </thead>
    <tbody>
      {#each items as item (item.id)}
        <tr class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50/50 dark:hover:bg-gray-850/50">
          <td class="px-4 py-2">
            <input type="checkbox" class="h-4 w-4" aria-label="Select item" checked={!!selectedMap[item.id]} on:click={() => dispatch('toggle-select', item.id)} />
          </td>
          <td class="px-4 py-2 max-w-[420px]">
            <div class="truncate text-gray-800 dark:text-gray-200">{item.filename}</div>
          </td>
          <td class="px-4 py-2">
            <span class="capitalize">{classify(item)}</span>
          </td>
          <td class="px-4 py-2">
            {formatBytes(item?.meta?.size)}
          </td>
          <td class="px-4 py-2">
            {formatDate(item?.updated_at)}
          </td>
          <td class="px-4 py-2 text-right">
            <button 
              class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 mr-2" 
              on:click={() => openPreview(item)}
            >
              Preview
            </button>
            <a 
              class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 mr-2" 
              href={contentUrl(item.id)} 
              target="_blank" 
              rel="noopener"
            >
              Open
            </a>
            <button 
              class="text-xs px-2 py-1 rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 mr-2" 
              on:click={() => chatWith(item)}
            >
              Chat
            </button>
            <button 
              class="text-xs px-2 py-1 rounded-full bg-red-100 dark:bg-red-900/30 hover:bg-red-200 dark:hover:bg-red-900/50 disabled:opacity-50" 
              on:click={() => deleteFile(item)} 
              disabled={!!deleting[item.id]}
            >
              {deleting[item.id] ? 'Deleting…' : 'Delete'}
            </button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
