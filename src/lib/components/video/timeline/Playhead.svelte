<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let position: number = 0;
	export let isDragging: boolean = false;
	export let currentTime: number = 0;
	export let duration: number = 0;

	const dispatch = createEventDispatcher();

	let isHovering = false;

	const handleMouseDown = (e: MouseEvent) => {
		e.stopPropagation();
		dispatch('dragstart');
	};

	const handleMouseEnter = () => {
		isHovering = true;
	};

	const handleMouseLeave = () => {
		isHovering = false;
	};
</script>

<div
	class="absolute top-0 bottom-0 bg-red-500 z-[2000] {isDragging || isHovering ? 'w-1' : 'w-0.5'}"
	style="left: {position}px; transform: translateX(-1px); transition: width 0.15s ease;"
>
	<!-- Playhead Handle -->
	<div
		class="absolute top-0 left-1/2 -translate-x-1/2 bg-red-500 rounded-full shadow-lg cursor-grab {isDragging ? 'cursor-grabbing scale-110' : ''} {isDragging || isHovering ? 'w-4 h-4' : 'w-3 h-3'}"
		style="transition: width 0.15s ease, height 0.15s ease, transform 0.15s ease;"
		on:mousedown={handleMouseDown}
		on:mouseenter={handleMouseEnter}
		on:mouseleave={handleMouseLeave}
		role="slider"
		tabindex="0"
		aria-label="Playhead"
		aria-valuemin="0"
		aria-valuemax={duration}
		aria-valuenow={currentTime}
	></div>

	<!-- Playhead Line -->
	<div class="absolute top-3 bottom-0 left-0 w-full bg-red-500 shadow-md pointer-events-none"></div>
</div>
