<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { fetchMediaOverview } from '$lib/services/media';
	import { classify } from '$lib/utils/media';
	import type { MediaFile } from '$lib/types/media';

	let loading = true;
	let videoList: MediaFile[] = [];
	let searchQuery = '';

	onMount(async () => {
		await loadVideos();
	});

	const loadVideos = async () => {
		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			const data = await fetchMediaOverview(token);
			
			// Filter for video and audio files only
			if (data && data.files) {
				videoList = data.files.filter((file) => {
					const type = classify(file);
					return type === 'video' || type === 'audio';
				});
			}
		} catch (error) {
			console.error('Error loading videos:', error);
			toast.error('Failed to load videos');
		} finally {
			loading = false;
		}
	};

	const backToTimeline = () => {
		goto('/workspace/videos');
	};

	const editVideo = (videoId: string) => {
		goto(`/workspace/videos/${videoId}`);
	};

	$: filteredVideos = videoList.filter((video) =>
		(video.filename || video.meta?.name || '').toLowerCase().includes(searchQuery.toLowerCase())
	);

	const formatDate = (timestamp: number) => {
		return new Date(timestamp * 1000).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	};

	const formatFileSize = (bytes: number | undefined) => {
		if (!bytes) return 'Unknown';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
	};

	const formatDuration = (file: MediaFile) => {
		// Duration will be determined on the editor page
		const type = classify(file);
		return type === 'video' ? '🎬 Video' : '🎵 Audio';
	};
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between mb-6">
		<div>
			<h1 class="text-2xl font-semibold">Video Library</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				Browse and manage your video files
			</p>
		</div>
		<button
			on:click={backToTimeline}
			class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
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
				<path d="M19 12H5M12 19l-7-7 7-7"/>
			</svg>
			Back to Timeline
		</button>
	</div>

	<!-- Search -->
	<div class="mb-4">
		<input
			type="text"
			bind:value={searchQuery}
			placeholder="Search videos..."
			class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
		/>
	</div>

	<!-- Videos Grid -->
	{#if loading}
		<div class="flex items-center justify-center h-64">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
		</div>
	{:else if filteredVideos.length === 0}
		<div class="flex flex-col items-center justify-center h-64 text-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-16 h-16 text-gray-400 mb-4"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<polygon points="23 7 16 12 23 17 23 7" />
				<rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
			</svg>
			<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No videos yet</h3>
			<p class="text-gray-500 dark:text-gray-400 mb-4">
				{searchQuery ? 'No videos match your search' : 'No videos in your library yet'}
			</p>
			{#if !searchQuery}
				<button
					on:click={backToTimeline}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
				>
					Go to Timeline Editor
				</button>
			{/if}
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each filteredVideos as video (video.id)}
				<div
					class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden hover:shadow-lg transition-shadow bg-white dark:bg-gray-800 cursor-pointer"
					on:click={() => editVideo(video.id)}
					role="button"
					tabindex="0"
					on:keydown={(e) => e.key === 'Enter' && editVideo(video.id)}
				>
					<!-- Video Thumbnail -->
					<div class="aspect-video bg-gray-900 flex items-center justify-center relative">
						{#if classify(video) === 'video'}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-12 h-12 text-gray-600"
								viewBox="0 0 24 24"
								fill="currentColor"
							>
								<polygon points="5 3 19 12 5 21 5 3" />
							</svg>
						{:else}
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-12 h-12 text-gray-600"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<path d="M9 18V5l12-2v13" />
								<circle cx="6" cy="18" r="3" />
								<circle cx="18" cy="16" r="3" />
							</svg>
						{/if}
					</div>

					<!-- Video Info -->
					<div class="p-4">
						<h3 class="font-semibold text-gray-900 dark:text-gray-100 mb-1 truncate">
							{video.filename || video.meta?.name || 'Untitled'}
						</h3>
						<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
							<span>{formatDuration(video)}</span>
							<span>{formatFileSize(video.meta?.size)}</span>
						</div>
						<div class="text-xs text-gray-400 mt-1">
							{formatDate(video.updated_at)}
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
