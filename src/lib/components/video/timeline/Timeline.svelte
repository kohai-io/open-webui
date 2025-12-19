<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import ThumbnailTrack from './ThumbnailTrack.svelte';
	import WaveformTrack from './WaveformTrack.svelte';
	import Playhead from './Playhead.svelte';
	import Marker from './Marker.svelte';
	import VideoSegment from './VideoSegment.svelte';
	import SegmentCutLine from './SegmentCutLine.svelte';
	import type { Marker as MarkerType, VideoSegment as VideoSegmentType } from '$lib/types/video';

	export let videoUrl: string;
	export let currentTime = 0;
	export let duration = 0;
	export let isPlaying = false;
	export let zoom = 1;
	export let pixelsPerSecond = 100;
	export let markers: MarkerType[] = [];
	export let segments: VideoSegmentType[] = [];
	export let frameRate = 30; // Default 30fps

	const dispatch = createEventDispatcher();

	let timelineContainer: HTMLElement;
	let scrollContainer: HTMLDivElement;
	let rulerContainer: HTMLDivElement;
	let timelineWidth = 0;
	let isDragging = false;
	let isPlayheadDragging = false;
	let showTimecodeTooltip = false;
	let tooltipTime = 0;
	let tooltipX = 0;
	let activeTool: 'select' | 'blade' = 'select';
	let activeSegmentId: string | null = null;
	let trimmingSegmentId: string | null = null;

	$: pixelsPerSecond = zoom * 100;
	$: sortedSegments = [...segments].sort((a, b) => a.startTime - b.startTime);
	
	// Calculate timeline width based on segments, with a minimum and maximum
	$: {
		const maxSegmentTime = segments.length > 0 
			? Math.max(...segments.map(s => s.endTime))
			: 0;
		const minWidth = 60; // At least 60 seconds visible
		const maxWidth = 10800; // Max 3 hours
		const calculatedDuration = Math.max(minWidth, Math.min(maxWidth, maxSegmentTime + 10)); // +10s padding
		timelineWidth = calculatedDuration * pixelsPerSecond;
	}
	
	$: playheadPosition = currentTime * pixelsPerSecond;
	

	const timeToPixel = (time: number) => time * pixelsPerSecond;
	const pixelToTime = (px: number) => px / pixelsPerSecond;

	const handleClick = (e: MouseEvent) => {
		// Determine which container was clicked (ruler or main timeline)
		const container = rulerContainer && e.currentTarget === rulerContainer 
			? rulerContainer 
			: scrollContainer;
			
		if (!container) return;
		
		// Allow blade tool to work even while dragging
		if (isDragging && !isPlayheadDragging && activeTool !== 'blade') {
			return;
		}

		const rect = container.getBoundingClientRect();
		const scrollOffset = container === rulerContainer ? rulerContainer.scrollLeft : scrollContainer?.scrollLeft || 0;
		const x = e.clientX - rect.left + scrollOffset;
		let time = pixelToTime(x);
		
		// Always snap to frame boundaries for frame-accurate editing
		const frameTime = 1 / frameRate;
		time = Math.round(time / frameTime) * frameTime;

		if (activeTool === 'blade') {
			handleBladeCut(time);
			activeTool = 'select';
		} else if (time >= 0 && time <= duration) {
			dispatch('seek', { time });
		}
	};

	const handleMouseDown = (e: MouseEvent) => {
		if (!isPlayheadDragging) {
			handleClick(e);
			isDragging = true;
		}
	};

	const handleMouseMove = (e: MouseEvent) => {
		if (trimmingSegmentId && scrollContainer) {
			// Handle segment trimming
			const rect = scrollContainer.getBoundingClientRect();
			const x = e.clientX - rect.left + scrollContainer.scrollLeft;
			let time = pixelToTime(x);
			
			// Snap to frame boundaries
			const frameTime = 1 / frameRate;
			time = Math.round(time / frameTime) * frameTime;
			
			// Update segment boundaries
			const newSegments = segments.map(s => {
				if (s.id === trimmingSegmentId) {
					// Determine which edge is being dragged based on proximity
					const distToStart = Math.abs(time - s.startTime);
					const distToEnd = Math.abs(time - s.endTime);
					
					if (distToStart < distToEnd) {
						// Dragging start edge - adjust both timeline and source
						const newStartTime = Math.max(0, Math.min(time, s.endTime - frameTime));
						const timelineChange = newStartTime - s.startTime;
						const newSourceStartTime = s.sourceStartTime + timelineChange;
						
						return { 
							...s, 
							startTime: newStartTime,
							sourceStartTime: Math.max(0, newSourceStartTime)
						};
					} else {
						// Dragging end edge - adjust both timeline and source
						const newEndTime = Math.min(duration, Math.max(time, s.startTime + frameTime));
						const timelineChange = newEndTime - s.endTime;
						const newSourceEndTime = s.sourceEndTime + timelineChange;
						
						return { 
							...s, 
							endTime: newEndTime,
							sourceEndTime: Math.min(duration, newSourceEndTime)
						};
					}
				}
				return s;
			});
			
			dispatch('segmentschange', { segments: newSegments });
		} else if (isDragging || isPlayheadDragging) {
			if (scrollContainer) {
				const rect = scrollContainer.getBoundingClientRect();
				const x = e.clientX - rect.left + scrollContainer.scrollLeft;
				tooltipTime = pixelToTime(x);
				tooltipX = e.clientX - rect.left;
				showTimecodeTooltip = true;
			}
			handleClick(e);
		}
	};

	const handleMouseUp = () => {
		isDragging = false;
		isPlayheadDragging = false;
		showTimecodeTooltip = false;
	};

	const handlePlayheadDragStart = () => {
		isPlayheadDragging = true;
		isDragging = true;
	};

	onMount(() => {
		document.addEventListener('mousemove', handleMouseMove);
		document.addEventListener('mouseup', handleMouseUp);

		return () => {
			document.removeEventListener('mousemove', handleMouseMove);
			document.removeEventListener('mouseup', handleMouseUp);
		};
	});

	const handleZoom = (delta: number) => {
		const newZoom = Math.max(0.5, Math.min(5, zoom + delta));
		dispatch('zoomchange', { zoom: newZoom });
	};

	const handlePlayPause = () => {
		dispatch('playpause');
	};

	const handleStop = () => {
		dispatch('seek', { time: 0 });
		dispatch('playpause'); // Pause if playing
	};

	const handleSkipBackward = () => {
		// Find current segment
		const currentSegment = segments.find(s => 
			currentTime >= s.startTime && currentTime < s.endTime && s.enabled
		);
		
		if (currentSegment) {
			// If more than 1 second into segment, jump to segment start
			if (currentTime - currentSegment.startTime > 1.0) {
				dispatch('seek', { time: currentSegment.startTime });
				return;
			}
			
			// Otherwise, find previous segment
			const sortedSegs = [...segments].sort((a, b) => a.startTime - b.startTime).filter(s => s.enabled);
			const currentIndex = sortedSegs.findIndex(s => s.id === currentSegment.id);
			
			if (currentIndex > 0) {
				// Jump to start of previous segment
				dispatch('seek', { time: sortedSegs[currentIndex - 1].startTime });
				return;
			}
		}
		
		// Default: jump back 5 seconds
		const newTime = Math.max(0, currentTime - 5);
		dispatch('seek', { time: newTime });
	};

	const handleSkipForward = () => {
		// Find current segment
		const currentSegment = segments.find(s => 
			currentTime >= s.startTime && currentTime < s.endTime && s.enabled
		);
		
		if (currentSegment) {
			// Jump to next segment
			const sortedSegs = [...segments].sort((a, b) => a.startTime - b.startTime).filter(s => s.enabled);
			const currentIndex = sortedSegs.findIndex(s => s.id === currentSegment.id);
			
			if (currentIndex >= 0 && currentIndex < sortedSegs.length - 1) {
				dispatch('seek', { time: sortedSegs[currentIndex + 1].startTime });
				return;
			}
		}
		
		// Default: jump forward 5 seconds
		const newTime = Math.min(duration, currentTime + 5);
		dispatch('seek', { time: newTime });
	};

	const handleAddMarker = () => {
		dispatch('addmarker', { time: currentTime });
	};

	const handleToggleBladeTool = () => {
		activeTool = activeTool === 'blade' ? 'select' : 'blade';
	};

	const handleBladeCut = (time: number) => {
		const segmentIndex = segments.findIndex(s => time >= s.startTime && time < s.endTime);
		
		if (segmentIndex !== -1) {
			const segment = segments[segmentIndex];
			
			// Don't cut if too close to start or end (< 1 frame)
			const minCutDistance = 1 / 30; // 1 frame at 30fps
			if (time - segment.startTime < minCutDistance || segment.endTime - time < minCutDistance) {
				return;
			}
			
			const newSegments = [...segments];
			
			// Calculate source offset for the cut
			const timelineOffset = time - segment.startTime;
			const sourceOffset = segment.sourceStartTime + timelineOffset;
			
			// Split segment into two, preserving source timecodes and mediaId
			const leftSegment: VideoSegmentType = {
				id: `segment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
				mediaId: segment.mediaId,
				startTime: segment.startTime,
				endTime: time,
				sourceStartTime: segment.sourceStartTime,
				sourceEndTime: sourceOffset,
				enabled: true
			};
			
			const rightSegment: VideoSegmentType = {
				id: `segment-${Date.now() + 1}-${Math.random().toString(36).substr(2, 9)}`,
				mediaId: segment.mediaId,
				startTime: time,
				endTime: segment.endTime,
				sourceStartTime: sourceOffset,
				sourceEndTime: segment.sourceEndTime,
				enabled: true
			};
			
			console.log('✂️ Blade cut at timeline', time.toFixed(2), 'created:');
			console.log('  Left:', {
				timeline: `${leftSegment.startTime.toFixed(2)}-${leftSegment.endTime.toFixed(2)}`,
				source: `${leftSegment.sourceStartTime.toFixed(2)}-${leftSegment.sourceEndTime.toFixed(2)}`
			});
			console.log('  Right:', {
				timeline: `${rightSegment.startTime.toFixed(2)}-${rightSegment.endTime.toFixed(2)}`,
				source: `${rightSegment.sourceStartTime.toFixed(2)}-${rightSegment.sourceEndTime.toFixed(2)}`
			});
			
			newSegments.splice(segmentIndex, 1, leftSegment, rightSegment);
			dispatch('segmentschange', { segments: newSegments });
		}
	};

	const handleSegmentTrimStart = (e: CustomEvent<{ segmentId: string }>) => {
		trimmingSegmentId = e.detail.segmentId;
	};

	const handleSegmentTrimEnd = () => {
		trimmingSegmentId = null;
	};

	const handleSegmentSelect = (e: CustomEvent<{ segmentId: string }>) => {
		activeSegmentId = e.detail.segmentId;
	};

	const handleSegmentMove = (e: CustomEvent<{ segmentId: string; startTime: number; endTime: number }>) => {
		const segment = segments.find(s => s.id === e.detail.segmentId);
		if (!segment) return;
		
		console.log('Timeline: BEFORE move', {
			id: segment.id.slice(-4),
			oldTimeline: `${segment.startTime.toFixed(1)}-${segment.endTime.toFixed(1)}`,
			oldSource: `${segment.sourceStartTime.toFixed(1)}-${segment.sourceEndTime.toFixed(1)}`,
			newTimeline: `${e.detail.startTime.toFixed(1)}-${e.detail.endTime.toFixed(1)}`
		});
		
		let newStartTime = e.detail.startTime;
		let newEndTime = e.detail.endTime;
		
		// Collision detection - snap to adjacent segments
		const snapThreshold = 0.3; // seconds - reduced for less aggressive snapping
		const otherSegments = segments.filter(s => s.id !== e.detail.segmentId);
		
		for (const other of otherSegments) {
			// Check if we're close to another segment's end
			if (Math.abs(newStartTime - other.endTime) < snapThreshold) {
				const duration = newEndTime - newStartTime;
				newStartTime = other.endTime;
				newEndTime = newStartTime + duration;
			}
			// Check if we're close to another segment's start
			if (Math.abs(newEndTime - other.startTime) < snapThreshold) {
				const duration = newEndTime - newStartTime;
				newEndTime = other.startTime;
				newStartTime = newEndTime - duration;
			}
		}
		
		const newSegments = segments.map(s => {
			if (s.id === e.detail.segmentId) {
				const updated = {
					...s,
					startTime: newStartTime,
					endTime: newEndTime,
					// EXPLICITLY preserve source times
					sourceStartTime: s.sourceStartTime,
					sourceEndTime: s.sourceEndTime
				};
				console.log('Timeline: AFTER move', {
					id: updated.id.slice(-4),
					timeline: `${updated.startTime.toFixed(1)}-${updated.endTime.toFixed(1)}`,
					source: `${updated.sourceStartTime.toFixed(1)}-${updated.sourceEndTime.toFixed(1)}`
				});
				return updated;
			}
			return s;
		});
		dispatch('segmentschange', { segments: newSegments });
	};

	const handleSegmentMoveStart = (e: CustomEvent<{ segmentId: string }>) => {
		// DO NOT set trimmingSegmentId here - that's only for edge trimming!
		// Move operations are handled by handleSegmentMove which preserves source times
		dispatch('dragstatechange', { isDragging: true });
	};

	const handleSegmentMoveEnd = () => {
		// trimmingSegmentId was never set during move, so don't clear it
		dispatch('dragstatechange', { isDragging: false });
		
		// Log segments after drag to debug source time issues
		console.log('Timeline: Drag ended, final segment state:', 
			segments.map(s => ({
				id: s.id.slice(-4),
				mediaId: s.mediaId.slice(-4),
				timeline: `${s.startTime.toFixed(1)}-${s.endTime.toFixed(1)}`,
				source: `${s.sourceStartTime.toFixed(1)}-${s.sourceEndTime.toFixed(1)}`
			}))
		);
	};

	const handleDeleteMarker = (e: CustomEvent<{ id: string }>) => {
		dispatch('deletemarker', { id: e.detail.id });
	};

	const handleMarkerSeek = (e: CustomEvent<{ time: number }>) => {
		dispatch('seek', { time: e.detail.time });
	};

	// Format time as HH:MM:SS:FF
	const formatTime = (seconds: number) => {
		const totalFrames = Math.floor(seconds * frameRate);
		const frames = totalFrames % frameRate;
		const totalSeconds = Math.floor(seconds);
		const s = totalSeconds % 60;
		const totalMinutes = Math.floor(totalSeconds / 60);
		const m = totalMinutes % 60;
		const h = Math.floor(totalMinutes / 60);
		return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}:${frames.toString().padStart(2, '0')}`;
	};

	// Generate per-frame tick marks with zoom-adaptive density
	$: timeMarkers = (() => {
		if (!duration || duration === 0) {
			return { frames: [] };
		}
		
		const totalFrames = Math.ceil(duration * frameRate);
		const frames = [];
		
		// Determine which tick marks to show based on zoom level
		// At low zoom, skip intermediate frames to avoid clutter
		const pixelsPerFrame = pixelsPerSecond / frameRate;
		
		for (let frame = 0; frame <= totalFrames; frame++) {
			const time = frame / frameRate;
			if (time > duration) break;
			
			// Determine tick height and whether to render based on frame position and zoom
			let height = 'short';
			let showLabel = false;
			let shouldRender = false;
			
			if (frame % frameRate === 0) {
				// Every second - always show with label
				height = 'tall';
				showLabel = true;
				shouldRender = true;
			} else if (frame % (frameRate / 2) === 0) {
				// Every half second - show at zoom >= 1.0x
				height = 'medium';
				shouldRender = zoom >= 1.0;
			} else if (frame % 10 === 0) {
				// Every 10 frames - show at zoom >= 1.5x
				height = 'small';
				shouldRender = zoom >= 1.5;
			} else if (frame % 5 === 0) {
				// Every 5 frames - show at zoom >= 2.0x
				height = 'small';
				shouldRender = zoom >= 2.0;
			} else {
				// Individual frames - show at zoom >= 3.0x
				height = 'short';
				shouldRender = zoom >= 3.0;
			}
			
			if (shouldRender) {
				frames.push({ time, frame, height, showLabel });
			}
		}
		
		return { frames };
	})();

	$: {
		if (scrollContainer && isPlaying) {
			const containerWidth = scrollContainer.clientWidth;
			const scrollLeft = scrollContainer.scrollLeft;
			const playheadScreenPos = playheadPosition - scrollLeft;

			if (playheadScreenPos > containerWidth * 0.8) {
				scrollContainer.scrollLeft = playheadPosition - containerWidth * 0.5;
			}
		}
	}
</script>

<div class="flex flex-col h-full bg-gray-800" bind:this={timelineContainer} style="max-width: 100%; contain: layout;">
	<!-- Timeline Controls -->
	<div class="flex items-center justify-between p-2 border-b border-gray-700 bg-gray-800">
		<div class="flex items-center gap-2">
			<!-- Stop -->
			<button
				on:click={handleStop}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors text-white"
				title="Stop (Home)"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="currentColor"
				>
					<rect x="6" y="6" width="12" height="12" />
				</svg>
			</button>

			<!-- Skip Backward -->
			<button
				on:click={handleSkipBackward}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors text-white"
				title="Skip Back 5s (←)"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M11 19l-7-7 7-7" />
					<path d="M18 19l-7-7 7-7" />
				</svg>
			</button>

			<!-- Play/Pause -->
			<button
				on:click={handlePlayPause}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors text-white"
				title={isPlaying ? 'Pause' : 'Play'}
			>
				{#if isPlaying}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						viewBox="0 0 24 24"
						fill="currentColor"
					>
						<rect x="6" y="4" width="4" height="16" />
						<rect x="14" y="4" width="4" height="16" />
					</svg>
				{:else}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						viewBox="0 0 24 24"
						fill="currentColor"
					>
						<polygon points="5 3 19 12 5 21 5 3" />
					</svg>
				{/if}
			</button>

			<!-- Skip Forward -->
			<button
				on:click={handleSkipForward}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors text-white"
				title="Skip Forward 5s (→)"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M13 5l7 7-7 7" />
					<path d="M6 5l7 7-7 7" />
				</svg>
			</button>

			<div class="w-px h-6 bg-gray-600"></div>

			<!-- Time Display -->
			<span class="text-sm font-mono text-gray-300 min-w-[80px]">
				{formatTime(currentTime)}
			</span>

			<div class="w-px h-6 bg-gray-600"></div>

			<!-- Zoom Controls -->
			<button
				on:click={() => handleZoom(-0.5)}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors text-white"
				title="Zoom Out"
				disabled={zoom <= 0.5}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<circle cx="11" cy="11" r="8" />
					<line x1="21" y1="21" x2="16.65" y2="16.65" />
					<line x1="8" y1="11" x2="14" y2="11" />
				</svg>
			</button>

			<span class="text-sm text-gray-400 min-w-[40px] text-center">{zoom.toFixed(1)}x</span>

			<button
				on:click={() => handleZoom(0.5)}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors text-white"
				title="Zoom In"
				disabled={zoom >= 5}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<circle cx="11" cy="11" r="8" />
					<line x1="21" y1="21" x2="16.65" y2="16.65" />
					<line x1="11" y1="8" x2="11" y2="14" />
					<line x1="8" y1="11" x2="14" y2="11" />
				</svg>
			</button>

			<div class="w-px h-6 bg-gray-600 ml-2"></div>

			<!-- Blade Tool -->
			<button
				on:click={handleToggleBladeTool}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors {activeTool === 'blade' ? 'bg-blue-600 text-white' : 'text-white'} ml-2"
				title="Blade Tool (C)"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M21 8L12 17l-3-3" />
					<path d="M3 12l9-9" />
					<line x1="12" y1="3" x2="17" y2="8" />
				</svg>
			</button>

			<!-- Add Marker -->
			<button
				on:click={handleAddMarker}
				class="p-2 hover:bg-gray-700 rounded-lg transition-colors text-white"
				title="Add Marker (M)"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M14.4 6L14 4H5v17h2v-7h5.6l.4 2h7V6z" />
				</svg>
			</button>
		</div>

		<div class="text-xs text-gray-400">
			{markers.length} marker{markers.length !== 1 ? 's' : ''}
		</div>

		<div class="text-sm text-gray-400">
			Duration: {formatTime(duration)}
		</div>
	</div>

	<!-- Time Ruler with Frame Markers -->
	<div 
		bind:this={rulerContainer}
		class="h-10 bg-gray-900 border-b border-gray-700 relative overflow-x-auto overflow-y-hidden flex-shrink-0"
		style="scrollbar-width: thin;"
		on:mousedown={handleMouseDown}
		on:scroll={() => {
			if (scrollContainer && rulerContainer) {
				scrollContainer.scrollLeft = rulerContainer.scrollLeft;
			}
		}}
	>
		<div
			class="relative h-full"
			style="width: {timelineWidth}px; background: linear-gradient(to bottom, rgb(31, 41, 55), rgb(17, 24, 39));"
		>
			<!-- Per-frame tick marks with alternating heights -->
			{#each timeMarkers.frames as marker}
				<div
					class="absolute bottom-0 flex flex-col-reverse items-start pointer-events-none select-none"
					style="left: {timeToPixel(marker.time)}px;"
				>
					<!-- Tick mark with varying height -->
					{#if marker.height === 'tall'}
						<div class="w-0.5 h-6 bg-gray-200"></div>
					{:else if marker.height === 'medium'}
						<div class="w-px h-4 bg-gray-400"></div>
					{:else if marker.height === 'small'}
						<div class="w-px h-3 bg-gray-500"></div>
					{:else}
						<div class="w-px h-2 bg-gray-600"></div>
					{/if}
					
					<!-- Timecode label for tall markers (every second) -->
					{#if marker.showLabel}
						<span class="text-[9px] leading-none text-gray-100 font-mono mb-1 ml-0.5 whitespace-nowrap select-none">{formatTime(marker.time)}</span>
					{/if}
				</div>
			{/each}
		</div>
	</div>

	<!-- Timeline Tracks Container -->
	<div
		bind:this={scrollContainer}
		class="flex-1 overflow-x-auto relative bg-gray-900 {activeTool === 'blade' ? 'cursor-crosshair' : 'cursor-default'}"
		on:mousedown={handleMouseDown}
		on:scroll={() => {
			if (scrollContainer && rulerContainer) {
				rulerContainer.scrollLeft = scrollContainer.scrollLeft;
			}
		}}
		role="slider"
		tabindex="0"
		aria-label="Timeline scrubber"
		aria-valuemin="0"
		aria-valuemax={duration}
		aria-valuenow={currentTime}
		style="transform: none; zoom: 1; overflow-y: visible !important;"
	>
		<div style="width: {timelineWidth}px; height: 180px; transform: none; position: relative;" class="relative">
			<!-- Background layer: Tracks with lower z-index -->
			<div style="position: relative; z-index: 0; height: 180px;">
				<!-- Thumbnail Track -->
				<ThumbnailTrack {videoUrl} {duration} {pixelsPerSecond} {zoom} {segments} />

				<!-- Waveform Track -->
				<WaveformTrack {videoUrl} {duration} {pixelsPerSecond} {segments} />
			</div>

			<!-- Foreground layer: Segments with higher z-index, absolutely positioned to cover tracks -->
			<div style="position: absolute; top: 0; left: 0; right: 0; height: 180px; z-index: 1000; pointer-events: none;">
				<!-- Video Segments -->
				{#each segments as segment (segment.id)}
					<VideoSegment
						{segment}
						{pixelsPerSecond}
						{duration}
						{frameRate}
						{activeTool}
						on:trimstart={handleSegmentTrimStart}
						on:trimend={handleSegmentTrimEnd}
						on:select={handleSegmentSelect}
						on:move={handleSegmentMove}
						on:movestart={handleSegmentMoveStart}
						on:moveend={handleSegmentMoveEnd}
					/>
				{/each}
				
				<!-- Cut line indicators only where segments are actually adjacent -->
				{#each sortedSegments as segment, i}
					{#if i < sortedSegments.length - 1}
						{@const nextSegment = sortedSegments[i + 1]}
						{#if Math.abs(segment.endTime - nextSegment.startTime) < 0.01}
							<SegmentCutLine time={segment.endTime} {pixelsPerSecond} />
						{/if}
					{/if}
				{/each}
			</div>

			<!-- Markers -->
			{#each markers as marker (marker.id)}
				<Marker 
					{marker} 
					{pixelsPerSecond}
					on:seek={handleMarkerSeek}
					on:delete={handleDeleteMarker}
				/>
			{/each}

			<!-- Playhead -->
			<Playhead 
				position={playheadPosition} 
				isDragging={isPlayheadDragging} 
				{currentTime}
				{duration}
				on:dragstart={handlePlayheadDragStart} 
			/>
			
			<!-- Timecode Tooltip during drag -->
			{#if showTimecodeTooltip && scrollContainer}
				<div
					class="absolute z-30 pointer-events-none"
					style="left: {tooltipX}px; top: -32px; transform: translateX(-50%);"
				>
					<div class="bg-blue-600 text-white text-xs font-mono px-2 py-1 rounded shadow-lg whitespace-nowrap">
						{formatTime(tooltipTime)}
					</div>
					<div class="w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-blue-600 mx-auto"></div>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	::-webkit-scrollbar {
		height: 12px;
	}

	::-webkit-scrollbar-track {
		background: #1f2937;
	}

	::-webkit-scrollbar-thumb {
		background: #4b5563;
		border-radius: 6px;
	}

	::-webkit-scrollbar-thumb:hover {
		background: #6b7280;
	}
</style>
