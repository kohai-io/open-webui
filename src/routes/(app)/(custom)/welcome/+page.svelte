<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';
	import Chat from '$lib/components/chat/Chat.svelte';

	onMount(() => {
		if (!$config?.features?.enable_welcome_page) {
			goto('/', { replaceState: true });
		}
	});
</script>

{#if $config?.features?.enable_welcome_page}
	<Chat welcome />
{/if}
