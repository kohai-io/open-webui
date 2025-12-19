<script lang="ts">
	import { onMount } from 'svelte';
	import CanvasVideoPlayer from './CanvasVideoPlayer.svelte';
	import Timeline from './timeline/Timeline.svelte';
	import MediaPool from './MediaPool.svelte';
	import { videoState, timelineState, markers, segments } from '$lib/stores/video';
	import { mediaPool, type MediaFile } from '$lib/stores/mediaPool';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import type { Marker, VideoSegment } from '$lib/types/video';
	import { toast } from 'svelte-sonner';

	export let videoId: string;

	let videoPlayerComponent: any = null;
	let videoUrl = '';
	let initialMediaId = '';

	$: videoUrl = `${WEBUI_API_BASE_URL}/files/${videoId}/content`;

	// Add initial video to media pool on mount
	onMount(async () => {
		initialMediaId = `media-${Date.now()}`;
		
		const video = document.createElement('video');
		video.src = videoUrl;
		
		await new Promise(resolve => {
			video.onloadedmetadata = () => {
				const media: MediaFile = {
					id: initialMediaId,
					name: 'Video',
					type: 'video',
					url: videoUrl,
					duration: video.duration,
					width: video.videoWidth,
					height: video.videoHeight
				};
				
				mediaPool.addMedia(media);
				
				// Create initial segment
				if ($segments.length === 0) {
					const defaultSegment: VideoSegment = {
						id: `segment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
						mediaId: initialMediaId,
						startTime: 0,
						endTime: video.duration,
						sourceStartTime: 0,
						sourceEndTime: video.duration,
						enabled: true
					};
					segments.set([defaultSegment]);
				}
				
				resolve(null);
			};
		});
	});

	const handleVideoTimeUpdate = (e: CustomEvent<{ time: number }>) => {
		videoState.update((s) => ({ ...s, currentTime: e.detail.time }));
	};

	const handleVideoDurationChange = (e: CustomEvent<{ duration: number }>) => {
		videoState.update((s) => ({ ...s, duration: e.detail.duration }));
	};

	const handleVideoPlayStateChange = (e: CustomEvent<{ isPlaying: boolean }>) => {
		videoState.update((s) => ({ ...s, isPlaying: e.detail.isPlaying }));
	};

	const handleTimelineSeek = (e: CustomEvent<{ time: number }>) => {
		if (videoPlayerComponent?.seekToTimelinePosition) {
			videoPlayerComponent.seekToTimelinePosition(e.detail.time);
		}
	};

	const handlePlayPause = () => {
		if (videoPlayerComponent) {
			videoPlayerComponent.togglePlayPause();
		}
	};

	const handleAddMediaToTimeline = (e: CustomEvent<{ media: MediaFile }>) => {
		const media = e.detail.media;
		const duration = media.duration || 5;
		
		// Find end of timeline
		const timelineEnd = $segments.length > 0 
			? Math.max(...$segments.map(s => s.endTime))
			: 0;
		
		// Create new segment at end of timeline
		const newSegment: VideoSegment = {
			id: `segment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
			mediaId: media.id,
			startTime: timelineEnd,
			endTime: timelineEnd + duration,
			sourceStartTime: 0,
			sourceEndTime: duration,
			enabled: true
		};
		
		segments.update(s => [...s, newSegment]);
		toast.success(`Added ${media.name} to timeline`);
	};

	const handleAddMarker = (e: CustomEvent<{ time: number }>) => {
		const time = e.detail.time;
		const label = prompt('Marker label:', `Marker at ${formatTime(time)}`);
		
		if (label) {
			const newMarker: Marker = {
				id: `marker-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
				time,
				label,
				type: 'chapter'
			};
			markers.update(m => [...m, newMarker]);
			toast.success('Marker added');
		}
	};

	const handleDeleteMarker = (e: CustomEvent<{ id: string }>) => {
		markers.update(m => m.filter(marker => marker.id !== e.detail.id));
		toast.success('Marker deleted');
	};

	const handleSegmentsChange = (e: CustomEvent<{ segments: VideoSegment[] }>) => {
		segments.set(e.detail.segments);
	};

	const formatTime = (seconds: number) => {
		const m = Math.floor(seconds / 60);
		const s = Math.floor(seconds % 60);
		return `${m}:${s.toString().padStart(2, '0')}`;
	};

	// Keyboard shortcut for adding markers
	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'M' || e.key === 'm') {
			if (!e.ctrlKey && !e.metaKey && !e.altKey) {
				e.preventDefault();
				handleAddMarker(new CustomEvent('addmarker', { detail: { time: $videoState.currentTime } }));
			}
		}
	};

	onMount(() => {
		window.addEventListener('keydown', handleKeydown);
		return () => {
			window.removeEventListener('keydown', handleKeydown);
		};
	});
</script>

<div class="flex flex-col h-full bg-gray-900" style="max-width: 100%; width: 100%; overflow-x: hidden; overflow-y: hidden; position: relative; isolation: isolate;">
	<!-- Video Player Section (50% height) -->
	<div class="flex-[3] flex flex-col items-center justify-center bg-black border-b border-gray-700" style="max-width: 100%; overflow: hidden;">
		<CanvasVideoPlayer
			bind:this={videoPlayerComponent}
			bind:currentTime={$videoState.currentTime}
			bind:isPlaying={$videoState.isPlaying}
			on:timeupdate={handleVideoTimeUpdate}
			on:durationchange={handleVideoDurationChange}
			on:playstatechange={handleVideoPlayStateChange}
		/>
	</div>

	<!-- Timeline Section (30% height) -->
	<div class="flex-[2] flex flex-col bg-gray-800" style="max-width: 100%; overflow: hidden; contain: layout;">
		<Timeline
			{videoUrl}
			currentTime={$videoState.currentTime}
			duration={$videoState.duration}
			isPlaying={$videoState.isPlaying}
			zoom={$timelineState.zoom}
			markers={$markers}
			segments={$segments}
			on:seek={handleTimelineSeek}
			on:playpause={handlePlayPause}
			on:zoomchange={(e) => timelineState.update((s) => ({ ...s, zoom: e.detail.zoom }))}
			on:addmarker={handleAddMarker}
			on:deletemarker={handleDeleteMarker}
			on:segmentschange={handleSegmentsChange}
		/>
	</div>

	<!-- Media Pool Section (20% height) -->
	<MediaPool on:addtotimeline={handleAddMediaToTimeline} />
</div>
