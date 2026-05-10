<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import type { MergeNodeData } from '$lib/types/flows';
	import { selectedNode, flowNodes } from '$lib/stores/flows';
	import { get } from 'svelte/store';
	
	export let data: MergeNodeData;
	export let selected = false;
	export let sourcePosition: 'left' | 'right' | 'top' | 'bottom' = 'right';
	export let targetPosition: 'left' | 'right' | 'top' | 'bottom' = 'left';
	export let id: string;
	
	function openConfig(event: MouseEvent) {
		event.stopPropagation(); // Prevent node click event
		const nodes = get(flowNodes);
		const fullNode = nodes.find(n => n.id === id);
		if (fullNode) selectedNode.set(fullNode);
		window.dispatchEvent(new CustomEvent('open-node-config'));
	}
	
	$: sourceHandlePosition = sourcePosition === 'right' ? Position.Right : sourcePosition === 'left' ? Position.Left : sourcePosition === 'top' ? Position.Top : Position.Bottom;
	$: targetHandlePosition = targetPosition === 'right' ? Position.Right : targetPosition === 'left' ? Position.Left : targetPosition === 'top' ? Position.Top : Position.Bottom;
	
	const getStatusColor = (status?: string) => {
		switch (status) {
			case 'running':
				return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
			case 'success':
				return 'border-green-500 bg-green-50 dark:bg-green-900/20';
			case 'error':
				return 'border-red-500 bg-red-50 dark:bg-red-900/20';
			default:
				return 'border-yellow-300 dark:border-yellow-600 bg-white dark:bg-gray-800';
		}
	};
</script>

<div
	class="merge-node min-w-[200px] rounded-lg border-2 transition-all shadow-md hover:shadow-lg {getStatusColor(
		data.status
	)} {selected ? 'ring-2 ring-yellow-500' : ''}"
>
	<!-- Multiple Input Handles -->
	<Handle
		type="target"
		position={targetHandlePosition}
		id="input-1"
		style={targetHandlePosition === Position.Top ? 'left: 33%' : targetHandlePosition === Position.Bottom ? 'left: 33%' : 'top: 33%'}
		class="!bg-yellow-500"
	/>
	<Handle
		type="target"
		position={targetHandlePosition}
		id="input-2"
		style={targetHandlePosition === Position.Top ? 'left: 67%' : targetHandlePosition === Position.Bottom ? 'left: 67%' : 'top: 67%'}
		class="!bg-yellow-500"
	/>
	
	<!-- Node Header -->
	<div class="node-header p-3 border-b border-gray-200 dark:border-gray-700">
		<div class="flex items-center gap-2">
			<div class="text-2xl">🔗</div>
			<div class="flex-1">
				<div class="font-semibold text-gray-900 dark:text-gray-100">
					{data.label || 'Merge'}
				</div>
				{#if data.strategy}
					<div class="text-xs text-gray-500 dark:text-gray-400 capitalize">
						{data.strategy}
					</div>
				{/if}
			</div>
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
			{#if data.status === 'running'}
				<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
			{:else if data.status === 'success'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-4 h-4 text-green-600"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<polyline points="20 6 9 17 4 12" />
				</svg>
			{:else if data.status === 'error'}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-4 h-4 text-red-600"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<circle cx="12" cy="12" r="10" />
					<line x1="15" y1="9" x2="9" y2="15" />
					<line x1="9" y1="9" x2="15" y2="15" />
				</svg>
			{/if}
		</div>
	</div>
	
	<!-- Node Body -->
	<div class="node-body p-3">
		{#if data.strategy}
			<div class="text-xs text-gray-600 dark:text-gray-400">
				<div class="flex items-center gap-2">
					<span class="font-medium">Strategy:</span>
					<span class="capitalize">{data.strategy}</span>
				</div>
				{#if data.strategy === 'concat' && data.separator}
					<div class="mt-1 text-gray-500 dark:text-gray-500">
						Separator: "{data.separator}"
					</div>
				{/if}
			</div>
		{:else}
			<div class="text-xs text-gray-400 dark:text-gray-500 italic">
				Configure merge strategy...
			</div>
		{/if}
		
		{#if data?.error}
			<div class="mt-2 text-xs text-red-600 dark:text-red-400">
				{data.error}
			</div>
		{/if}

		{#if data?.result && data.status === 'success'}
			<div class="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
				<div class="text-xs text-gray-500 dark:text-gray-400">
					Merged successfully
				</div>
			</div>
		{/if}
	</div>
	
	<!-- Output Handle -->
	<Handle
		type="source"
		position={sourceHandlePosition}
		class="!bg-yellow-500"
	/>
</div>
