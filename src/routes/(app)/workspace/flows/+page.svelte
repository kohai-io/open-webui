<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { getFlows, deleteFlowById, duplicateFlowById } from '$lib/apis/flows';
	import { flows } from '$lib/stores/flows';
	import { user } from '$lib/stores';
	import { toast } from 'svelte-sonner';
	import type { Flow } from '$lib/types/flows';

	let loading = true;
	let flowList: Flow[] = [];
	let searchQuery = '';
	let showDeleteConfirm = false;
	let flowToDelete: Flow | null = null;

	onMount(async () => {
		await loadFlows();
	});

	const loadFlows = async () => {
		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			const data = await getFlows(token);
			if (data) {
				flowList = data;
				flows.set(data);
			}
		} catch (error) {
			console.error('Error loading flows:', error);
			toast.error('Failed to load flows');
		} finally {
			loading = false;
		}
	};

	const createNewFlow = () => {
		goto('/workspace/flows/create');
	};

	const editFlow = (flowId: string) => {
		goto(`/workspace/flows/${flowId}`);
	};

	const confirmDelete = (flow: Flow) => {
		flowToDelete = flow;
		showDeleteConfirm = true;
	};

	const deleteFlow = async () => {
		if (!flowToDelete) return;

		try {
			const token = localStorage.getItem('token') || '';
			await deleteFlowById(token, flowToDelete.id);
			toast.success('Flow deleted successfully');
			await loadFlows();
		} catch (error) {
			console.error('Error deleting flow:', error);
			toast.error('Failed to delete flow');
		} finally {
			showDeleteConfirm = false;
			flowToDelete = null;
		}
	};

	const duplicateFlow = async (flow: Flow) => {
		try {
			const token = localStorage.getItem('token') || '';
			const duplicated = await duplicateFlowById(token, flow.id, `${flow.name} (Copy)`);
			if (duplicated) {
				toast.success('Flow duplicated successfully');
				await loadFlows();
			}
		} catch (error) {
			console.error('Error duplicating flow:', error);
			toast.error('Failed to duplicate flow');
		}
	};

	$: filteredFlows = flowList.filter((flow) =>
		flow.name.toLowerCase().includes(searchQuery.toLowerCase())
	);

	const formatDate = (timestamp: number) => {
		// Backend stores timestamps in seconds, JavaScript expects milliseconds
		return new Date(timestamp * 1000).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	};
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between mb-6">
		<div>
			<h1 class="text-2xl font-semibold">Flows</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				Create visual workflows to chain multiple models together
			</p>
		</div>
		<button
			on:click={createNewFlow}
			class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-5 h-5"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<line x1="12" y1="5" x2="12" y2="19" />
				<line x1="5" y1="12" x2="19" y2="12" />
			</svg>
			Create Flow
		</button>
	</div>

	<!-- Search -->
	<div class="mb-4">
		<input
			type="text"
			bind:value={searchQuery}
			placeholder="Search flows..."
			class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
		/>
	</div>

	<!-- Flows Grid -->
	{#if loading}
		<div class="flex items-center justify-center h-64">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
		</div>
	{:else if filteredFlows.length === 0}
		<div class="flex flex-col items-center justify-center h-64 text-center">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-16 h-16 text-gray-400 mb-4"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<rect x="3" y="3" width="7" height="7" />
				<rect x="14" y="3" width="7" height="7" />
				<rect x="14" y="14" width="7" height="7" />
				<rect x="3" y="14" width="7" height="7" />
			</svg>
			<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No flows yet</h3>
			<p class="text-gray-500 dark:text-gray-400 mb-4">
				{searchQuery ? 'No flows match your search' : 'Create your first flow to get started'}
			</p>
			{#if !searchQuery}
				<button
					on:click={createNewFlow}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
				>
					Create Flow
				</button>
			{/if}
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each filteredFlows as flow (flow.id)}
				<div
					class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-lg transition-shadow bg-white dark:bg-gray-800 cursor-pointer"
					on:click={() => editFlow(flow.id)}
					role="button"
					tabindex="0"
					on:keydown={(e) => e.key === 'Enter' && editFlow(flow.id)}
				>
					<div class="flex items-start justify-between mb-3">
						<div class="flex-1">
							<h3 class="font-semibold text-gray-900 dark:text-gray-100 mb-1">
								{flow.name}
							</h3>
							{#if flow.description}
								<p class="text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
									{flow.description}
								</p>
							{/if}
						</div>
					</div>

					<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 mb-3">
						<span>{flow.nodes.length} nodes</span>
						<span>{formatDate(flow.updated_at)}</span>
					</div>

					<div class="flex items-center gap-2" on:click|stopPropagation>
						<button
							on:click={() => editFlow(flow.id)}
							class="flex-1 px-3 py-1.5 text-sm bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
						>
							Edit
						</button>
						<button
							on:click={() => duplicateFlow(flow)}
							class="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
							title="Duplicate"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-4 h-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
								<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
							</svg>
						</button>
						<button
							on:click={() => confirmDelete(flow)}
							class="px-3 py-1.5 text-sm bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
							title="Delete"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-4 h-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
								stroke-linecap="round"
								stroke-linejoin="round"
							>
								<polyline points="3 6 5 6 21 6" />
								<path
									d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
								/>
							</svg>
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Delete Confirmation Modal -->
{#if showDeleteConfirm && flowToDelete}
	<div
		class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
		on:click={() => (showDeleteConfirm = false)}
		role="button"
		tabindex="0"
	>
		<div
			class="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4"
			on:click|stopPropagation
			role="dialog"
		>
			<h3 class="text-lg font-semibold mb-2">Delete Flow</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-4">
				Are you sure you want to delete "{flowToDelete.name}"? This action cannot be undone.
			</p>
			<div class="flex justify-end gap-2">
				<button
					on:click={() => (showDeleteConfirm = false)}
					class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
				>
					Cancel
				</button>
				<button
					on:click={deleteFlow}
					class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded transition-colors"
				>
					Delete
				</button>
			</div>
		</div>
	</div>
{/if}
