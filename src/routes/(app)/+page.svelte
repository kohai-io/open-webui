<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import Welcome from '$lib/components/welcome/Welcome.svelte';
	import { page } from '$app/stores';
	import { config } from '$lib/stores';

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
	});
</script>

{#if $config?.features?.enable_welcome_page && !$page.url.searchParams.has('models') && $page.url.searchParams.get('chat') !== 'true'}
	<Welcome />
{:else}
	<Chat />
{/if}
