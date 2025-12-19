<script lang="ts">
	export let time: number;
	export let pixelsPerSecond: number;
	
	$: position = time * pixelsPerSecond;
</script>

<div
	class="absolute pointer-events-none"
	style="
		left: {position}px; 
		width: 2px;
		top: 0;
		height: 100%;
		background: repeating-linear-gradient(
			to bottom,
			white 0px,
			white 4px,
			transparent 4px,
			transparent 8px
		);
		z-index: 110;
		opacity: 0.6;
	"
>
	<!-- Small indicator at top to show cut point -->
	<div 
		class="absolute top-0 left-1/2"
		style="
			width: 0;
			height: 0;
			border-left: 6px solid transparent;
			border-right: 6px solid transparent;
			border-top: 8px solid white;
			transform: translateX(-50%);
			opacity: 0.8;
		"
	></div>
</div>
