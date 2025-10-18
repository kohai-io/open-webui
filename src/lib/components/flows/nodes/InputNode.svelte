<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import type { InputNodeData } from '$lib/types/flows';
	
	export let data: InputNodeData;
	export let selected = false;
	
	let showLightbox = false;
	
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
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

<div
	class="input-node min-w-[180px] rounded-lg border-2 border-green-300 dark:border-green-600 bg-white dark:bg-gray-800 transition-all shadow-md hover:shadow-lg {selected
		? 'ring-2 ring-green-500'
		: ''}"
>
	<!-- Node Header -->
	<div class="node-header p-3 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-2">
			<div class="text-2xl">📥</div>
			<div class="flex-1">
				<div class="font-semibold text-gray-900 dark:text-gray-100">
					{data.label || 'Input'}
				</div>
			</div>
		</div>
	</div>
	
	<!-- Node Body -->
	<div class="node-body p-3">
		{#if data.mediaFileId && data.mediaFileName}
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
			<div class="text-xs text-gray-600 dark:text-gray-400 line-clamp-3">
				{data.value}
			</div>
		{:else}
			<div class="text-xs text-gray-400 dark:text-gray-500 italic">
				{data.placeholder || 'Enter input...'}
			</div>
		{/if}
	</div>
	
	<!-- Output Handle -->
	<Handle
		type="source"
		position={Position.Right}
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
