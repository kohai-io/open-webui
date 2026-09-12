<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import type ImageCanvas from '$lib/components/custom/image-canvas/ImageCanvas.svelte';
	const i18n: Writable<I18n> = getContext('i18n');
	let Canvas: typeof ImageCanvas | null = null;
	let failed = false;
	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}
		try {
			Canvas = (await import('$lib/components/custom/image-canvas/ImageCanvas.svelte')).default;
		} catch {
			failed = true;
		}
	});
</script>

{#if Canvas}
	<svelte:component this={Canvas} />
{:else}
	<p class="p-4 text-sm" role="status">
		{failed
			? $i18n.t('Unable to load the image canvas. Reload to try again.')
			: $i18n.t('Loading...')}
	</p>
{/if}
