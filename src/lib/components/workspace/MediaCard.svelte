<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { classify, contentUrl } from '$lib/utils/media';
  import type { MediaFile } from '$lib/types/media';

  export let item: MediaFile;
  export let deleting: boolean = false;
  export let selected: boolean = false;
  export let showChatButton: boolean = true;

  const dispatch = createEventDispatcher<{
    'preview': MediaFile;
    'chat-with': MediaFile;
    'delete': MediaFile;
    'toggle-select': string;
  }>();

  const openPreview = () => {
    dispatch('preview', item);
  };

  const chatWith = () => {
    dispatch('chat-with', item);
  };

  const deleteFile = () => {
    dispatch('delete', item);
  };

  const toggleSelect = () => {
    dispatch('toggle-select', item.id);
  };

  const handleKeydown = (e: KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  };

  $: mediaType = classify(item);
</script>

{#if mediaType === 'image'}
  <a 
    class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition" 
    href={contentUrl(item.id)} 
    target="_blank" 
    rel="noopener" 
    on:click|preventDefault={openPreview}
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
          checked={selected}
          on:click|preventDefault|stopPropagation={toggleSelect}
        />
        {#if showChatButton}
          <button 
            class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 hover:bg-gray-100 dark:hover:bg-gray-850" 
            title="Chat" 
            on:click|preventDefault|stopPropagation={chatWith}
          >
            Chat
          </button>
        {/if}
        <button 
          class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 bg-red-50/70 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50" 
          title="Delete" 
          on:click|preventDefault|stopPropagation={deleteFile}
          disabled={deleting}
        >
          {deleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  </a>
{:else if mediaType === 'video'}
  <div class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition">
    <div 
      class="aspect-video bg-black cursor-zoom-in relative" 
      role="button" 
      tabindex="0" 
      aria-label="Preview video" 
      on:click={openPreview}
      on:keydown={(e) => handleKeydown(e, openPreview)}
    >
      <video src={`${contentUrl(item.id)}#t=0.1`} class="w-full h-full pointer-events-none" preload="metadata">
        <track kind="captions" srclang="en" label="captions" />
      </video>
      <div class="absolute inset-0 flex items-center justify-center bg-black/20 group-hover:bg-black/30 transition">
        <div class="w-12 h-12 rounded-full bg-white/90 dark:bg-gray-900/90 flex items-center justify-center shadow-lg">
          <svg class="w-6 h-6 text-gray-800 dark:text-gray-200 ml-0.5" fill="currentColor" viewBox="0 0 16 16">
            <path d="M5 3.5v9l7-4.5z"/>
          </svg>
        </div>
      </div>
    </div>
    <div class="px-3 py-2 flex items-center justify-between gap-2">
      <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
      <div class="flex items-center gap-2 shrink-0">
        <input 
          type="checkbox" 
          class="h-4 w-4" 
          aria-label="Select item" 
          checked={selected}
          on:click|stopPropagation={toggleSelect}
        />
        {#if showChatButton}
          <button 
            class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 hover:bg-gray-100 dark:hover:bg-gray-850" 
            title="Chat" 
            on:click|stopPropagation={chatWith}
          >
            Chat
          </button>
        {/if}
        <button 
          class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 bg-red-50/70 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50" 
          title="Delete" 
          on:click|stopPropagation={deleteFile}
          disabled={deleting}
        >
          {deleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  </div>
{:else if mediaType === 'audio'}
  <div class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition">
    <div 
      class="p-3 cursor-zoom-in" 
      role="button" 
      tabindex="0" 
      aria-label="Preview audio" 
      on:click={openPreview}
      on:keydown={(e) => handleKeydown(e, openPreview)}
    >
      <audio controls src={contentUrl(item.id)} class="w-full">
        <track kind="captions" srclang="en" label="captions" />
      </audio>
    </div>
    <div class="px-3 pb-3 flex items-center justify-between gap-2">
      <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
      <div class="flex items-center gap-2 shrink-0">
        <input 
          type="checkbox" 
          class="h-4 w-4" 
          aria-label="Select item" 
          checked={selected}
          on:click|stopPropagation={toggleSelect}
        />
        {#if showChatButton}
          <button 
            class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 hover:bg-gray-100 dark:hover:bg-gray-850" 
            title="Chat" 
            on:click|stopPropagation={chatWith}
          >
            Chat
          </button>
        {/if}
        <button 
          class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 bg-red-50/70 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50" 
          title="Delete" 
          on:click|stopPropagation={deleteFile}
          disabled={deleting}
        >
          {deleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  </div>
{:else}
  <!-- Other file types (documents, etc.) -->
  <a 
    class="group block rounded-xl overflow-hidden border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition" 
    href={contentUrl(item.id)} 
    target="_blank" 
    rel="noopener" 
    on:click|preventDefault={openPreview}
  >
    <div class="aspect-video bg-gray-100 dark:bg-gray-950 flex items-center justify-center text-xs text-gray-500 cursor-zoom-in">
      📄
    </div>
    <div class="px-3 py-2 flex items-center justify-between gap-2">
      <div class="text-xs text-gray-700 dark:text-gray-300 truncate">{item.filename}</div>
      <div class="flex items-center gap-2 shrink-0">
        <input 
          type="checkbox" 
          class="h-4 w-4" 
          aria-label="Select item" 
          checked={selected}
          on:click|preventDefault|stopPropagation={toggleSelect}
        />
        {#if showChatButton}
          <button 
            class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-gray-200 dark:border-gray-800 bg-white/80 dark:bg-gray-900/60 hover:bg-gray-100 dark:hover:bg-gray-850" 
            title="Chat" 
            on:click|preventDefault|stopPropagation={chatWith}
          >
            Chat
          </button>
        {/if}
        <button 
          class="inline-flex items-center h-7 px-3 rounded-full text-xs whitespace-nowrap border border-red-300 dark:border-red-900 text-red-700 dark:text-red-300 bg-red-50/70 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 disabled:opacity-50" 
          title="Delete" 
          on:click|preventDefault|stopPropagation={deleteFile}
          disabled={deleting}
        >
          {deleting ? 'Deleting…' : 'Delete'}
        </button>
      </div>
    </div>
  </a>
{/if}
