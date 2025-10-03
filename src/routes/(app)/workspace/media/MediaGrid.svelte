<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { classify, contentUrl } from './media-utils';
  import type { MediaFile } from './media-types';

  export let items: MediaFile[] = [];
  export let deleting: Record<string, boolean> = {};
  export let selectedMap: Record<string, boolean> = {};

  const dispatch = createEventDispatcher<{
    'preview': MediaFile;
    'chat-with': MediaFile;
    'delete': MediaFile;
    'toggle-select': string;
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

  const handleKeydown = (e: KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  };
</script>

<div class="mt-5 grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
  {#each items as item (item.id)}
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
            class="w-full h-full object-cover" 
            loading="lazy" 
            decoding="async" 
          />
        </div>
        <div class="px-3 py-2 flex items-center justify-between gap-2">
          <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
          <div class="flex items-center gap-2 shrink-0">
            <input type="checkbox" class="h-4 w-4" aria-label="Select item" checked={!!selectedMap[item.id]} on:click|preventDefault|stopPropagation={() => dispatch('toggle-select', item.id)} />
            <button
              class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 hover:bg-gray-100 dark:hover:bg-gray-850"
              title="Chat"
              on:click|preventDefault|stopPropagation={() => chatWith(item)}
            >
              Chat
            </button>
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
    {:else if classify(item) === 'video'}
      <div class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition">
        <div 
          class="aspect-video bg-black cursor-zoom-in" 
          role="button" 
          tabindex="0" 
          aria-label="Preview video" 
          on:click={() => openPreview(item)} 
          on:keydown={(e) => handleKeydown(e, () => openPreview(item))}
        >
          <video controls src={contentUrl(item.id)} class="w-full h-full" preload="metadata">
            <track kind="captions" srclang="en" label="captions" />
          </video>
        </div>
        <div class="px-3 py-2 flex items-center justify-between gap-2">
          <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
          <div class="flex items-center gap-2 shrink-0">
            <input type="checkbox" class="h-4 w-4" aria-label="Select item" checked={!!selectedMap[item.id]} on:click|preventDefault|stopPropagation={() => dispatch('toggle-select', item.id)} />
            <button 
              class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 hover:bg-gray-100 dark:hover:bg-gray-850" 
              title="Chat" 
              on:click={() => chatWith(item)}
            >
              Chat
            </button>
            <button 
              class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 bg-red-50/70 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50" 
              title="Delete" 
              on:click={() => deleteFile(item)} 
              disabled={!!deleting[item.id]}
            >
              {deleting[item.id] ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
    {:else if classify(item) === 'audio'}
      <div class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition">
        <div 
          class="p-3 cursor-zoom-in" 
          role="button" 
          tabindex="0" 
          aria-label="Preview audio" 
          on:click={() => openPreview(item)} 
          on:keydown={(e) => handleKeydown(e, () => openPreview(item))}
        >
          <audio controls src={contentUrl(item.id)} class="w-full"></audio>
        </div>
        <div class="px-3 pb-3 flex items-center justify-between gap-2">
          <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
          <div class="flex items-center gap-2 shrink-0">
            <input type="checkbox" class="h-4 w-4" aria-label="Select item" checked={!!selectedMap[item.id]} on:click|preventDefault|stopPropagation={() => dispatch('toggle-select', item.id)} />
            <button 
              class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 hover:bg-gray-100 dark:hover:bg-gray-850" 
              title="Chat" 
              on:click={() => chatWith(item)}
            >
              Chat
            </button>
            <button 
              class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 bg-red-50/70 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50" 
              title="Delete" 
              on:click={() => deleteFile(item)} 
              disabled={!!deleting[item.id]}
            >
              {deleting[item.id] ? 'Deleting…' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
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
            <input type="checkbox" class="h-4 w-4" aria-label="Select item" checked={!!selectedMap[item.id]} on:click|preventDefault|stopPropagation={() => dispatch('toggle-select', item.id)} />
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
