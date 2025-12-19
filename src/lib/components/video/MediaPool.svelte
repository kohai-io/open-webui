<script lang="ts">
	import { mediaPool, type MediaFile } from '$lib/stores/mediaPool';
	import { createEventDispatcher } from 'svelte';
	import MediaBrowserModal from './MediaBrowserModal.svelte';

	const dispatch = createEventDispatcher();

	let fileInput: HTMLInputElement;
	let draggingOver = false;
	let showBrowserModal = false;

	const handleFileSelect = async (files: FileList | null) => {
		if (!files) return;

		for (let i = 0; i < files.length; i++) {
			const file = files[i];
			const url = URL.createObjectURL(file);
			const mediaId = `media-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

			const type = file.type.startsWith('video/') 
				? 'video' 
				: file.type.startsWith('audio/')
				? 'audio'
				: file.type.startsWith('image/')
				? 'image'
				: null;

			if (!type) continue;

			const media: MediaFile = {
				id: mediaId,
				name: file.name,
				type,
				url
			};

			if (type === 'video') {
				const video = document.createElement('video');
				video.src = url;
				await new Promise(resolve => {
					video.onloadedmetadata = () => {
						media.duration = video.duration;
						media.width = video.videoWidth;
						media.height = video.videoHeight;
						resolve(null);
					};
				});
			} else if (type === 'image') {
				const img = new Image();
				img.src = url;
				await new Promise(resolve => {
					img.onload = () => {
						media.width = img.width;
						media.height = img.height;
						media.duration = 5;
						resolve(null);
					};
				});
			}

			mediaPool.addMedia(media);
		}
	};

	const handleDrop = (e: DragEvent) => {
		e.preventDefault();
		draggingOver = false;
		handleFileSelect(e.dataTransfer?.files || null);
	};

	const handleDragOver = (e: DragEvent) => {
		e.preventDefault();
		draggingOver = true;
	};

	const handleDragLeave = () => {
		draggingOver = false;
	};

	const handleMediaClick = (media: MediaFile) => {
		console.log('MediaPool: Clicking media', media.name);
		dispatch('addtotimeline', { media });
	};

	const handleAddMediaFromBrowser = (e: CustomEvent<{ media: MediaFile }>) => {
		console.log('MediaPool: Received addmedia event from browser', e.detail.media.name);
		const media = e.detail.media;
		mediaPool.addMedia(media);
		console.log('MediaPool: Added to pool, current pool size:', $mediaPool.length);
		// Don't auto-add to timeline - let user click media item to add
	};
</script>

<div class="media-pool">
	<div class="header">
		<h3>Media Pool</h3>
		<button 
			class="btn-add"
			on:click={() => showBrowserModal = true}
		>
			+ Add Media
		</button>
	</div>

	<MediaBrowserModal 
		bind:show={showBrowserModal}
		on:addmedia={handleAddMediaFromBrowser}
	/>

	<input
		bind:this={fileInput}
		type="file"
		accept="video/*,audio/*,image/*"
		multiple
		style="display: none"
		on:change={(e) => handleFileSelect(e.currentTarget.files)}
	/>

	<div 
		class="drop-zone"
		class:dragging={draggingOver}
		role="button"
		tabindex="0"
		on:drop={handleDrop}
		on:dragover={handleDragOver}
		on:dragleave={handleDragLeave}
	>
		{#if $mediaPool.length === 0}
			<div class="empty-state">
				<p>Drop media files here or click "Add Media"</p>
				<span>Supports video, audio, and images</span>
			</div>
		{:else}
			<div class="media-grid">
				{#each $mediaPool as media (media.id)}
					<button
						class="media-item"
						on:click={() => handleMediaClick(media)}
						title="Click to add to timeline"
					>
						{#if media.type === 'video'}
							<video src={media.url} class="thumbnail" muted></video>
						{:else if media.type === 'image'}
							<img src={media.url} alt={media.name} class="thumbnail" />
						{:else}
							<div class="audio-icon">🎵</div>
						{/if}
						<div class="media-info">
							<span class="name">{media.name}</span>
							{#if media.duration}
								<span class="duration">{media.duration.toFixed(1)}s</span>
							{/if}
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.media-pool {
		display: flex;
		flex-direction: column;
		height: 200px;
		background: #1a1a1a;
		border-top: 1px solid #333;
	}

	.header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #333;
	}

	h3 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: #e5e7eb;
	}

	.btn-add {
		padding: 0.375rem 0.75rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.75rem;
		cursor: pointer;
		transition: background 0.2s;
	}

	.btn-add:hover {
		background: #2563eb;
	}

	.drop-zone {
		flex: 1;
		overflow-y: auto;
		padding: 0.75rem;
		transition: background 0.2s;
	}

	.drop-zone.dragging {
		background: #2a2a2a;
		border: 2px dashed #3b82f6;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		color: #9ca3af;
		text-align: center;
	}

	.empty-state p {
		margin: 0 0 0.5rem 0;
		font-size: 0.875rem;
	}

	.empty-state span {
		font-size: 0.75rem;
		color: #6b7280;
	}

	.media-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
		gap: 0.75rem;
	}

	.media-item {
		display: flex;
		flex-direction: column;
		background: #2a2a2a;
		border: 1px solid #333;
		border-radius: 0.375rem;
		overflow: hidden;
		cursor: pointer;
		transition: all 0.2s;
		padding: 0;
	}

	.media-item:hover {
		border-color: #3b82f6;
		transform: translateY(-2px);
	}

	.thumbnail {
		width: 100%;
		height: 80px;
		object-fit: cover;
		display: block;
	}

	.audio-icon {
		width: 100%;
		height: 80px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 2rem;
		background: #1f2937;
	}

	.media-info {
		display: flex;
		flex-direction: column;
		padding: 0.5rem;
		gap: 0.25rem;
	}

	.name {
		font-size: 0.75rem;
		color: #e5e7eb;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.duration {
		font-size: 0.625rem;
		color: #9ca3af;
	}
</style>
