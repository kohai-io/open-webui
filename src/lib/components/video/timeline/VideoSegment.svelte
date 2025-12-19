<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { VideoSegment } from '$lib/types/video';
	import { mediaPool } from '$lib/stores/mediaPool';

	export let segment: VideoSegment;
	export let pixelsPerSecond: number;
	export let duration: number;
	export let frameRate = 30;
	export let activeTool: 'select' | 'blade' = 'select';
	export let zoom = 1.0;

	const dispatch = createEventDispatcher();
	
	let thumbnails: { time: number; dataUrl: string }[] = [];
	let generating = false;
	
	$: mediaFile = $mediaPool.find(m => m.id === segment.mediaId);
	$: segmentDuration = segment.sourceEndTime - segment.sourceStartTime;
	$: startPosition = segment.startTime * pixelsPerSecond;
	$: endPosition = segment.endTime * pixelsPerSecond;
	$: segmentWidth = (segment.endTime - segment.startTime) * pixelsPerSecond;

	let isDraggingStart = false;
	let isDraggingEnd = false;
	let isDraggingSegment = false;
	let isHoveringStart = false;
	let isHoveringEnd = false;
	let dragStartX = 0;
	let dragStartTime = 0;
	let dragStartDuration = 0;

	const handleStartDragStart = (e: MouseEvent) => {
		e.stopPropagation();
		isDraggingStart = true;
		dispatch('trimstart', { segmentId: segment.id });
	};

	const handleEndDragStart = (e: MouseEvent) => {
		e.stopPropagation();
		isDraggingEnd = true;
		dispatch('trimstart', { segmentId: segment.id });
	};

	const handleSegmentClick = (e: MouseEvent | KeyboardEvent) => {
		// Don't stop propagation if blade tool is active - let timeline handle the cut
		if (activeTool === 'blade') {
			return;
		}
		e.stopPropagation();
		dispatch('select', { segmentId: segment.id });
	};

	const handleSegmentDragStart = (e: MouseEvent) => {
		// Only allow drag if select tool is active
		if (activeTool !== 'select') return;
		
		e.stopPropagation();
		e.preventDefault();
		isDraggingSegment = true;
		dragStartX = e.clientX;
		dragStartTime = segment.startTime;
		dragStartDuration = segment.endTime - segment.startTime;
		console.log('Drag start:', { startX: dragStartX, startTime: dragStartTime });
		dispatch('movestart', { segmentId: segment.id });
	};

	const handleSegmentDragMove = (e: MouseEvent) => {
		if (!isDraggingSegment) return;
		
		const deltaX = e.clientX - dragStartX;
		const deltaTime = deltaX / pixelsPerSecond;
		
		// Snap to 0.1 second intervals for smoother dragging
		const snapInterval = 0.1;
		const rawNewStartTime = dragStartTime + deltaTime;
		const snappedStartTime = Math.round(rawNewStartTime / snapInterval) * snapInterval;
		
		// Use stored duration from drag start, not current reactive segment values
		const newStartTime = Math.max(0, snappedStartTime);
		
		dispatch('move', {
			segmentId: segment.id,
			startTime: newStartTime,
			endTime: newStartTime + dragStartDuration
		});
	};

	const handleSegmentDragEnd = () => {
		if (isDraggingSegment) {
			isDraggingSegment = false;
			dispatch('moveend', { segmentId: segment.id });
		}
	};

	const handleContextMenu = (e: MouseEvent) => {
		e.preventDefault();
		e.stopPropagation();
		dispatch('contextmenu', { 
			segmentId: segment.id,
			x: e.clientX,
			y: e.clientY
		});
	};

	// Generate thumbnails for this segment
	const generateSegmentThumbnails = async () => {
		if (!mediaFile?.url || generating || segmentDuration === 0) return;

		generating = true;
		thumbnails = [];

		try {
			const video = document.createElement('video');
			video.src = mediaFile.url;
			video.crossOrigin = 'anonymous';

			await new Promise<void>((resolve, reject) => {
				video.onloadedmetadata = () => resolve();
				video.onerror = () => reject(new Error('Failed to load video'));
			});

			const canvas = document.createElement('canvas');
			const ctx = canvas.getContext('2d');
			if (!ctx) return;

			// Ultra high-quality thumbnail dimensions - 16:9 aspect ratio, 4x resolution for maximum sharpness
			canvas.width = 480;
			canvas.height = 270;

			// Calculate how many thumbnails to tile edge-to-edge across segment width
			const thumbnailDisplayWidth = 110; // Display width in pixels
			const thumbnailCount = Math.max(1, Math.ceil(segmentWidth / thumbnailDisplayWidth));
			const interval = segmentDuration / thumbnailCount;

			for (let i = 0; i < thumbnailCount; i++) {
				// Calculate time in the source video (not timeline)
				const sourceTime = segment.sourceStartTime + (i * interval);
				
				// Frame-accurate time snapping
				const frame = Math.round(sourceTime * frameRate);
				const snappedTime = frame / frameRate;

				video.currentTime = snappedTime;
				await new Promise<void>((resolve) => {
					video.onseeked = () => resolve();
				});

				// Enable image smoothing for better quality
				ctx.imageSmoothingEnabled = true;
				ctx.imageSmoothingQuality = 'high';
				ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
				const dataUrl = canvas.toDataURL('image/jpeg', 0.92);

				// Store with timeline position (offset from segment start)
				const timelineOffset = i * interval;
				thumbnails = [...thumbnails, { time: timelineOffset, dataUrl }];
			}
		} catch (error) {
			console.error('Error generating segment thumbnails:', error);
		} finally {
			generating = false;
		}
	};

	// Generate thumbnails when segment or zoom changes
	$: if (mediaFile?.url && segmentWidth > 50 && zoom > 0) {
		generateSegmentThumbnails();
	}
</script>

<svelte:window
	on:mouseup={() => {
		if (isDraggingStart || isDraggingEnd) {
			dispatch('trimend', { segmentId: segment.id });
		}
		isDraggingStart = false;
		isDraggingEnd = false;
		handleSegmentDragEnd();
	}}
	on:mousemove={handleSegmentDragMove}
/>

<div
	class="absolute group pointer-events-auto"
	class:cursor-grab={activeTool === 'select' && !isDraggingSegment}
	class:cursor-grabbing={isDraggingSegment}
	class:cursor-pointer={activeTool === 'blade'}
	style="
		left: {startPosition}px; 
		width: {segmentWidth}px; 
		top: 0;
		height: 100%;
		background: {segment.enabled ? 'rgba(59, 130, 246, 0.5)' : 'rgba(107, 114, 128, 0.6)'};
		border: 4px solid {segment.enabled ? '#3b82f6' : '#6b7280'};
		z-index: 100;
		position: absolute;
	"
	on:mousedown={handleSegmentDragStart}
	on:click={handleSegmentClick}
	on:contextmenu={handleContextMenu}
	on:keydown={(e) => e.key === 'Enter' && handleSegmentClick(e)}
	role="button"
	tabindex="0"
>
	<!-- Keyframe thumbnails -->
	{#if thumbnails.length > 0 && segment.enabled}
		<div class="absolute inset-0 overflow-hidden pointer-events-none">
			{#each thumbnails as thumbnail, i}
				<div
					class="absolute top-[4px] bottom-[4px] border border-gray-700/40 overflow-hidden shadow-md bg-black"
					style="left: {i * 110}px; width: 110px;"
				>
					<img
						src={thumbnail.dataUrl}
						alt="Keyframe {i + 1}"
						class="w-full h-full object-cover"
						style="image-rendering: auto;"
						draggable="false"
					/>
				</div>
			{/each}
		</div>
	{/if}

	<!-- Segment enabled/disabled indicator -->
	{#if !segment.enabled}
		<div class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
			<div class="text-xs text-gray-500 bg-gray-800/90 px-2 py-1 rounded border border-gray-700">
				Disabled
			</div>
		</div>
	{/if}

	<!-- Start Trim Handle -->
	<div
		class="absolute left-0 top-0 bottom-0 cursor-ew-resize hover:bg-blue-500 transition-colors {isDraggingStart ? 'bg-blue-400' : 'bg-blue-600'}"
		style="width: {isDraggingStart ? '16px' : '12px'}; z-index: 10; border-right: 1px solid #60a5fa;"
		on:mousedown={handleStartDragStart}
		on:mouseenter={() => isHoveringStart = true}
		on:mouseleave={() => isHoveringStart = false}
		role="slider"
		tabindex="0"
		aria-label="Trim segment start"
		aria-valuemin={0}
		aria-valuemax={duration}
		aria-valuenow={segment.startTime}
	>
		<div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-10 bg-white/80"></div>
	</div>

	<!-- Segment Content Area -->
	<div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
		<div class="text-xs text-white bg-black/80 px-3 py-1.5 rounded border border-blue-500/50">
			{(segment.endTime - segment.startTime).toFixed(2)}s
		</div>
	</div>

	<!-- End Trim Handle -->
	<div
		class="absolute right-0 top-0 bottom-0 cursor-ew-resize hover:bg-blue-500 transition-colors {isDraggingEnd ? 'bg-blue-400' : 'bg-blue-600'}"
		style="width: {isDraggingEnd ? '16px' : '12px'}; z-index: 10; border-left: 1px solid #60a5fa;"
		on:mousedown={handleEndDragStart}
		on:mouseenter={() => isHoveringEnd = true}
		on:mouseleave={() => isHoveringEnd = false}
		role="slider"
		tabindex="0"
		aria-label="Trim segment end"
		aria-valuemin={0}
		aria-valuemax={duration}
		aria-valuenow={segment.endTime}
	>
		<div class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-10 bg-white/80"></div>
	</div>
</div>
