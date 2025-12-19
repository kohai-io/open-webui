<script lang="ts">
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';
	import { mediaPool, type MediaFile } from '$lib/stores/mediaPool';
	import { segments } from '$lib/stores/video';
	import type { VideoSegment } from '$lib/types/video';

	export let currentTime = 0;
	export let isPlaying = false;
	export let isSegmentDragging = false;

	const dispatch = createEventDispatcher();

	let canvasElement: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null;
	let videoElements = new Map<string, HTMLVideoElement>();
	let animationFrameId: number;
	let lastFrameTime = 0;
	let activeSegment: VideoSegment | null = null;
	let activeMediaId: string | null = null;
	let lastSyncTime = 0;

	$: sortedSegments = [...$segments].sort((a, b) => a.startTime - b.startTime);

	// Load video elements for all media in pool
	$: {
		if ($mediaPool) {
			$mediaPool.forEach(media => {
				if (media.type === 'video' && !videoElements.has(media.id)) {
					const video = document.createElement('video');
					video.src = media.url;
					video.preload = 'auto';
					videoElements.set(media.id, video);
				}
			});
		}
	}

	// Find which segment we're in - SKIP ENTIRELY during drag to prevent reactive loops
	$: if (!isSegmentDragging) {
		const segment = sortedSegments.find(s => 
			currentTime >= s.startTime && currentTime < s.endTime && s.enabled
		);
		
		if (segment?.id !== activeSegment?.id) {
			console.log('CanvasVideoPlayer: Active segment changed', {
				currentTime,
				newSegment: segment ? `${segment.startTime}-${segment.endTime}` : 'none',
				mediaId: segment?.mediaId
			});
			activeSegment = segment || null;
			activeMediaId = segment?.mediaId || null;
			lastSyncTime = 0; // Force sync on segment change
		}
		
		// Sync video time with throttling
		if (segment) {
			const now = Date.now();
			if (now - lastSyncTime > 100) { // Max 10 syncs per second
				const offset = currentTime - segment.startTime;
				const sourceTime = segment.sourceStartTime + offset;
				const video = videoElements.get(segment.mediaId);
				
				if (video && Math.abs(video.currentTime - sourceTime) > 0.1) {
					console.log('CanvasVideoPlayer: Syncing video time to', sourceTime, 'for timeline position', currentTime);
					video.currentTime = sourceTime;
					lastSyncTime = now;
				}
			}
		}
	}

	const renderFrame = (timestamp: number) => {
		if (!ctx || !canvasElement) {
			animationFrameId = requestAnimationFrame(renderFrame);
			return;
		}

		// If no active segment and playing, find next segment or stop
		if (!activeSegment && isPlaying) {
			const nextSegment = sortedSegments.find(s => s.startTime > currentTime && s.enabled);
			if (nextSegment) {
				console.log('CanvasVideoPlayer: Gap detected, jumping to next segment at', nextSegment.startTime);
				currentTime = nextSegment.startTime;
				dispatch('timeupdate', { time: currentTime });
			} else {
				console.log('CanvasVideoPlayer: No more segments, stopping playback');
				isPlaying = false;
				dispatch('playstatechange', { isPlaying: false });
			}
			animationFrameId = requestAnimationFrame(renderFrame);
			return;
		}

		// If no active segment but not playing, just clear canvas
		if (!activeSegment) {
			ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);
			animationFrameId = requestAnimationFrame(renderFrame);
			return;
		}

		const video = videoElements.get(activeSegment.mediaId);
		if (!video || video.readyState < 2) {
			animationFrameId = requestAnimationFrame(renderFrame);
			return;
		}

		// Clear canvas
		ctx.clearRect(0, 0, canvasElement.width, canvasElement.height);

		// Draw current frame
		ctx.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);

		if (isPlaying) {
			const deltaTime = timestamp - lastFrameTime;
			if (deltaTime >= 16.67) { // ~60fps
				lastFrameTime = timestamp;
				
				// Calculate new timeline position
				const offset = currentTime - activeSegment.startTime;
				const sourceTime = activeSegment.sourceStartTime + offset + (deltaTime / 1000);
				
				// Check if we've reached the end of this segment
				if (sourceTime >= activeSegment.sourceEndTime - 0.033) {
					// Find next segment by TIMELINE position (not array index)
					// sortedSegments is already sorted by startTime, so find first segment after this one
					const currentSegmentId = activeSegment.id;
					const currentEndTime = activeSegment.endTime;
					const nextSegment = sortedSegments.find(s => 
						s.startTime >= currentEndTime - 0.05 && s.id !== currentSegmentId && s.enabled
					);
					
					if (nextSegment) {
						// Jump to next segment (handles gaps automatically)
						console.log('CanvasVideoPlayer: End of segment, jumping to next at', nextSegment.startTime);
						currentTime = nextSegment.startTime;
						dispatch('timeupdate', { time: currentTime });
					} else {
						// End of timeline
						console.log('CanvasVideoPlayer: End of timeline, stopping');
						isPlaying = false;
						dispatch('playstatechange', { isPlaying: false });
					}
				} else {
					// Update current time
					currentTime += deltaTime / 1000;
					video.currentTime = sourceTime;
					dispatch('timeupdate', { time: currentTime });
				}
			}
		}

		animationFrameId = requestAnimationFrame(renderFrame);
	};

	export const play = () => {
		isPlaying = true;
		dispatch('playstatechange', { isPlaying: true });
	};

	export const pause = () => {
		isPlaying = false;
		dispatch('playstatechange', { isPlaying: false });
	};

	export const togglePlayPause = () => {
		if (isPlaying) {
			pause();
		} else {
			play();
		}
	};

	export const seekToTimelinePosition = (time: number) => {
		currentTime = Math.max(0, Math.min(time, getTimelineDuration()));
		
		const segment = sortedSegments.find(s => 
			currentTime >= s.startTime && currentTime < s.endTime
		);
		
		if (segment) {
			const offset = currentTime - segment.startTime;
			const sourceTime = segment.sourceStartTime + offset;
			const video = videoElements.get(segment.mediaId);
			
			if (video) {
				video.currentTime = sourceTime;
			}
		}
		
		dispatch('timeupdate', { time: currentTime });
	};

	const getTimelineDuration = () => {
		if (sortedSegments.length === 0) return 0;
		return Math.max(...sortedSegments.map(s => s.endTime));
	};

	onMount(() => {
		if (canvasElement) {
			ctx = canvasElement.getContext('2d');
			canvasElement.width = 1920;
			canvasElement.height = 1080;
			animationFrameId = requestAnimationFrame(renderFrame);
		}

		const duration = getTimelineDuration();
		if (duration > 0) {
			dispatch('durationchange', { duration });
		}
	});

	onDestroy(() => {
		if (animationFrameId) {
			cancelAnimationFrame(animationFrameId);
		}
		
		// Clean up video elements
		videoElements.forEach(video => {
			video.src = '';
			video.load();
		});
		videoElements.clear();
	});

	// Update duration when segments change
	$: if ($segments) {
		const duration = getTimelineDuration();
		dispatch('durationchange', { duration });
	}
</script>

<div class="canvas-video-player">
	<canvas bind:this={canvasElement} class="video-canvas"></canvas>
	
	<!-- Hidden video elements for all media -->
	{#each Array.from(videoElements.entries()) as [mediaId, video]}
		<video bind:this={video} style="display: none;" muted></video>
	{/each}
</div>

<style>
	.canvas-video-player {
		position: relative;
		width: 100%;
		height: 100%;
		background: #000;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.video-canvas {
		max-width: 100%;
		max-height: 100%;
		display: block;
	}
</style>
