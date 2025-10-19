<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { getFlowById, updateFlowById } from '$lib/apis/flows';
	import { saveFlowExecution } from '$lib/apis/flows/executions';
	import { toast } from 'svelte-sonner';
	import FlowEditor from '$lib/components/flows/FlowEditor.svelte';
	import ExecutionHistory from '$lib/components/flows/panels/ExecutionHistory.svelte';
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
	let showHistory = false;
	let lastExecutionResults: Record<string, any> = {}; // Store execution results for each node
	let editorViewMode: 'edit' | 'execution' = 'edit'; // Control editor view mode

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
			
			// Only clear value and iteration results for output nodes (execution results)
			// Input nodes use value for their input data
			if (node.type === 'output') {
				clearData.value = undefined;
				clearData.iterationResults = undefined;
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
				// Only update status and error - DON'T spread result to avoid overwriting config
				const updateData: any = { status };
				if (status === 'error' && result?.error) {
					updateData.error = result.error;
				} else if (status === 'success') {
					updateData.error = undefined;
					// Update value for output nodes
					if (result?.value !== undefined) {
						updateData.value = result.value;
					}
					// Preserve iterationResults for Output nodes (from loops)
					if (result?.iterationResults) {
						updateData.iterationResults = result.iterationResults;
					}
				}
				updateNodeData(nodeId, updateData);
			});
			
			// Execute the flow
			const result = await currentExecutor.execute();
			
			// Capture node data (which includes iterationResults) for saving
			const allNodes = get(flowNodes);
			const nodeResultsWithIterations: Record<string, any> = {};
			allNodes.forEach(node => {
				// For each node, save its complete data including iterationResults
				nodeResultsWithIterations[node.id] = {
					...result.nodeResults?.[node.id],
					...node.data // Include visual data which has iterationResults
				};
			});
			
			// Save execution history to backend with complete node data
			try {
				const token = localStorage.getItem('token') || '';
				// Map result status to execution status
				const executionStatus = result.status === 'error' ? 'error' : 'success';
				await saveFlowExecution(token, flowId, {
					flow_id: flowId,
					status: executionStatus,
					inputs: {}, // Could capture input node values here
					outputs: nodeResultsWithIterations,
					node_results: nodeResultsWithIterations,
					errors: result.errors,
					execution_time: result.executionTime
				});
			} catch (saveError) {
				console.error('Failed to save execution history:', saveError);
				// Don't show error to user - execution history is not critical
			}
			
			// Store execution results for each node
			lastExecutionResults = nodeResultsWithIterations;
			console.log('💾 Execution complete, nodeResults with iterations:', nodeResultsWithIterations);
			
			if (result.status === 'success') {
				toast.success(`Flow executed successfully in ${(result.executionTime / 1000).toFixed(2)}s`);
				console.log('Flow results:', nodeResultsWithIterations);
			} else if (result.status === 'error') {
				toast.error('Flow execution failed');
				console.error('Flow errors:', result.errors);
			} else {
				toast.warning('Flow execution completed with warnings');
			}
		} catch (error) {
			console.error('Error executing flow:', error);
			const errorMessage = (error as Error).message;
			
			// Save failed execution to history
			try {
				const token = localStorage.getItem('token') || '';
				await saveFlowExecution(token, flowId, {
					flow_id: flowId,
					status: errorMessage.includes('aborted') ? 'aborted' : 'error',
					inputs: {},
					outputs: {},
					node_results: {},
					errors: { global: errorMessage },
					execution_time: 0
				});
			} catch (saveError) {
				console.error('Failed to save execution history:', saveError);
			}
			
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
	
	const loadHistoricalExecution = (executionDetail: any) => {
		console.log('📋 Loading execution results:', executionDetail);
		const nodeResults = executionDetail.node_results || {};
		console.log('📋 nodeResults from backend:', nodeResults);
		lastExecutionResults = nodeResults;
		
		// Switch to execution history mode
		editorViewMode = 'execution';
		
		// Apply results to visible node data
		const nodes = get(flowNodes);
		nodes.forEach(node => {
			const result = nodeResults[node.id];
			if (result !== undefined) {
				console.log(`Updating ${node.id}:`, result);
				// Update node with execution result
				const updateData: Record<string, unknown> = { status: 'success' };
				
				// For output nodes, preserve iteration results
				if (node.type === 'output') {
					if (result.value !== undefined) updateData.value = result.value;
					if (result.iterationResults !== undefined) {
						updateData.iterationResults = result.iterationResults;
						console.log(`  → Setting iterationResults (${result.iterationResults.length} items)`);
					}
				} else {
					// For other nodes, just update value
					if (result.value !== undefined) updateData.value = result.value;
				}
				
				updateNodeData(node.id, updateData as any);
			}
		});
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
		<!-- Header - Responsive -->
		<div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-0 mb-2 sm:mb-4 p-3 sm:p-4 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-2 sm:gap-3 flex-1 w-full sm:max-w-xl">
				<button
					on:click={handleBack}
					class="p-1.5 sm:p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors flex-shrink-0"
					title="Back to flows"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-4 h-4 sm:w-5 sm:h-5"
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
				<div class="flex-1 min-w-0">
					<input
						type="text"
						value={flow.name}
						on:input={(e) => updateFlowName(e.currentTarget.value)}
						class="w-full text-lg sm:text-2xl font-semibold bg-transparent border-none focus:outline-none focus:ring-0 p-0"
					/>
					<input
						type="text"
						value={flow.description || ''}
						on:input={(e) => updateFlowDescription(e.currentTarget.value)}
						placeholder="Add description (optional)..."
						class="w-full text-xs sm:text-sm text-gray-500 dark:text-gray-400 bg-transparent border-none focus:outline-none focus:ring-0 p-0 mt-1 hidden sm:block"
					/>
				</div>
			</div>
			<div class="flex items-center gap-1.5 sm:gap-2 w-full sm:w-auto">
				<button
					on:click={() => (showHistory = !showHistory)}
					class="px-2 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm {showHistory ? 'bg-gray-200 dark:bg-gray-700' : 'bg-gray-100 dark:bg-gray-800'} hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg font-medium transition-colors flex items-center gap-1 sm:gap-2 flex-1 sm:flex-initial justify-center"
					title="Execution History"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-3 h-3 sm:w-4 sm:h-4"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<path d="M3 3v5h5" />
						<path d="M3.05 13A9 9 0 1 0 6 5.3L3 8" />
					</svg>
					<span class="hidden sm:inline">History</span>
				</button>
				{#if executing || $isExecuting}
					<button
						on:click={stopFlow}
						class="px-2 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors flex items-center gap-1 sm:gap-2 flex-1 sm:flex-initial justify-center"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-3 h-3 sm:w-4 sm:h-4"
							viewBox="0 0 24 24"
							fill="currentColor"
						>
							<rect x="6" y="6" width="12" height="12" />
						</svg>
						<span class="hidden xs:inline">Stop</span>
					</button>
				{:else}
					<button
						on:click={handleExecute}
						disabled={executing || $isExecuting}
						class="px-2 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1 sm:gap-2 flex-1 sm:flex-initial justify-center"
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-3 h-3 sm:w-4 sm:h-4"
							viewBox="0 0 24 24"
							fill="currentColor"
						>
							<polygon points="5 3 19 12 5 21 5 3" />
						</svg>
						<span class="hidden xs:inline">Run</span><span class="hidden sm:inline"> Flow</span>
					</button>
				{/if}
				<button
					on:click={handleSave}
					disabled={saving}
					class="px-2 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex-1 sm:flex-initial justify-center"
				>
					{saving ? 'Saving...' : 'Save'}
				</button>
			</div>
		</div>

		<!-- Flow Editor with History Panel - Responsive Layout -->
		<div class="flex-1 flex flex-col md:flex-row overflow-hidden">
			<div class="flex-1 order-2 md:order-1">
				<FlowEditor 
					{lastExecutionResults}
					viewMode={editorViewMode}
					on:clearResults={() => {
						console.log('🔄 Received clearResults event, clearing data...');
						lastExecutionResults = {};
						clearNodeStates(); // Also clear node status/results
						editorViewMode = 'edit'; // Switch back to edit mode
						console.log('✅ lastExecutionResults and node states cleared');
					}}
				/>
			</div>
			{#if showHistory}
				<div class="h-48 md:h-auto md:w-96 border-b md:border-b-0 md:border-l border-gray-200 dark:border-gray-700 order-1 md:order-2">
					<ExecutionHistory 
						{flowId} 
						onClose={() => (showHistory = false)}
						on:selectExecution={(e) => loadHistoricalExecution(e.detail)}
					/>
				</div>
			{/if}
		</div>
	</div>
{/if}
