<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let segment: any;
	export let x: number;
	export let y: number;
	export let visible: boolean = false;

	const dispatch = createEventDispatcher();

	const handleSendToModel = (e: MouseEvent) => {
		e.stopPropagation();
		dispatch('sendtomodel', { segmentId: segment.id });
		visible = false;
	};

	const handleDuplicate = (e: MouseEvent) => {
		e.stopPropagation();
		dispatch('duplicate', { segmentId: segment.id });
		visible = false;
	};

	const handleDelete = (e: MouseEvent) => {
		e.stopPropagation();
		e.preventDefault();
		console.log('SegmentContextMenu: Delete clicked for segment', segment.id);
		dispatch('delete', { segmentId: segment.id });
		visible = false;
	};

	const handleToggleEnabled = (e: MouseEvent) => {
		e.stopPropagation();
		dispatch('toggleenabled', { segmentId: segment.id });
		visible = false;
	};
</script>

{#if visible}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="fixed bg-gray-800 border border-gray-700 rounded-lg shadow-lg py-1 min-w-[200px]"
		style="left: {x}px; top: {y}px; z-index: 99999; pointer-events: auto;"
		on:click={(e) => e.stopPropagation()}
	>
		<button
			class="w-full px-4 py-2 text-left text-sm text-white hover:bg-gray-700 transition-colors flex items-center gap-2"
			on:click={handleSendToModel}
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
			</svg>
			Send to Model
		</button>

		<button
			class="w-full px-4 py-2 text-left text-sm text-white hover:bg-gray-700 transition-colors flex items-center gap-2"
			on:click={handleDuplicate}
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
				<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
			</svg>
			Duplicate Segment
		</button>

		<button
			class="w-full px-4 py-2 text-left text-sm text-white hover:bg-gray-700 transition-colors flex items-center gap-2"
			on:click={handleToggleEnabled}
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				{#if segment.enabled}
					<rect x="3" y="3" width="18" height="18" rx="2"/>
					<path d="m9 11 3 3L22 4"/>
				{:else}
					<rect x="3" y="3" width="18" height="18" rx="2"/>
				{/if}
			</svg>
			{segment.enabled ? 'Disable' : 'Enable'} Segment
		</button>

		<div class="border-t border-gray-700 my-1"></div>

		<button
			class="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-gray-700 transition-colors flex items-center gap-2"
			on:click={handleDelete}
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<path d="M3 6h18"/>
				<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
			</svg>
			Delete Segment
		</button>
	</div>
{/if}

<svelte:window on:click={() => visible = false} />
