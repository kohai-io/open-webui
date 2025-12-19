<script lang="ts">
	import { goto } from '$app/navigation';
	import CanvasVideoPlayer from '$lib/components/video/CanvasVideoPlayer.svelte';
	import Timeline from '$lib/components/video/timeline/Timeline.svelte';
	import MediaPool from '$lib/components/video/MediaPool.svelte';
	import { videoState, timelineState, markers, segments } from '$lib/stores/video';
	import { mediaPool, type MediaFile } from '$lib/stores/mediaPool';
	import type { Marker, VideoSegment } from '$lib/types/video';
	import { toast } from 'svelte-sonner';

	let videoPlayerComponent: any = null;

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
		console.log('Timeline: Received addtotimeline event', e.detail);
		const media = e.detail.media;
		const mediaDuration = media.duration || 5;
		
		const timelineEnd = $segments.length > 0 
			? Math.max(...$segments.map(s => s.endTime))
			: 0;
		
		const newSegment: VideoSegment = {
			id: `segment-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
			mediaId: media.id,
			startTime: timelineEnd,
			endTime: timelineEnd + mediaDuration,
			sourceStartTime: 0,
			sourceEndTime: mediaDuration, // Use actual media duration, not timeline duration
			enabled: true
		};
		
		console.log('Timeline: Creating segment', {
			mediaId: media.id,
			mediaDuration,
			timeline: `${newSegment.startTime}s - ${newSegment.endTime}s`,
			source: `${newSegment.sourceStartTime}s - ${newSegment.sourceEndTime}s`
		});
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

	const viewVideoList = () => {
		goto('/workspace/videos/list');
	};
</script>

<div class="flex flex-col h-full w-full">
	<!-- Header -->
	<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-4 px-3 sm:px-4 pt-4">
		<div class="flex-1">
			<h1 class="text-xl sm:text-2xl font-semibold">Video Timeline Editor</h1>
			<p class="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
				Add media from your library and create multi-video timelines
			</p>
		</div>
		<button
			on:click={viewVideoList}
			class="px-3 sm:px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium transition-colors flex items-center gap-2 whitespace-nowrap"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-4 h-4"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<rect x="3" y="3" width="7" height="7" />
				<rect x="14" y="3" width="7" height="7" />
				<rect x="14" y="14" width="7" height="7" />
				<rect x="3" y="14" width="7" height="7" />
			</svg>
			<span class="hidden sm:inline">View All Videos</span>
			<span class="sm:hidden">Library</span>
		</button>
	</div>

	<!-- Timeline Editor -->
	<div class="flex-1 flex flex-col bg-gray-900 w-full overflow-hidden">
		<!-- Video Player Section (50% height) -->
		<div class="flex-1 bg-black flex items-center justify-center overflow-hidden">
			<CanvasVideoPlayer
				bind:this={videoPlayerComponent}
				currentTime={$videoState.currentTime}
				isPlaying={$videoState.isPlaying}
				isSegmentDragging={$timelineState.isDragging}
				on:timeupdate={handleVideoTimeUpdate}
				on:playstatechange={handleVideoPlayStateChange}
			/>
		</div>

		<!-- Timeline Section (30% height) -->
		<div class="flex-[2] flex flex-col bg-gray-800 min-h-0">
			<Timeline
				videoUrl=""
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
				on:dragstatechange={(e) => timelineState.update((s) => ({ ...s, isDragging: e.detail.isDragging }))}
			/>
		</div>

		<!-- Media Pool Section (20% height) -->
		<MediaPool on:addtotimeline={handleAddMediaToTimeline} />
	</div>
</div>
