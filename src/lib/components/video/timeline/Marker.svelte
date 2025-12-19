<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { Marker as MarkerType } from '$lib/types/video';

	export let marker: MarkerType;
	export let pixelsPerSecond: number;

	const dispatch = createEventDispatcher();

	$: position = marker.time * pixelsPerSecond;

	const getColor = () => {
		if (marker.color) return marker.color;
		switch (marker.type) {
			case 'chapter':
				return '#3b82f6'; // blue
			case 'note':
				return '#10b981'; // green
			case 'flag':
				return '#ef4444'; // red
			default:
				return '#f59e0b'; // amber
		}
	};

	const handleClick = () => {
		dispatch('seek', { time: marker.time });
	};

	const handleDelete = (e: MouseEvent) => {
		e.stopPropagation();
		dispatch('delete', { id: marker.id });
	};
</script>

<div
	class="absolute top-0 bottom-0 cursor-pointer group z-10"
	style="left: {position}px"
	on:click={handleClick}
	role="button"
	tabindex="0"
	on:keydown={(e) => e.key === 'Enter' && handleClick()}
>
	<!-- Marker Line -->
	<div
		class="h-full w-0.5 opacity-70 group-hover:opacity-100 transition-opacity"
		style="background-color: {getColor()}"
	></div>

	<!-- Marker Flag/Icon -->
	<div
		class="absolute top-0 left-0 -translate-x-1/2 w-4 h-4 rounded-full border-2 border-white shadow-lg group-hover:scale-125 transition-transform"
		style="background-color: {getColor()}"
	>
		{#if marker.type === 'chapter'}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-full h-full text-white p-0.5"
				viewBox="0 0 24 24"
				fill="currentColor"
			>
				<path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z" />
			</svg>
		{:else if marker.type === 'flag'}
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-full h-full text-white p-0.5"
				viewBox="0 0 24 24"
				fill="currentColor"
			>
				<path d="M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6z" />
			</svg>
		{/if}
	</div>

	<!-- Marker Label (on hover) -->
	<div
		class="absolute top-5 left-0 -translate-x-1/2 bg-gray-900/95 backdrop-blur-sm text-white text-xs px-2 py-1 rounded shadow-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none border border-gray-700"
	>
		<div class="font-semibold">{marker.label}</div>
		<div class="text-gray-400 text-[10px]">
			{Math.floor(marker.time / 60)}:{Math.floor(marker.time % 60)
				.toString()
				.padStart(2, '0')}
		</div>
	</div>

	<!-- Delete Button (on hover) -->
	<button
		class="absolute top-6 left-0 -translate-x-1/2 mt-12 bg-red-600 hover:bg-red-700 text-white text-xs px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity"
		on:click={handleDelete}
		title="Delete marker"
	>
		×
	</button>
</div>
