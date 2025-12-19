<script lang="ts">
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	let uploading = false;
	let uploadProgress = 0;
	let selectedFile: File | null = null;
	let dragOver = false;

	const handleFileSelect = (e: Event) => {
		const target = e.target as HTMLInputElement;
		if (target.files && target.files.length > 0) {
			selectedFile = target.files[0];
			validateFile();
		}
	};

	const handleDrop = (e: DragEvent) => {
		e.preventDefault();
		dragOver = false;

		if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
			selectedFile = e.dataTransfer.files[0];
			validateFile();
		}
	};

	const handleDragOver = (e: DragEvent) => {
		e.preventDefault();
		dragOver = true;
	};

	const handleDragLeave = () => {
		dragOver = false;
	};

	const validateFile = () => {
		if (!selectedFile) return false;

		const validTypes = ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'];
		if (!validTypes.includes(selectedFile.type)) {
			toast.error('Please select a valid video file (MP4, WebM, OGG, MOV)');
			selectedFile = null;
			return false;
		}

		const maxSize = 500 * 1024 * 1024; // 500MB
		if (selectedFile.size > maxSize) {
			toast.error('File size must be less than 500MB');
			selectedFile = null;
			return false;
		}

		return true;
	};

	const handleUpload = async () => {
		if (!selectedFile) {
			toast.error('Please select a video file');
			return;
		}

		uploading = true;
		uploadProgress = 0;

		try {
			const formData = new FormData();
			formData.append('file', selectedFile);

			const xhr = new XMLHttpRequest();

			xhr.upload.addEventListener('progress', (e) => {
				if (e.lengthComputable) {
					uploadProgress = Math.round((e.loaded / e.total) * 100);
				}
			});

			xhr.addEventListener('load', () => {
				if (xhr.status === 200) {
					const response = JSON.parse(xhr.responseText);
					toast.success('Video uploaded successfully');
					goto(`/workspace/editor/${response.id || response.file_id}`);
				} else {
					toast.error('Upload failed');
					uploading = false;
				}
			});

			xhr.addEventListener('error', () => {
				toast.error('Upload failed');
				uploading = false;
			});

			const token = localStorage.getItem('token') || '';
			xhr.open('POST', '/api/v1/files');
			xhr.setRequestHeader('Authorization', `Bearer ${token}`);
			xhr.send(formData);
		} catch (error) {
			console.error('Upload error:', error);
			toast.error('Failed to upload video');
			uploading = false;
		}
	};

	const handleCancel = () => {
		goto('/workspace/editor');
	};

	const formatFileSize = (bytes: number) => {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
	};
</script>

<div class="flex flex-col h-full p-6">
	<div class="mb-6">
		<h1 class="text-2xl font-semibold mb-2">Upload Video</h1>
		<p class="text-sm text-gray-500 dark:text-gray-400">
			Upload a video file to edit with the timeline editor
		</p>
	</div>

	<div class="flex-1 flex items-center justify-center">
		<div class="w-full max-w-2xl">
			<!-- Drop Zone -->
			<div
				class="border-2 border-dashed rounded-lg p-12 text-center transition-colors {dragOver
					? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
					: 'border-gray-300 dark:border-gray-600'}"
				on:drop={handleDrop}
				on:dragover={handleDragOver}
				on:dragleave={handleDragLeave}
				role="button"
				tabindex="0"
			>
				{#if !selectedFile}
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-16 h-16 mx-auto mb-4 text-gray-400"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
						<polyline points="17 8 12 3 7 8" />
						<line x1="12" y1="3" x2="12" y2="15" />
					</svg>
					<h3 class="text-lg font-medium mb-2">Drop video file here</h3>
					<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">or click to browse</p>
					<input
						type="file"
						accept="video/*"
						on:change={handleFileSelect}
						class="hidden"
						id="file-input"
					/>
					<label
						for="file-input"
						class="inline-block px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors cursor-pointer"
					>
						Choose File
					</label>
					<p class="text-xs text-gray-400 mt-4">Supported: MP4, WebM, OGG, MOV (max 500MB)</p>
				{:else}
					<div class="bg-gray-100 dark:bg-gray-800 rounded-lg p-6">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-12 h-12 mx-auto mb-3 text-blue-600"
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
						<h4 class="font-medium mb-1">{selectedFile.name}</h4>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{formatFileSize(selectedFile.size)}
						</p>

						{#if uploading}
							<div class="mt-4">
								<div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
									<div
										class="h-full bg-blue-600 transition-all duration-300"
										style="width: {uploadProgress}%"
									></div>
								</div>
								<p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
									Uploading... {uploadProgress}%
								</p>
							</div>
						{:else}
							<button
								on:click={() => (selectedFile = null)}
								class="mt-4 text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
							>
								Remove file
							</button>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Action Buttons -->
			<div class="flex items-center justify-end gap-3 mt-6">
				<button
					on:click={handleCancel}
					disabled={uploading}
					class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
				>
					Cancel
				</button>
				<button
					on:click={handleUpload}
					disabled={!selectedFile || uploading}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{uploading ? 'Uploading...' : 'Upload & Edit'}
				</button>
			</div>
		</div>
	</div>
</div>
