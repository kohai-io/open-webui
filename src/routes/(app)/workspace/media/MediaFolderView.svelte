<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { formatDate } from '$lib/utils/media';
  import type { Chat } from '$lib/types/media';

  export let folderChats: Chat[] = [];
  export let selectedFolderName: string = '';

  const dispatch = createEventDispatcher<{
    'enter-overview': void;
    'enter-chat': string;
  }>();

  const enterOverview = () => {
    dispatch('enter-overview');
  };

  const enterChat = (chatId: string) => {
    dispatch('enter-chat', chatId);
  };

  const handleKeydown = (e: KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  };
</script>

<div class="mt-5">
  <div class="flex items-center gap-2 mb-4 text-sm">
    <button 
      class="px-3 py-1.5 text-xs rounded-full border border-gray-200 dark:border-gray-800 hover:bg-gray-100 dark:hover:bg-gray-850" 
      on:click={enterOverview}
    >
      Back
    </button>
    <div class="text-gray-500 dark:text-gray-400">Overview</div>
    <div class="text-gray-400">/</div>
    <div class="font-medium">{selectedFolderName}</div>
  </div>

  {#if folderChats.length === 0}
    <div class="text-xs text-gray-500 dark:text-gray-400">No chats in this folder.</div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {#each folderChats as chat (chat.id)}
        <div 
          role="button" 
          tabindex="0" 
          class="group rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition p-4 cursor-pointer"
          on:click={() => enterChat(chat.id)}
          on:keydown={(e) => handleKeydown(e, () => enterChat(chat.id))}
        >
          <div class="flex items-center gap-3">
            <div class="shrink-0 w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-850 flex items-center justify-center">💬</div>
            <div class="min-w-0">
              <div class="text-sm font-medium truncate">{chat.title || '(Untitled chat)'}</div>
              <div class="text-[11px] text-gray-500 dark:text-gray-400">Updated {formatDate(chat.updated_at)}</div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>
