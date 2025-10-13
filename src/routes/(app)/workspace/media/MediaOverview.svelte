<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { formatDate } from '$lib/utils/media';
  import type { Folder, Chat } from '$lib/types/media';

  export let allFolders: Folder[] = [];
  export let allChats: Chat[] = [];

  const dispatch = createEventDispatcher<{
    'enter-folder': string;
    'enter-chat': string;
    'enter-orphans': void;
  }>();

  const enterFolder = (folderId: string) => {
    dispatch('enter-folder', folderId);
  };

  const enterChat = (chatId: string) => {
    dispatch('enter-chat', chatId);
  };

  const enterOrphans = () => {
    dispatch('enter-orphans');
  };

  const handleKeydown = (e: KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  };

  $: chatsNotInFolders = allChats.filter((c) => !(c?.folder_id || c?.folderId));
</script>

<div class="mt-5">
  <div class="mb-3 text-sm font-medium text-gray-600 dark:text-gray-300">Folders</div>
  {#if allFolders.length === 0}
    <div class="text-xs text-gray-500 dark:text-gray-400">No folders yet.</div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {#each allFolders as folder (folder.id)}
        <div 
          role="button" 
          tabindex="0" 
          class="group rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition p-4 cursor-pointer"
          on:click={() => enterFolder(folder.id)}
          on:keydown={(e) => handleKeydown(e, () => enterFolder(folder.id))}
        >
          <div class="flex items-center gap-3">
            <div class="shrink-0 w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-850 flex items-center justify-center">📁</div>
            <div class="min-w-0">
              <div class="text-sm font-medium truncate">{folder.name || '(Untitled folder)'}</div>
              <div class="text-[11px] text-gray-500 dark:text-gray-400">Updated {formatDate(folder.updated_at)}</div>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <div class="mt-8 mb-3 text-sm font-medium text-gray-600 dark:text-gray-300">Chats (not in folders)</div>
  {#if chatsNotInFolders.length === 0}
    <div class="text-xs text-gray-500 dark:text-gray-400">No chats.</div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      {#each chatsNotInFolders as chat (chat.id)}
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

  <!-- Media not in chats (tile) -->
  <div class="mt-8 mb-3 text-sm font-medium text-gray-600 dark:text-gray-300">Other</div>
  <div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
    <div 
      role="button" 
      tabindex="0" 
      class="group rounded-xl border border-gray-100 dark:border-gray-900 bg-white dark:bg-gray-900 hover:shadow-sm transition p-4 cursor-pointer"
      on:click={enterOrphans}
      on:keydown={(e) => handleKeydown(e, enterOrphans)}
    >
      <div class="flex items-center gap-3">
        <div class="shrink-0 w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-850 flex items-center justify-center">🗂️</div>
        <div class="min-w-0">
          <div class="text-sm font-medium truncate">Media not in chats</div>
          <div class="text-[11px] text-gray-500 dark:text-gray-400">Browse unlinked media</div>
        </div>
      </div>
    </div>
  </div>
</div>
