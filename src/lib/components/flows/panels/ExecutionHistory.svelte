<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { getFlowExecutions, getFlowExecutionStats, deleteFlowExecution, getFlowExecutionById } from '$lib/apis/flows/executions';
	import type { FlowExecutionListItem, FlowExecutionStats } from '$lib/apis/flows/executions';
	import { toast } from 'svelte-sonner';

	export let flowId: string;
	export let onClose: () => void = () => {};
	export let selectedExecutionId: string | null = null;
	
	const dispatch = createEventDispatcher();

	let executions: FlowExecutionListItem[] = [];
	let stats: FlowExecutionStats | null = null;
	let loading = true;
	let currentPage = 1;

	onMount(async () => {
		await loadExecutions();
		await loadStats();
	});

	const loadExecutions = async () => {
		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			executions = await getFlowExecutions(token, flowId, currentPage);
		} catch (error) {
			console.error('Error loading executions:', error);
			toast.error('Failed to load execution history');
		} finally {
			loading = false;
		}
	};

	const loadStats = async () => {
		try {
			const token = localStorage.getItem('token') || '';
			stats = await getFlowExecutionStats(token, flowId);
		} catch (error) {
			console.error('Error loading stats:', error);
		}
	};

	const handleDelete = async (executionId: string) => {
		try {
			const token = localStorage.getItem('token') || '';
			const success = await deleteFlowExecution(token, flowId, executionId);
			if (success) {
				toast.success('Execution deleted');
				await loadExecutions();
				await loadStats();
			}
		} catch (error) {
			console.error('Error deleting execution:', error);
			toast.error('Failed to delete execution');
		}
	};

	const formatDate = (timestamp: number) => {
		return new Date(timestamp * 1000).toLocaleString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	};

	const formatDuration = (ms: number) => {
		if (ms < 1000) return `${ms}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	};

	const getStatusColor = (status: string) => {
		switch (status) {
			case 'success':
				return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
			case 'error':
				return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
			case 'aborted':
				return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
			default:
				return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-700';
		}
	};

	const getStatusIcon = (status: string) => {
		switch (status) {
			case 'success':
				return '✓';
			case 'error':
				return '✗';
			case 'aborted':
				return '⊘';
			default:
				return '?';
		}
	};
	
	const handleExecutionClick = async (executionId: string) => {
		try {
			const token = localStorage.getItem('token') || '';
			const execution = await getFlowExecutionById(token, flowId, executionId);
			if (execution) {
				selectedExecutionId = executionId;
				// Dispatch event with execution details
				dispatch('selectExecution', execution);
			}
		} catch (error) {
			console.error('Error loading execution details:', error);
			toast.error('Failed to load execution details');
		}
	};
</script>

<div class="flex flex-col h-full bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<div>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
				Execution History
			</h3>
			{#if stats}
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					{stats.total_executions} runs · {stats.success_count} successful
				</p>
			{/if}
		</div>
		<button
			on:click={onClose}
			class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
			title="Close"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		</button>
	</div>

	<!-- Stats -->
	{#if stats && stats.total_executions > 0}
		<div class="p-4 border-b border-gray-200 dark:border-gray-700">
			<div class="grid grid-cols-2 gap-3 text-sm">
				<div class="bg-gray-50 dark:bg-gray-700 rounded p-2">
					<div class="text-gray-500 dark:text-gray-400 text-xs">Success Rate</div>
					<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{Math.round((stats.success_count / stats.total_executions) * 100)}%
					</div>
				</div>
				<div class="bg-gray-50 dark:bg-gray-700 rounded p-2">
					<div class="text-gray-500 dark:text-gray-400 text-xs">Avg Duration</div>
					<div class="text-lg font-semibold text-gray-900 dark:text-gray-100">
						{formatDuration(stats.avg_execution_time)}
					</div>
				</div>
			</div>
		</div>
	{/if}

	<!-- Executions List -->
	<div class="flex-1 overflow-y-auto p-4">
		{#if loading}
			<div class="flex items-center justify-center h-32">
				<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
			</div>
		{:else if executions.length === 0}
			<div class="flex flex-col items-center justify-center h-32 text-center">
				<svg
					class="w-12 h-12 text-gray-400 mb-2"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
					/>
				</svg>
				<p class="text-sm text-gray-500 dark:text-gray-400">No execution history yet</p>
				<p class="text-xs text-gray-400 dark:text-gray-500 mt-1">
					Run the flow to see execution history
				</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each executions as execution (execution.id)}
					<button
						type="button"
						on:click={() => handleExecutionClick(execution.id)}
						class="w-full text-left border rounded-lg p-3 transition-all {selectedExecutionId === execution.id 
							? 'border-blue-500 dark:border-blue-400 bg-blue-50 dark:bg-blue-900/20 shadow-md' 
							: 'border-gray-200 dark:border-gray-700 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-600'}"
					>
						<div class="flex items-start justify-between mb-2">
							<div class="flex items-center gap-2">
								<span
									class={`flex items-center justify-center w-6 h-6 rounded text-xs font-bold ${getStatusColor(execution.status)}`}
								>
									{getStatusIcon(execution.status)}
								</span>
								<div>
									<div class="text-sm font-medium text-gray-900 dark:text-gray-100 capitalize">
										{execution.status}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">
										{formatDate(execution.created_at)}
									</div>
								</div>
							</div>
							<button
								type="button"
								on:click|stopPropagation={() => handleDelete(execution.id)}
								class="p-1 hover:bg-red-50 dark:hover:bg-red-900/20 text-red-600 dark:text-red-400 rounded transition-colors"
								title="Delete"
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
									/>
								</svg>
							</button>
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">
							Duration: {formatDuration(execution.execution_time)}
						</div>
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>
