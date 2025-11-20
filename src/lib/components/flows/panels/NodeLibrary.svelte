<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { NodeType } from '$lib/types/flows';
	
	const dispatch = createEventDispatcher();
	
	interface NodeTemplate {
		type: NodeType;
		label: string;
		icon: string;
		description: string;
		color: string;
	}
	
	const nodeTemplates: NodeTemplate[] = [
		{
			type: 'input',
			label: 'Input',
			icon: '📥',
			description: 'Start node for user input',
			color: 'border-green-500 hover:bg-green-50 dark:hover:bg-green-900/20'
		},
		{
			type: 'model',
			label: 'Model',
			icon: '🤖',
			description: 'Execute an AI model',
			color: 'border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20'
		},
		{
			type: 'knowledge',
			label: 'Knowledge',
			icon: '📚',
			description: 'Query knowledge base (RAG)',
			color: 'border-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/20'
		},
		{
			type: 'websearch',
			label: 'Web Search',
			icon: '🌐',
			description: 'Search the internet',
			color: 'border-cyan-500 hover:bg-cyan-50 dark:hover:bg-cyan-900/20'
		},
		{
			type: 'transform',
			label: 'Transform',
			icon: '🔄',
			description: 'Modify text or extract data',
			color: 'border-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900/20'
		},
		{
			type: 'conditional',
			label: 'Conditional',
			icon: '🔀',
			description: 'Branch based on conditions',
			color: 'border-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20'
		},
		{
			type: 'loop',
			label: 'Loop',
			icon: '🔁',
			description: 'Iterate over data',
			color: 'border-indigo-500 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'
		},
		{
			type: 'merge',
			label: 'Merge',
			icon: '🔗',
			description: 'Combine multiple inputs',
			color: 'border-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/20'
		},
		{
			type: 'output',
			label: 'Output',
			icon: '📤',
			description: 'End node to display results',
			color: 'border-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/20'
		}
	];
	
	const addNode = (type: NodeType) => {
		dispatch('addnode', { type });
	};
	
	// Scroll indicator state
	let scrollContainer: HTMLDivElement;
	let showScrollIndicator = false;
	let isScrolledToBottom = false;
	
	function checkScroll() {
		if (!scrollContainer) return;
		
		const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
		const canScroll = scrollHeight > clientHeight;
		const isAtBottom = scrollTop + clientHeight >= scrollHeight - 5; // 5px threshold
		
		showScrollIndicator = canScroll && !isAtBottom;
		isScrolledToBottom = isAtBottom;
	}
	
	onMount(() => {
		// Check scroll state after DOM settles
		setTimeout(checkScroll, 100);
	});
</script>

<svelte:window on:resize={checkScroll} />

<div class="node-library bg-white dark:bg-gray-800 border-2 border-blue-300 dark:border-blue-600 rounded-lg shadow-2xl w-full md:w-72 relative overflow-hidden">
	<div class="p-3 md:p-4">
		<h3 class="font-bold text-base md:text-lg mb-2 md:mb-3 text-blue-900 dark:text-blue-100 flex items-center gap-2">
			<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 md:w-5 md:h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<rect x="3" y="3" width="7" height="7" />
				<rect x="14" y="3" width="7" height="7" />
				<rect x="14" y="14" width="7" height="7" />
				<rect x="3" y="14" width="7" height="7" />
			</svg>
			Available Nodes
		</h3>
	</div>
	
	<div 
		bind:this={scrollContainer}
		on:scroll={checkScroll}
		class="space-y-1.5 md:space-y-2 px-3 md:px-4 overflow-y-auto max-h-[60vh] md:max-h-none"
		style="scrollbar-width: thin;"
	>
		{#each nodeTemplates as template}
			<button
				on:click={() => addNode(template.type)}
				class="w-full flex items-start gap-2 md:gap-3 p-2.5 md:p-4 border-2 {template.color} rounded-lg md:rounded-xl transition-all cursor-pointer hover:scale-105 active:scale-95 shadow-md hover:shadow-lg bg-white dark:bg-gray-900"
			>
				<div class="text-2xl md:text-3xl flex-shrink-0">{template.icon}</div>
				<div class="flex-1 text-left min-w-0">
					<div class="font-bold text-sm md:text-base text-gray-900 dark:text-gray-100 mb-0.5 md:mb-1">
						{template.label}
					</div>
					<div class="text-xs text-gray-600 dark:text-gray-400 line-clamp-1 md:line-clamp-none">
						{template.description}
					</div>
				</div>
			</button>
		{/each}
	</div>
	
	<!-- Scroll Indicator for Mobile - only shows when content is scrollable and not at bottom -->
	{#if showScrollIndicator}
		<div class="md:hidden absolute bottom-0 left-0 right-0 h-20 pointer-events-none bg-gradient-to-t from-white dark:from-gray-800 via-white/80 dark:via-gray-800/80 to-transparent">
			<div class="absolute bottom-2 left-1/2 -translate-x-1/2 animate-bounce">
				<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-blue-600 dark:text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
					<polyline points="7 13 12 18 17 13"></polyline>
					<polyline points="7 6 12 11 17 6"></polyline>
				</svg>
			</div>
		</div>
	{/if}
	
	<div class="mt-3 md:mt-4 pt-3 md:pt-4 border-t border-gray-200 dark:border-gray-700 hidden md:block px-3 md:px-4 pb-3 md:pb-4">
		<p class="text-xs text-gray-500 dark:text-gray-400">
			Click a node to add it to the canvas. Connect nodes by dragging from one handle to another.
		</p>
	</div>
</div>
