<script lang="ts">
	import { onMount } from 'svelte';
	import { getScheduledPrompts } from '$lib/apis/scheduled-prompts';
	import ScheduledPrompts from '$lib/components/workspace/ScheduledPrompts/ScheduledPrompts.svelte';

	let scheduledPrompts: any[] | null = null;

	onMount(async () => {
		scheduledPrompts = await getScheduledPrompts(localStorage.token);
	});
</script>

{#if scheduledPrompts !== null}
	<ScheduledPrompts bind:scheduledPrompts />
{/if}
