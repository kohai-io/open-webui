<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getFlowById, updateFlowById } from '$lib/apis/flows';
	import { toast } from 'svelte-sonner';
	import FlowEditor from '$lib/components/flows/FlowEditor.svelte';
	import { currentFlow, loadFlow, saveFlowState, isExecuting, flowNodes, flowEdges, updateNodeData } from '$lib/stores/flows';
	import { FlowExecutor } from '$lib/components/flows/execution/FlowExecutor';
	import type { Flow } from '$lib/types/flows';
	import { get } from 'svelte/store';

	let flowId: string = '';
	let flow: Flow | null = null;
	let loading = true;
	let saving = false;
	let executing = false;
	let currentExecutor: FlowExecutor | null = null;

	$: flowId = $page.params.id || '';

	onMount(async () => {
		await loadFlowData();
	});

	const loadFlowData = async () => {
		loading = true;
		try {
			const token = localStorage.getItem('token') || '';
			const data = await getFlowById(token, flowId);
			if (data) {
				flow = data;
				loadFlow(data);
			} else {
				toast.error('Flow not found');
				goto('/workspace/flows');
			}
		} catch (error) {
			console.error('Error loading flow:', error);
			toast.error('Failed to load flow');
			goto('/workspace/flows');
		} finally {
			loading = false;
		}
	};

	const handleSave = async () => {
		if (!flow) return;

		saving = true;
		try {
			const token = localStorage.getItem('token') || '';
			const flowState = saveFlowState();
			
			if (!flowState) {
				toast.error('No flow data to save');
				return;
			}

			const updated = await updateFlowById(token, flowId, {
				name: flowState.name,
				description: flowState.description,
				nodes: flowState.nodes,
				edges: flowState.edges
			});

			if (updated) {
				flow = updated;
				loadFlow(updated);
				toast.success('Flow saved successfully');
			}
		} catch (error) {
			console.error('Error saving flow:', error);
			toast.error('Failed to save flow');
		} finally {
			saving = false;
		}
	};

	const clearNodeStates = () => {
		// Clear status and error from all nodes, but only clear value from output nodes
		// (Input nodes use 'value' for user input data, not execution results)
		const nodes = get(flowNodes);
		nodes.forEach(node => {
			const clearData: any = { 
				status: undefined, 
				error: undefined
			};
			
			// Only clear value for output nodes (execution results)
			// Input nodes use value for their input data
			if (node.type === 'output') {
				clearData.value = undefined;
			}
			
			updateNodeData(node.id, clearData);
		});
	};

	const handleExecute = async () => {
		if (!flow) return;

		executing = true;
		isExecuting.set(true);
		
		// Clear all node states before starting new execution
		clearNodeStates();
		
		// Get current nodes and edges from store
		const nodes = get(flowNodes);
		const edges = get(flowEdges);
		
		// Validate flow has necessary nodes
		const hasInput = nodes.some(n => n.type === 'input');
		const hasOutput = nodes.some(n => n.type === 'output');
		
		if (!hasInput) {
			toast.error('Flow must have at least one Input node');
			executing = false;
			isExecuting.set(false);
			return;
		}
		
		if (!hasOutput) {
			toast.error('Flow must have at least one Output node');
			executing = false;
			isExecuting.set(false);
			return;
		}
		
		try {
			// Create executor with callback for status updates
			currentExecutor = new FlowExecutor(nodes, edges, (nodeId, status, result) => {
				// Clear error field on success, keep it on error
				const updateData = { status, ...(result || {}) };
				if (status === 'success') {
					updateData.error = undefined;
				}
				updateNodeData(nodeId, updateData);
			});
			
			// Execute the flow
			const result = await currentExecutor.execute();
			
			if (result.status === 'success') {
				toast.success(`Flow executed successfully in ${(result.executionTime / 1000).toFixed(2)}s`);
				console.log('Flow results:', result.nodeResults);
			} else if (result.status === 'error') {
				toast.error('Flow execution failed');
				console.error('Flow errors:', result.errors);
			} else {
				toast.warning('Flow execution completed with warnings');
			}
		} catch (error) {
			console.error('Error executing flow:', error);
			const errorMessage = (error as Error).message;
			if (errorMessage.includes('aborted')) {
				toast.warning('Flow execution stopped');
			} else {
				toast.error('Failed to execute flow: ' + errorMessage);
			}
		} finally {
			executing = false;
			isExecuting.set(false);
			currentExecutor = null;
		}
	};

	const stopFlow = () => {
		if (currentExecutor && executing) {
			currentExecutor.abort();
			toast.info('Stopping flow execution...');
		}
	};

	const handleBack = () => {
		goto('/workspace/flows');
	};

	const updateFlowName = (newName: string) => {
		if (flow) {
			flow.name = newName;
			currentFlow.update((f) => (f ? { ...f, name: newName } : f));
		}
	};

	const updateFlowDescription = (newDesc: string) => {
		if (flow) {
			flow.description = newDesc;
			currentFlow.update((f) => (f ? { ...f, description: newDesc } : f));
		}
	};
</script>

{#if loading}
	<div class="flex items-center justify-center h-full">
		<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
	</div>
{:else if flow}
	<div class="flex flex-col h-full">
		<!-- Header -->
		<div class="flex items-center justify-between mb-4 p-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-3 flex-1 max-w-xl">
				<button
					on:click={handleBack}
					class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
					title="Back to flows"
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
						<line x1="19" y1="12" x2="5" y2="12" />
						<polyline points="12 19 5 12 12 5" />
					</svg>
				</button>
				<div class="flex-1">
					<input
						type="text"
						value={flow.name}
						on:input={(e) => updateFlowName(e.currentTarget.value)}
						class="w-full text-2xl font-semibold bg-transparent border-none focus:outline-none focus:ring-0 p-0"
					/>
					<input
						type="text"
						value={flow.description || ''}
						on:input={(e) => updateFlowDescription(e.currentTarget.value)}
						placeholder="Add description (optional)..."
						class="w-full text-sm text-gray-500 dark:text-gray-400 bg-transparent border-none focus:outline-none focus:ring-0 p-0 mt-1"
					/>
				</div>
			</div>
			<div class="flex items-center gap-2">
				{#if executing || $isExecuting}
					<button
						on:click={stopFlow}
						class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors flex items-center gap-2"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-4 h-4"
							viewBox="0 0 24 24"
							fill="currentColor"
						>
							<rect x="6" y="6" width="12" height="12" />
						</svg>
						Stop
					</button>
				{:else}
					<button
						on:click={handleExecute}
						disabled={executing || $isExecuting}
						class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-4 h-4"
							viewBox="0 0 24 24"
							fill="currentColor"
						>
							<polygon points="5 3 19 12 5 21 5 3" />
						</svg>
						Run Flow
					</button>
				{/if}
				<button
					on:click={handleSave}
					disabled={saving}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{saving ? 'Saving...' : 'Save'}
				</button>
			</div>
		</div>

		<!-- Flow Editor -->
		<div class="flex-1">
			<FlowEditor />
		</div>
	</div>
{/if}
