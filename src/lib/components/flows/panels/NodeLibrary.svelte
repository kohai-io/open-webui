<script lang="ts">
	import { createEventDispatcher } from 'svelte';
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
</script>

<div class="node-library bg-white dark:bg-gray-800 border-2 border-blue-300 dark:border-blue-600 rounded-lg shadow-2xl p-4 w-72">
	<h3 class="font-bold text-lg mb-3 text-blue-900 dark:text-blue-100 flex items-center gap-2">
		<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
			<rect x="3" y="3" width="7" height="7" />
			<rect x="14" y="3" width="7" height="7" />
			<rect x="14" y="14" width="7" height="7" />
			<rect x="3" y="14" width="7" height="7" />
		</svg>
		Available Nodes
	</h3>
	
	<div class="space-y-2">
		{#each nodeTemplates as template}
			<button
				on:click={() => addNode(template.type)}
				class="w-full flex items-start gap-3 p-4 border-2 {template.color} rounded-xl transition-all cursor-pointer hover:scale-105 active:scale-95 shadow-md hover:shadow-lg bg-white dark:bg-gray-900"
			>
				<div class="text-3xl">{template.icon}</div>
				<div class="flex-1 text-left">
					<div class="font-bold text-gray-900 dark:text-gray-100 mb-1">
						{template.label}
					</div>
					<div class="text-xs text-gray-600 dark:text-gray-400">
						{template.description}
					</div>
				</div>
			</button>
		{/each}
	</div>
	
	<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
		<p class="text-xs text-gray-500 dark:text-gray-400">
			Click a node to add it to the canvas. Connect nodes by dragging from one handle to another.
		</p>
	</div>
</div>
