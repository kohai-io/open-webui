<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import type { OutputNodeData } from '$lib/types/flows';
	import { selectedNode, flowNodes } from '$lib/stores/flows';
	import { get } from 'svelte/store';
	
	export let data: OutputNodeData;
	export let selected = false;
	export let targetPosition: 'left' | 'right' | 'top' | 'bottom' = 'left';
	export let id: string;
	
	function openConfig(event: MouseEvent) {
		event.stopPropagation(); // Prevent node click event
		const nodes = get(flowNodes);
		const fullNode = nodes.find(n => n.id === id);
		if (fullNode) {
			selectedNode.set(fullNode);
		}
		window.dispatchEvent(new CustomEvent('open-node-config'));
	}
	
	// Map string to Position enum
	$: handlePosition = targetPosition === 'right' ? Position.Right 
		: targetPosition === 'left' ? Position.Left
		: targetPosition === 'top' ? Position.Top
		: Position.Bottom;
	
	let expanded = false;
	let showLightbox = false;
	let currentIterationIndex = 0;
	
	// Handle iteration results array
	$: iterationResults = data.iterationResults || [];
	$: hasMultipleResults = iterationResults.length > 1;
	$: currentValue = hasMultipleResults && currentIterationIndex < iterationResults.length 
		? iterationResults[currentIterationIndex] 
		: data.value;
	
	// Reset index when results change
	$: if (iterationResults.length > 0 && currentIterationIndex >= iterationResults.length) {
		currentIterationIndex = iterationResults.length - 1;
	}
	
	$: fileUrl = data.fileId ? `${WEBUI_BASE_URL}/api/v1/files/${data.fileId}/content` : null;
	$: hasLongText = currentValue && currentValue.length > 150;
	
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
	
	async function copyToClipboard() {
		if (!currentValue) return;
		try {
			await navigator.clipboard.writeText(currentValue);
			// Could add a toast notification here
		} catch (err) {
			console.error('Failed to copy:', err);
		}
	}
	
	function downloadAsFile() {
		if (!currentValue) return;
		const blob = new Blob([currentValue], { type: 'text/plain' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `output-${Date.now()}.txt`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
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
		position={handlePosition}
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
				{#if currentValue}
					<button
						type="button"
						on:click={copyToClipboard}
						class="nodrag p-1.5 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/30 rounded transition-colors"
						title="Copy to clipboard"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
						</svg>
					</button>
					<button
						type="button"
						on:click={downloadAsFile}
						class="nodrag p-1.5 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-900/30 rounded transition-colors"
						title="Download as file"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
						</svg>
					</button>
				{/if}
			</div>
		</div>
	</div>
	
	<!-- Node Body -->
	<div class="node-body p-3">
		<!-- Iteration Navigator -->
		{#if hasMultipleResults}
			<div class="mb-2 flex items-center gap-2 p-2 bg-purple-50 dark:bg-purple-900/20 rounded border border-purple-200 dark:border-purple-700">
				<button
					type="button"
					on:click={() => currentIterationIndex = Math.max(0, currentIterationIndex - 1)}
					disabled={currentIterationIndex === 0}
					class="nodrag p-1 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-800 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
					title="Previous result"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
				</button>
				<div class="flex-1 text-center text-xs font-medium text-purple-700 dark:text-purple-300">
					Iteration {currentIterationIndex + 1} of {iterationResults.length}
				</div>
				<button
					type="button"
					on:click={() => currentIterationIndex = Math.min(iterationResults.length - 1, currentIterationIndex + 1)}
					disabled={currentIterationIndex === iterationResults.length - 1}
					class="nodrag p-1 text-purple-600 dark:text-purple-400 hover:bg-purple-100 dark:hover:bg-purple-800 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
					title="Next result"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</button>
			</div>
		{/if}
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
		{:else if currentValue}
			<div class="relative">
				<div class="text-xs text-gray-600 dark:text-gray-400 {expanded ? '' : 'line-clamp-3'} whitespace-pre-wrap">
					{currentValue}
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
