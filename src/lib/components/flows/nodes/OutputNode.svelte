<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import type { OutputNodeData } from '$lib/types/flows';
	
	export let data: OutputNodeData;
	export let selected = false;
	
	let expanded = false;
	let showLightbox = false;
	
	$: fileUrl = data.fileId ? `${WEBUI_BASE_URL}/api/v1/files/${data.fileId}/content` : null;
	$: hasLongText = data.value && data.value.length > 150;
	
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
	class="output-node min-w-[180px] rounded-lg border-2 border-purple-300 dark:border-purple-600 bg-white dark:bg-gray-800 transition-all shadow-md hover:shadow-lg {selected
		? 'ring-2 ring-purple-500'
		: ''}"
>
	<!-- Input Handle -->
	<Handle
		type="target"
		position={Position.Left}
		class="!bg-purple-500"
	/>
	
	<!-- Node Header -->
	<div class="node-header p-3 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-2">
			<div class="text-2xl">📤</div>
			<div class="flex-1">
				<div class="font-semibold text-gray-900 dark:text-gray-100">
					{data.label || 'Output'}
				</div>
			</div>
		</div>
	</div>
	
	<!-- Node Body -->
	<div class="node-body p-3">
		{#if data.format === 'file' && fileUrl}
			<!-- File Output -->
			<div class="file-preview">
				{#if data.fileType === 'image'}
					<button
						type="button"
						on:click={openLightbox}
						class="nodrag w-full cursor-zoom-in hover:opacity-90 transition-opacity"
					>
						<img src={fileUrl} alt="Output" class="w-full rounded" />
					</button>
				{:else if data.fileType === 'video'}
					<div class="relative group">
						<video src={fileUrl} class="w-full rounded" preload="metadata">
							<track kind="captions" />
						</video>
						<button
							type="button"
							on:click={openLightbox}
							class="nodrag absolute inset-0 flex items-center justify-center bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-all rounded cursor-pointer"
						>
							<svg class="w-12 h-12 text-white opacity-60 group-hover:opacity-90 transition-opacity" fill="currentColor" viewBox="0 0 24 24">
								<path d="M8 5v14l11-7z"/>
							</svg>
						</button>
					</div>
				{:else if data.fileType === 'audio'}
					<audio src={fileUrl} controls class="w-full" />
				{/if}
			</div>
			<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
				File: {data.fileType}
			</div>
		{:else if data.value}
			<div class="relative">
				<div class="text-xs text-gray-600 dark:text-gray-400 {expanded ? '' : 'line-clamp-3'} whitespace-pre-wrap">
					{data.value}
				</div>
				{#if hasLongText}
					<button
						type="button"
						on:click={() => expanded = !expanded}
						class="nodrag mt-1 text-xs text-purple-600 dark:text-purple-400 hover:underline font-medium"
					>
						{expanded ? 'Show less' : 'Show more'}
					</button>
				{/if}
			</div>
		{:else}
			<div class="text-xs text-gray-400 dark:text-gray-500 italic">
				Output will appear here...
			</div>
		{/if}
		
		{#if data.format && data.format !== 'file'}
			<div class="mt-2 text-xs text-gray-500 dark:text-gray-400">
				Format: {data.format}
			</div>
		{/if}
	</div>
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
			
			{#if data.fileType === 'image'}
				<img 
					src={fileUrl} 
					alt="Full size output" 
					class="max-w-[95vw] max-h-[90vh] object-contain rounded-lg shadow-2xl"
				/>
			{:else if data.fileType === 'video'}
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
