<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import type { InputNodeData } from '$lib/types/flows';
	import { uploadFile } from '$lib/apis/files';
	import { updateNodeData } from '$lib/stores/flows';
	
	export let data: InputNodeData;
	export let selected = false;
	export let sourcePosition: 'left' | 'right' | 'top' | 'bottom' = 'right';
	export let id: string; // Node ID passed by SvelteFlow
	
	import { selectedNode, flowNodes } from '$lib/stores/flows';
	import { get } from 'svelte/store';
	
	function openConfig(event: MouseEvent) {
		event.stopPropagation(); // Prevent node click event
		// Find the full node from the store
		const nodes = get(flowNodes);
		const fullNode = nodes.find(n => n.id === id);
		if (fullNode) {
			selectedNode.set(fullNode);
		}
		// Dispatch custom event to trigger config panel
		window.dispatchEvent(new CustomEvent('open-node-config'));
	}
	
	// Map string to Position enum
	$: handlePosition = sourcePosition === 'right' ? Position.Right 
		: sourcePosition === 'left' ? Position.Left
		: sourcePosition === 'top' ? Position.Top
		: Position.Bottom;
	
	let showLightbox = false;
	let isEditing = false;
	let editValue = '';
	let fileInputElement: HTMLInputElement;
	let isUploading = false;
	
	$: fileUrl = data.mediaFileId ? `/api/v1/files/${data.mediaFileId}/content` : null;
	
	function openLightbox() {
		showLightbox = true;
	}
	
	function closeLightbox() {
		showLightbox = false;
	}
	
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			closeLightbox();
			if (isEditing) {
				cancelEdit();
			}
		}
	}
	
	function startEdit() {
		isEditing = true;
		editValue = data.value || '';
	}
	
	function saveEdit() {
		updateNodeData(id, { value: editValue });
		isEditing = false;
	}
	
	function cancelEdit() {
		isEditing = false;
		editValue = '';
	}
	
	async function handleFileUpload(event: Event) {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		if (!file) return;
		
		isUploading = true;
		try {
			const token = localStorage.getItem('token') || '';
			const uploadedFile = await uploadFile(token, file);
			
			updateNodeData(id, {
				mediaFileId: uploadedFile.id,
				mediaFileName: file.name,
				mediaFileType: file.type
			});
		} catch (error) {
			console.error('File upload failed:', error);
		} finally {
			isUploading = false;
			if (fileInputElement) {
				fileInputElement.value = '';
			}
		}
	}
	
	function triggerFileUpload() {
		fileInputElement?.click();
	}
	
	
	function clearMedia() {
		updateNodeData(id, {
			mediaFileId: undefined,
			mediaFileName: undefined,
			mediaFileType: undefined
		});
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="input-node min-w-[180px] rounded-lg border-2 border-green-300 dark:border-green-600 bg-white dark:bg-gray-800 transition-all shadow-md hover:shadow-lg {selected
		? 'ring-2 ring-green-500'
		: ''}"
>
	<!-- Hidden file input -->
	<input
		type="file"
		bind:this={fileInputElement}
		on:change={handleFileUpload}
		accept="image/*,video/*,audio/*"
		class="hidden"
	/>
	
	<!-- Node Header -->
	<div class="node-header p-3 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-2">
			<div class="text-2xl">📥</div>
			<div class="flex-1">
				<div class="font-semibold text-gray-900 dark:text-gray-100">
					{data.label || 'Input'}
				</div>
			</div>
			<!-- Action buttons -->
			<div class="flex items-center gap-1">
				<!-- Config button -->
				<button
					type="button"
					on:click={openConfig}
					class="nodrag p-1.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
					title="Configure node"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
				</button>
				{#if isUploading}
					<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600"></div>
				{:else}
					<!-- Upload file button -->
					<button
						type="button"
						on:click={triggerFileUpload}
						class="nodrag p-1.5 text-green-600 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/30 rounded transition-colors"
						title="Upload file"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
						</svg>
					</button>
					<!-- Clear media button (only show if media exists) -->
					{#if data.mediaFileId}
						<button
							type="button"
							on:click={clearMedia}
							class="nodrag p-1.5 text-red-600 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 rounded transition-colors"
							title="Clear media"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
							</svg>
						</button>
					{/if}
				{/if}
			</div>
		</div>
	</div>
	
	<!-- Node Body -->
	<div class="node-body p-3">
		{#if isEditing}
			<!-- Inline text editor -->
			<div class="space-y-2">
				<textarea
					bind:value={editValue}
					class="nodrag w-full px-2 py-1.5 text-xs bg-white dark:bg-gray-900 border border-green-300 dark:border-green-600 rounded resize-none focus:outline-none focus:ring-2 focus:ring-green-500"
					rows="3"
					placeholder="Enter your input text..."
					autofocus
				></textarea>
				<div class="flex gap-2">
					<button
						type="button"
						on:click={saveEdit}
						class="nodrag flex-1 px-2 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
					>
						Save
					</button>
					<button
						type="button"
						on:click={cancelEdit}
						class="nodrag flex-1 px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
					>
						Cancel
					</button>
				</div>
			</div>
		{:else if data.mediaFileId && data.mediaFileName}
			<div class="space-y-2">
				{#if data.mediaFileType?.startsWith('image/')}
					<button
						type="button"
						on:click={openLightbox}
						class="nodrag w-full cursor-zoom-in hover:opacity-90 transition-opacity rounded overflow-hidden bg-gray-50 dark:bg-gray-900"
					>
						<img 
							src={`/api/v1/files/${data.mediaFileId}/content`}
							alt={data.mediaFileName}
							class="w-full h-auto max-h-32 object-contain"
							loading="lazy"
						/>
					</button>
				{:else if data.mediaFileType?.startsWith('video/')}
					<div class="relative group rounded overflow-hidden bg-gray-900">
						<video 
							src={`/api/v1/files/${data.mediaFileId}/content#t=0.1`}
							class="w-full h-auto max-h-32 object-contain"
							preload="metadata"
						>
							<track kind="captions" />
						</video>
						<button
							type="button"
							on:click={openLightbox}
							class="nodrag absolute inset-0 flex items-center justify-center bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all cursor-pointer"
						>
							<svg class="w-8 h-8 text-white opacity-60 group-hover:opacity-90 transition-opacity" fill="currentColor" viewBox="0 0 24 24">
								<path d="M8 5v14l11-7z"/>
							</svg>
						</button>
					</div>
				{:else if data.mediaFileType?.startsWith('audio/')}
					<div class="rounded bg-gray-50 dark:bg-gray-900 p-2">
						<audio 
							controls
							src={`/api/v1/files/${data.mediaFileId}/content`}
							class="w-full"
							style="height: 32px;"
						>
							<track kind="captions" />
						</audio>
					</div>
				{:else}
					<div class="flex items-center gap-2">
						<span class="text-lg">📎</span>
						<div class="text-xs text-gray-600 dark:text-gray-400 font-medium">
							Media File
						</div>
					</div>
				{/if}
				<div class="text-xs text-gray-500 dark:text-gray-500 truncate">
					{data.mediaFileName}
				</div>
			</div>
		{:else if data.value}
			<button
				type="button"
				on:click={startEdit}
				class="nodrag w-full text-left text-xs text-gray-600 dark:text-gray-400 line-clamp-3 hover:bg-green-50 dark:hover:bg-green-900/10 rounded p-1 transition-colors"
				title="Click to edit"
			>
				{data.value}
			</button>
		{:else}
			<button
				type="button"
				on:click={startEdit}
				class="nodrag w-full text-left text-xs text-gray-400 dark:text-gray-500 italic hover:bg-green-50 dark:hover:bg-green-900/10 rounded p-1 transition-colors"
				title="Click to add text"
			>
				{data.placeholder || 'Click to enter input...'}
			</button>
		{/if}
	</div>
	
	<!-- Output Handle -->
	<Handle
		type="source"
		position={handlePosition}
		class="!bg-green-500"
	/>
</div>

<!-- Lightbox Modal -->
{#if showLightbox && fileUrl}
	<div 
		class="fixed inset-0 z-[9999] flex items-center justify-center bg-black bg-opacity-90"
		on:click={closeLightbox}
		on:keydown={(e) => e.key === 'Escape' && closeLightbox()}
		role="button"
		tabindex="0"
	>
		<div 
			class="relative"
			on:click|stopPropagation
			role="presentation"
		>
			<!-- Close button -->
			<button
				type="button"
				on:click|stopPropagation={closeLightbox}
				class="absolute top-2 right-2 z-10 p-2 bg-black bg-opacity-50 hover:bg-opacity-75 rounded-full text-white transition-all"
				aria-label="Close"
			>
				<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
			
			{#if data.mediaFileType?.startsWith('image/')}
				<img 
					src={fileUrl} 
					alt={data.mediaFileName || 'Full size input'} 
					class="max-w-[95vw] max-h-[90vh] object-contain rounded-lg shadow-2xl"
				/>
			{:else if data.mediaFileType?.startsWith('video/')}
				<video 
					src={fileUrl} 
					controls 
					autoplay
					class="max-w-[95vw] max-h-[90vh] rounded-lg shadow-2xl"
				>
					<track kind="captions" />
				</video>
			{/if}
		</div>
	</div>
{/if}

<style>
	.line-clamp-3 {
		display: -webkit-box;
		-webkit-line-clamp: 3;
		line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
