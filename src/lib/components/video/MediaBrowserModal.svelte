<script lang="ts">
	import { onMount, createEventDispatcher } from 'svelte';
	import { getMediaOverview, uploadFile } from '$lib/apis/files';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { classify } from '$lib/utils/media';
	import Modal from '$lib/components/common/Modal.svelte';
	import type { MediaFile as ApiMediaFile } from '$lib/types/media';
	import type { MediaFile } from '$lib/stores/mediaPool';

	export let show = false;

	const dispatch = createEventDispatcher();

	let loading = true;
	let files: ApiMediaFile[] = [];
	let selectedFileIds: string[] = [];
	let uploadingFiles: File[] = [];
	let uploadProgress: Record<string, number> = {};
	let fileInput: HTMLInputElement;
	let searchQuery = '';

	const loadFiles = async () => {
		loading = true;
		const token = localStorage.token;
		
		try {
			const response = await getMediaOverview(token, 0, 100);
			if (response?.files) {
				// Filter to only show video/audio/image files
				files = response.files.filter((f: any) => {
					const contentType = f.data?.content_type || f.meta?.content_type || '';
					return contentType.startsWith('video/') ||
						contentType.startsWith('audio/') ||
						contentType.startsWith('image/');
				});
			}
		} catch (err) {
			console.error('Failed to load files:', err);
		} finally {
			loading = false;
		}
	};

	const toggleFileSelection = (fileId: string) => {
		console.log('MediaBrowserModal: Toggling selection for', fileId);
		if (selectedFileIds.includes(fileId)) {
			selectedFileIds = selectedFileIds.filter(id => id !== fileId);
			console.log('MediaBrowserModal: Deselected, total selected:', selectedFileIds.length);
		} else {
			selectedFileIds = [...selectedFileIds, fileId];
			console.log('MediaBrowserModal: Selected, total selected:', selectedFileIds.length);
		}
	};

	const handleAddSelected = () => {
		console.log('MediaBrowserModal: Add Selected clicked, selected count:', selectedFileIds.length);
		const selected = files.filter(f => selectedFileIds.includes(f.id));
		console.log('MediaBrowserModal: Filtered selected files:', selected.length);
		
		selected.forEach((file: any) => {
			const contentType = file.data?.content_type || file.meta?.content_type || '';
			const type = contentType.startsWith('video/') 
				? 'video' 
				: contentType.startsWith('audio/')
				? 'audio'
				: 'image';

			const media: MediaFile = {
				id: file.id,
				name: file.meta?.name || file.filename || 'Untitled',
				type,
				url: `${WEBUI_API_BASE_URL}/files/${file.id}/content`,
				duration: file.data?.duration || file.meta?.duration,
				width: file.data?.width || file.meta?.width,
				height: file.data?.height || file.meta?.height
			};

			console.log('MediaBrowserModal: Dispatching addmedia event for', media.name);
			dispatch('addmedia', { media });
		});

		show = false;
		selectedFileIds = [];
	};

	const handleUpload = async (fileList: FileList | null) => {
		if (!fileList) return;

		const token = localStorage.token;
		uploadingFiles = Array.from(fileList);

		for (const file of uploadingFiles) {
			try {
				uploadProgress[file.name] = 0;
				const response = await uploadFile(token, file);
				
				if (response?.id) {
					uploadProgress[file.name] = 100;
					await loadFiles();
					selectedFileIds = [...selectedFileIds, response.id];
				}
			} catch (err) {
				console.error(`Failed to upload ${file.name}:`, err);
			}
		}

		uploadingFiles = [];
		uploadProgress = {};
	};

	const getFileUrl = (file: ApiMediaFile) => {
		return `${WEBUI_API_BASE_URL}/files/${file.id}/content`;
	};

	const formatFileSize = (bytes: number | undefined) => {
		if (!bytes) return 'Unknown';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
	};

	const formatDuration = (file: ApiMediaFile) => {
		const type = classify(file);
		return type === 'video' ? '🎬 Video' : type === 'audio' ? '🎵 Audio' : '🖼️ Image';
	};

	const formatDate = (timestamp: number) => {
		return new Date(timestamp * 1000).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	};

	$: filteredFiles = files.filter((file) =>
		(file.filename || file.meta?.name || '').toLowerCase().includes(searchQuery.toLowerCase())
	);

	onMount(() => {
		if (show) {
			loadFiles();
		}
	});

	$: if (show) {
		loadFiles();
		selectedFileIds = [];
		searchQuery = '';
	}
</script>

<Modal bind:show size="xl">
	<div class="flex flex-col h-full">
		<div class="flex flex-col gap-3 px-4 pt-4">
			<div class="flex items-center justify-between">
				<div>
					<h2 class="text-xl font-semibold dark:text-gray-100">Add Media to Timeline</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
						Select media files from your library
					</p>
				</div>
				<div class="flex gap-2">
					<input
						bind:this={fileInput}
						type="file"
						accept="video/*,audio/*,image/*"
						multiple
						style="display: none"
						on:change={(e) => handleUpload(e.currentTarget.files)}
					/>
					<button
						class="px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors flex items-center gap-2"
						on:click={() => fileInput.click()}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-4 h-4"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
						>
							<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
							<polyline points="17 8 12 3 7 8" />
							<line x1="12" y1="3" x2="12" y2="15" />
						</svg>
						Upload
					</button>
					<button
						class="px-3 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded-lg disabled:opacity-50 transition-colors"
						disabled={selectedFileIds.length === 0}
						on:click={handleAddSelected}
					>
						Add Selected ({selectedFileIds.length})
					</button>
				</div>
			</div>
			
			<!-- Search -->
			<input
				type="text"
				bind:value={searchQuery}
				placeholder="Search media files..."
				class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
			/>
		</div>

		<div class="flex-1 flex flex-col overflow-hidden min-h-0">
			{#if loading}
			<div class="flex flex-col items-center justify-center h-full gap-4">
				<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
				<button
					class="px-4 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
					on:click={() => show = false}
				>
					Cancel
				</button>
			</div>
		{:else if filteredFiles.length === 0}
			<div class="flex flex-col items-center justify-center h-full gap-4 text-center">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-16 h-16 text-gray-400"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<polygon points="23 7 16 12 23 17 23 7" />
					<rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
				</svg>
				<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
					{searchQuery ? 'No files match your search' : 'No media files yet'}
				</h3>
				<p class="text-gray-500 dark:text-gray-400">
					{searchQuery ? 'Try a different search term' : 'Upload your first video, audio, or image file'}
				</p>
				{#if !searchQuery}
					<button
						class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
						on:click={() => fileInput.click()}
					>
						Upload Media
					</button>
				{/if}
			</div>
		{:else}
			<div class="overflow-y-auto p-4">
				<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
					{#each filteredFiles as file (file.id)}
						{@const contentType = (file as any).data?.content_type || file.meta?.content_type || ''}
						<button
							class="relative border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden hover:shadow-lg transition-all bg-white dark:bg-gray-800 cursor-pointer text-left"
							class:ring-2={selectedFileIds.includes(file.id)}
							class:ring-blue-500={selectedFileIds.includes(file.id)}
							on:click={() => toggleFileSelection(file.id)}
						>
							<!-- Thumbnail -->
							<div class="aspect-video bg-gray-900 flex items-center justify-center relative">
								{#if contentType.startsWith('video/')}
									<video
										src={getFileUrl(file)}
										class="w-full h-full object-cover"
										muted
									></video>
								{:else if contentType.startsWith('image/')}
									<img
										src={getFileUrl(file)}
										alt={file.filename}
										class="w-full h-full object-cover"
									/>
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

								{#if selectedFileIds.includes(file.id)}
									<div class="absolute top-2 right-2 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center shadow-lg">
										<svg class="w-5 h-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
											<polyline points="20 6 9 17 4 12"></polyline>
										</svg>
									</div>
								{/if}
							</div>

							<!-- File Info -->
							<div class="p-3">
								<h3 class="font-semibold text-gray-900 dark:text-gray-100 text-sm mb-1 truncate">
									{file.meta?.name || file.filename}
								</h3>
								<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
									<span>{formatDuration(file)}</span>
									<span>{formatFileSize(file.meta?.size)}</span>
								</div>
								<div class="text-xs text-gray-400 mt-1">
									{formatDate(file.updated_at)}
								</div>
							</div>
						</button>
					{/each}
				</div>
			</div>
		{/if}

		{#if uploadingFiles.length > 0}
			<div class="border-t border-gray-700 p-4 bg-gray-50 dark:bg-gray-800">
				<div class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">Uploading files...</div>
				<div class="space-y-2">
					{#each uploadingFiles as file}
						<div class="flex items-center gap-3">
							<div class="flex-1">
								<div class="text-sm text-gray-600 dark:text-gray-400 truncate">{file.name}</div>
								<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5 mt-1">
									<div 
										class="bg-blue-600 h-1.5 rounded-full transition-all"
										style="width: {uploadProgress[file.name] || 0}%"
									></div>
								</div>
							</div>
							<span class="text-xs text-gray-500 dark:text-gray-400 font-medium">
								{uploadProgress[file.name] || 0}%
							</span>
						</div>
					{/each}
				</div>
			</div>
			{/if}
		</div>
	</div>
</Modal>

<style>
	button:disabled {
		cursor: not-allowed;
	}
</style>
