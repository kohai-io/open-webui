<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let selectedCount: number;
  export let loading: boolean = false;

  const dispatch = createEventDispatcher();

  const handleDelete = () => {
    dispatch('delete');
  };

  const handleClear = () => {
    dispatch('clear');
  };
</script>

{#if selectedCount > 0}
  <div class="mt-3 mb-2 flex flex-wrap items-center gap-2">
    <div class="text-xs sm:text-sm font-medium">{selectedCount} selected</div>
    <button
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-full bg-red-100 dark:bg-red-900/20 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/40 active:scale-95 transition-transform disabled:opacity-50"
      on:click={handleDelete}
      disabled={loading}
      aria-label="Delete selected files"
    >
      <span class="hidden xs:inline">Delete Selected</span>
      <span class="xs:hidden">Delete ({selectedCount})</span>
    </button>
    <button
      class="px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-full bg-gray-100 dark:bg-gray-850 hover:bg-gray-200 dark:hover:bg-gray-800 active:scale-95 transition-transform"
      on:click={handleClear}
      aria-label="Clear selection"
    >
      Clear
    </button>
  </div>
{/if}
