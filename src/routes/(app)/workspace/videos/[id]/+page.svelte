<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import VideoTimelineEditor from '$lib/components/video/VideoTimelineEditor.svelte';
	import { currentVideo, videoState, isProcessing } from '$lib/stores/video';
	import { getFileById } from '$lib/apis/files';
	import type { Video } from '$lib/types/video';
	import type { MediaFile } from '$lib/types/media';

	let videoId: string = '';
	let video: Video | null = null;
	let fileData: MediaFile | null = null;
	let loading = true;
	let saving = false;

	$: videoId = $page.params.id || '';

	onMount(async () => {
		await loadVideoData();
	});

	const loadVideoData = async () => {
		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			fileData = await getFileById(token, videoId);
			
			if (!fileData) {
				toast.error('Video not found');
				goto('/workspace/videos');
				return;
			}

			// Convert MediaFile to Video format
			video = {
				id: fileData.id,
				name: fileData.filename || fileData.meta?.name || 'Untitled',
				description: '',
				file_id: fileData.id,
				duration: 0, // Will be determined by video player
				created_at: fileData.updated_at,
				updated_at: fileData.updated_at
			};
			currentVideo.set(video);
		} catch (error) {
			console.error('Error loading video:', error);
			toast.error('Failed to load video');
			goto('/workspace/videos');
		} finally {
			loading = false;
		}
	};

	const handleSave = async () => {
		if (!video) return;

		saving = true;
		try {
			// TODO: Implement save logic
			toast.success('Video saved successfully');
		} catch (error) {
			console.error('Error saving video:', error);
			toast.error('Failed to save video');
		} finally {
			saving = false;
		}
	};

	const handleExport = async () => {
		if (!video) return;

		try {
			// TODO: Implement export logic
			toast.success('Export started');
		} catch (error) {
			console.error('Error exporting video:', error);
			toast.error('Failed to export video');
		}
	};

	const handleBack = () => {
		goto('/workspace/videos');
	};

	const updateVideoName = (newName: string) => {
		if (video) {
			video.name = newName;
			currentVideo.update((v) => (v ? { ...v, name: newName } : v));
		}
	};

	const updateVideoDescription = (newDesc: string) => {
		if (video) {
			video.description = newDesc;
			currentVideo.update((v) => (v ? { ...v, description: newDesc } : v));
		}
	};
</script>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
	</div>
{:else if video}
	<div class="flex flex-col h-full" style="overflow-x: hidden; max-width: 100%; position: relative;">
		<!-- Header -->
		<div
			class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0 mb-2 sm:mb-4 p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700"
			style="flex-shrink: 0;"
		>
			<div class="flex items-center gap-2 sm:gap-3 flex-1 w-full sm:max-w-xl">
				<button
					on:click={handleBack}
					class="p-1.5 sm:p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors flex-shrink-0"
					title="Back to videos"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-4 h-4 sm:w-5 sm:h-5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<line x1="19" y1="12" x2="5" y2="12" />
						<polyline points="12 19 5 12 12 5" />
					</svg>
				</button>
				<div class="flex-1 min-w-0">
					<input
						type="text"
						value={video.name}
						on:input={(e) => updateVideoName(e.currentTarget.value)}
						class="w-full text-lg sm:text-2xl font-semibold bg-transparent border-none focus:outline-none focus:ring-0 p-0"
					/>
					<input
						type="text"
						value={video.description || ''}
						on:input={(e) => updateVideoDescription(e.currentTarget.value)}
						placeholder="Add description (optional)..."
						class="w-full text-xs sm:text-sm text-gray-500 dark:text-gray-400 bg-transparent border-none focus:outline-none focus:ring-0 p-0 mt-1 hidden sm:block"
					/>
				</div>
			</div>
			<div class="flex items-center gap-1.5 sm:gap-2 w-full sm:w-auto">
				<button
					on:click={handleExport}
					disabled={$isProcessing}
					class="px-2 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 sm:gap-2 flex-1 sm:flex-initial justify-center"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-3 h-3 sm:w-4 sm:h-4"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
						<polyline points="7 10 12 15 17 10" />
						<line x1="12" y1="15" x2="12" y2="3" />
					</svg>
					Export
				</button>
				<button
					on:click={handleSave}
					disabled={saving}
					class="px-2 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-1 sm:flex-initial justify-center"
				>
					{saving ? 'Saving...' : 'Save'}
				</button>
			</div>
		</div>

		<!-- Video Timeline Editor (full height) -->
		<div class="flex-1" style="overflow: hidden; max-width: 100%; position: relative; isolation: isolate;">
			<VideoTimelineEditor videoId={video.file_id} />
		</div>
	</div>
{/if}
