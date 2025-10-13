<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import MediaCard from '$lib/components/workspace/MediaCard.svelte';
  import type { MediaFile } from '$lib/types/media';

  export let items: MediaFile[] = [];
  export let deleting: Record<string, boolean> = {};
  export let selectedMap: Record<string, boolean> = {};

  const dispatch = createEventDispatcher<{
    'preview': MediaFile;
    'chat-with': MediaFile;
    'delete': MediaFile;
    'toggle-select': string;
  }>();
</script>

<div class="mt-5 grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
  {#each items as item (item.id)}
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
