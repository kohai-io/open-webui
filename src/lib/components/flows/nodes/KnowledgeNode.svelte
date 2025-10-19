<script lang="ts">
	import { Handle, Position } from '@xyflow/svelte';
	import type { KnowledgeNodeData } from '$lib/types/flows';
	
	export let data: KnowledgeNodeData;
	export let selected = false;
	
	const getStatusColor = (status?: string) => {
		switch (status) {
			case 'running':
				return 'border-blue-500 bg-blue-50 dark:bg-blue-900/20';
			case 'success':
				return 'border-green-500 bg-green-50 dark:bg-green-900/20';
			case 'error':
				return 'border-red-500 bg-red-50 dark:bg-red-900/20';
			default:
				return 'border-purple-300 dark:border-purple-600 bg-white dark:bg-gray-800';
		}
	};
</script>

<div
	class="knowledge-node min-w-[200px] rounded-lg border-2 transition-all shadow-md hover:shadow-lg {getStatusColor(
		data.status
	)} {selected ? 'ring-2 ring-purple-500' : ''}"
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
			<div class="text-2xl">📚</div>
			<div class="flex-1">
				<div class="font-semibold text-gray-900 dark:text-gray-100">
					{data.label || 'Knowledge'}
				</div>
				{#if data.knowledgeBaseName}
					<div class="text-xs text-gray-500 dark:text-gray-400">
						{data.knowledgeBaseName}
					</div>
				{/if}
			</div>
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
		{#if data?.query}
			<div class="text-xs text-gray-600 dark:text-gray-400">
				<div class="mb-1">
					<span class="font-medium">Query:</span>
					<div class="line-clamp-2 mt-1">{data.query}</div>
				</div>
				{#if data.topK}
					<div class="text-xs text-gray-500 dark:text-gray-500 mt-1">
						Top {data.topK} results
						{#if data.useReranking}
							• Reranking
						{/if}
						{#if data.hybridSearch}
							• Hybrid
						{/if}
					</div>
				{/if}
			</div>
		{:else}
			<div class="text-xs text-gray-400 dark:text-gray-500 italic">
				Configure knowledge query...
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
					{#if Array.isArray(data.result)}
						{data.result.length} chunk{data.result.length !== 1 ? 's' : ''} retrieved
					{:else}
						Result available
					{/if}
				</div>
			</div>
		{/if}
	</div>
	
	<!-- Output Handle -->
	<Handle
		type="source"
		position={Position.Right}
		class="!bg-purple-500"
	/>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
