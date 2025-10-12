<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { page } from '$app/stores';

	onMount(() => {
		// Redirect to welcome page if no query parameters
		const searchParams = $page.url.searchParams;
		const hasParams = Array.from(searchParams.keys()).length > 0;
		
		if (!hasParams) {
			goto('/welcome');
			return;
		}

		if (searchParams.get('error')) {
			toast.error(searchParams.get('error') || 'An unknown error occurred.');
		}
	});
</script>

<Chat />
