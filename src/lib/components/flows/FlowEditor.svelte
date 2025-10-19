<script lang="ts">
	import { SvelteFlow, Controls, Background, MiniMap, Panel } from '@xyflow/svelte';
	import { writable } from 'svelte/store';
	import { createEventDispatcher } from 'svelte';
	import '@xyflow/svelte/dist/style.css';
	
	import {
		flowNodes,
		flowEdges,
		selectedNode,
		addNode,
		addEdge,
		removeNode,
		removeEdge,
		updateNodeData,
		generateNodeId,
		generateEdgeId
	} from '$lib/stores/flows';
	
	import type { FlowNode, FlowEdge, NodeType } from '$lib/types/flows';
	
	const dispatch = createEventDispatcher();
	
	// Node components
	import InputNode from './nodes/InputNode.svelte';
	import ModelNode from './nodes/ModelNode.svelte';
	import OutputNode from './nodes/OutputNode.svelte';
	import TransformNode from './nodes/TransformNode.svelte';
	import KnowledgeNode from './nodes/KnowledgeNode.svelte';
	import WebSearchNode from './nodes/WebSearchNode.svelte';
	import ConditionalNode from './nodes/ConditionalNode.svelte';
	import LoopNode from './nodes/LoopNode.svelte';
	import MergeNode from './nodes/MergeNode.svelte';
	
	// Panels
	import NodeLibrary from './panels/NodeLibrary.svelte';
	import NodeConfig from './panels/NodeConfig.svelte';
	
	const nodeTypes = {
		model: ModelNode,
		input: InputNode,
		output: OutputNode,
		transform: TransformNode,
		knowledge: KnowledgeNode,
		websearch: WebSearchNode,
		conditional: ConditionalNode,
		loop: LoopNode,
		merge: MergeNode
	};
	
	export let lastExecutionResults: Record<string, any> = {}; // Passed from parent page
	export let viewMode: 'edit' | 'execution' = 'edit'; // Toggle between edit and execution history - can be controlled by parent
	
	let showNodeLibrary = false; // Will be set based on whether flow is new or existing
	let showNodeConfig = false;
	
	// Show node library by default only for new flows (no nodes)
	$: if ($flowNodes.length === 0 && !showNodeLibrary) {
		showNodeLibrary = true;
	}
	
	// Responsive handle positioning
	let isMobile = false;
	let windowWidth = 1024; // Default to desktop
	let previousMobileState = false;
	let flowKey = 0; // Used to force re-render and trigger fitView
	
	$: isMobile = windowWidth < 768;
	
	// Function to estimate node height based on type and content
	function estimateNodeHeight(node: FlowNode): number {
		// Use actual height if available
		if (node.height) return node.height;
		
		// Base heights for different node types
		const baseHeights: Record<string, number> = {
			input: 200,      // Usually has content/media
			model: 150,      // Compact with model info
			output: 150,     // Compact with format
			transform: 150,
			knowledge: 150,
			websearch: 150,
			conditional: 180,
			loop: 180,
			merge: 150
		};
		
		let estimatedHeight = baseHeights[node.type] || 150;
		
		// Adjust for input nodes with media
		if (node.type === 'input' && (node.data as any).mediaFileId) {
			estimatedHeight = 300; // Taller for image preview
		}
		
		return estimatedHeight;
	}
	
	// Function to reorganize node positions based on layout direction
	function reorganizeNodePositions(nodes: FlowNode[], edges: FlowEdge[], isVertical: boolean) {
		if (nodes.length === 0) return nodes;
		
		// Create a map of nodes by id for quick lookup
		const nodeMap = new Map(nodes.map(n => [n.id, n]));
		
		// Build adjacency list (which nodes connect to which)
		const adjacency = new Map<string, string[]>();
		const inDegree = new Map<string, number>();
		
		nodes.forEach(node => {
			adjacency.set(node.id, []);
			inDegree.set(node.id, 0);
		});
		
		edges.forEach(edge => {
			if (adjacency.has(edge.source)) {
				adjacency.get(edge.source)!.push(edge.target);
			}
			if (inDegree.has(edge.target)) {
				inDegree.set(edge.target, inDegree.get(edge.target)! + 1);
			}
		});
		
		// Find starting nodes (nodes with no inputs)
		const startNodes = nodes.filter(n => inDegree.get(n.id) === 0);
		
		// Layout configuration
		const HORIZONTAL_SPACING = 300; // Space between nodes going left-to-right
		const NODE_GAP = 50;            // Tighter gap between nodes in vertical layout for consistency
		const BRANCH_SPACING_HORIZONTAL = 150; // Space between parallel branches (horizontal layout)
		const BRANCH_SPACING_VERTICAL = 350;   // Space between parallel branches (vertical layout) - wider for node width
		const START_X = 100;
		const START_Y = 50;  // Reduced to give more viewport space
		
		// Position nodes based on layout
		const positioned = new Set<string>();
		const newPositions = new Map<string, { x: number; y: number }>();
		const depthYPositions = new Map<number, number>(); // Track Y position for each depth level
		
		function positionNode(nodeId: string, depth: number, offset: number = 0, parentNodeId?: string) {
			if (positioned.has(nodeId)) return;
			positioned.add(nodeId);
			
			const currentNode = nodeMap.get(nodeId);
			if (!currentNode) return;
			
			if (isVertical) {
				// Vertical layout: adaptive spacing based on previous node height
				let yPosition: number;
				
				if (depth === 0 || !depthYPositions.has(depth)) {
					// First node at this depth
					yPosition = START_Y + (depth === 0 ? 0 : depthYPositions.get(depth - 1)! + NODE_GAP);
				} else {
					// Use existing position for this depth
					yPosition = depthYPositions.get(depth)!;
				}
				
				// If there's a parent, calculate position based on parent's position + height + gap
				if (parentNodeId) {
					const parentNode = nodeMap.get(parentNodeId);
					const parentPos = newPositions.get(parentNodeId);
					if (parentNode && parentPos) {
						const parentHeight = estimateNodeHeight(parentNode);
						yPosition = parentPos.y + parentHeight + NODE_GAP;
					}
				}
				
				newPositions.set(nodeId, {
					x: START_X + (offset * BRANCH_SPACING_VERTICAL),
					y: yPosition
				});
				
				// Update depth Y position for next node
				depthYPositions.set(depth, yPosition);
				
			} else {
				// Horizontal layout: spread left to right, stack branches vertically
				newPositions.set(nodeId, {
					x: START_X + (depth * HORIZONTAL_SPACING),
					y: START_Y + (offset * BRANCH_SPACING_HORIZONTAL)
				});
			}
			
			// Position children
			const children = adjacency.get(nodeId) || [];
			children.forEach((childId, index) => {
				positionNode(childId, depth + 1, index, nodeId);
			});
		}
		
		// Position all start nodes and their descendants
		startNodes.forEach((node, index) => {
			positionNode(node.id, 0, index);
		});
		
		// Position any remaining unconnected nodes
		let unconnectedYOffset = 0;
		nodes.forEach((node, index) => {
			if (!positioned.has(node.id)) {
				if (isVertical) {
					// Get the max Y position from already positioned nodes
					let maxY = START_Y;
					newPositions.forEach(pos => {
						if (pos.y > maxY) maxY = pos.y;
					});
					
					newPositions.set(node.id, {
						x: START_X + BRANCH_SPACING_VERTICAL,
						y: maxY + 200 + unconnectedYOffset // Add below existing nodes
					});
					unconnectedYOffset += estimateNodeHeight(node) + NODE_GAP;
				} else {
					newPositions.set(node.id, {
						x: START_X + (positioned.size * HORIZONTAL_SPACING),
						y: START_Y + BRANCH_SPACING_HORIZONTAL
					});
				}
				positioned.add(node.id);
			}
		});
		
		// Apply new positions to nodes
		return nodes.map(node => ({
			...node,
			position: newPositions.get(node.id) || node.position
		}));
	}
	
	// Update handle positions and reorganize when mobile state changes
	$: if (typeof window !== 'undefined' && isMobile !== previousMobileState) {
		previousMobileState = isMobile;
		flowNodes.update((nodes: FlowNode[]): FlowNode[] => {
			// First update handle positions
			const sourcePos: 'left' | 'right' | 'top' | 'bottom' = isMobile ? 'bottom' : 'right';
			const targetPos: 'left' | 'right' | 'top' | 'bottom' = isMobile ? 'top' : 'left';
			
			let updatedNodes: FlowNode[] = nodes.map((node: FlowNode): FlowNode => ({
				...node,
				sourcePosition: sourcePos,
				targetPosition: targetPos
			}));
			
			// Then reorganize positions based on layout
			updatedNodes = reorganizeNodePositions(updatedNodes, $flowEdges, isMobile);
			
			// Increment key to trigger fitView (SvelteFlow will auto-fit on re-render)
			setTimeout(() => {
				flowKey++;
			}, 100);
			
			return updatedNodes;
		});
	}
	
	// Debug: Log when execution results change
	$: if (Object.keys(lastExecutionResults).length > 0) {
		console.log('🔍 FlowEditor: Execution results updated, count:', Object.keys(lastExecutionResults).length);
	}
	
	// Reactive execution result for selected node
	$: selectedNodeExecutionResult = $selectedNode ? lastExecutionResults[$selectedNode.id] : undefined;
	
	const handleNodeClick = (event: CustomEvent) => {
		const node = event.detail.node as FlowNode;
		selectedNode.set(node);
	};
	
	// Listen for config button clicks from nodes
	if (typeof window !== 'undefined') {
		window.addEventListener('open-node-config', () => {
			showNodeConfig = true;
		});
	}
	
	const handlePaneClick = () => {
		selectedNode.set(null);
		showNodeConfig = false; // Close config panel when clicking canvas
	};
	
	const handleClearResults = () => {
		console.log('🗑️ Clear Results clicked');
		// Dispatch event to parent to clear execution results
		dispatch('clearResults');
		console.log('✅ clearResults event dispatched');
		// Also switch back to edit mode
		viewMode = 'edit';
	};
	
	const handleConnect = (event: CustomEvent) => {
		const { source, target } = event.detail.connection;
		const edgeId = generateEdgeId(source, target);
		
		// Check if edge already exists
		if ($flowEdges.some((e) => e.id === edgeId)) {
			return;
		}
		
		const newEdge: FlowEdge = {
			id: edgeId,
			source,
			target,
			animated: true
		};
		
		addEdge(newEdge);
	};
	
	const handleNodesChange = (event: CustomEvent) => {
		const changes = event.detail;
		// Handle node position changes, deletions, etc.
		changes.forEach((change: any) => {
			if (change.type === 'position' && change.position) {
				const node = $flowNodes.find((n) => n.id === change.id);
				if (node) {
					flowNodes.update((nodes) =>
						nodes.map((n) =>
							n.id === change.id ? { ...n, position: change.position } : n
						)
					);
				}
			} else if (change.type === 'remove') {
				removeNode(change.id);
			}
		});
	};
	
	const handleEdgesChange = (event: CustomEvent) => {
		const changes = event.detail;
		changes.forEach((change: any) => {
			if (change.type === 'remove') {
				removeEdge(change.id);
			}
		});
	};
	
	const handleNodeDelete = (nodeId: string) => {
		removeNode(nodeId);
		if ($selectedNode?.id === nodeId) {
			selectedNode.set(null);
		}
	};
	
	const handleAddNode = (type: NodeType, position?: { x: number; y: number }) => {
		const id = generateNodeId(type);
		const nodePosition = position || {
			x: Math.random() * 500,
			y: Math.random() * 500
		};
		
		// Set handle positions based on screen size
		const sourcePosition = isMobile ? 'bottom' : 'right';
		const targetPosition = isMobile ? 'top' : 'left';
		
		let nodeData: any = { label: type.charAt(0).toUpperCase() + type.slice(1) };
		
		switch (type) {
			case 'input':
				nodeData = {
					label: 'Input',
					value: '',
					placeholder: 'Enter input text...'
				};
				break;
			case 'model':
				nodeData = {
					label: 'Model',
					modelId: '',
					modelName: '',
					prompt: '',
					useAdvancedSettings: false,
					temperature: 0.7
				};
				break;
			case 'knowledge':
				nodeData = {
					label: 'Knowledge',
					knowledgeBaseId: '',
					knowledgeBaseName: '',
					query: '{{input}}',
					topK: 4,
					confidenceThreshold: 0,
					useReranking: false,
					hybridSearch: false,
					includeMetadata: true
				};
				break;
			case 'websearch':
				nodeData = {
					label: 'Web Search',
					query: '{{input}}',
					engine: '',
					maxResults: 5
				};
				break;
			case 'conditional':
				nodeData = {
					label: 'Conditional',
					condition: '{{input}}',
					operator: 'equals',
					compareValue: ''
				};
				break;
			case 'loop':
				nodeData = {
					label: 'Loop',
					loopType: 'count',
					maxIterations: 5,
					currentIteration: 0
				};
				break;
			case 'merge':
				nodeData = {
					label: 'Merge',
					strategy: 'concat',
					separator: '\n'
				};
				break;
			case 'transform':
				nodeData = {
					label: 'Transform',
					operation: '',
					config: {}
				};
				break;
			case 'output':
				nodeData = {
					label: 'Output',
					format: 'text'
				};
				break;
		}
		
		const newNode: FlowNode = {
			id,
			type,
			position: nodePosition,
			data: nodeData,
			sourcePosition,
			targetPosition
		};
		
		addNode(newNode);
	};
	
	const toggleNodeLibrary = () => {
		showNodeLibrary = !showNodeLibrary;
	};
	
	// Handle keyboard events for deletion
	const handleKeyDown = (event: KeyboardEvent) => {
		// Don't handle if we're typing in an input/textarea
		const target = event.target as HTMLElement;
		if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
			return;
		}
		
		// Only handle Delete key, not Backspace (to avoid browser back)
		if (event.key === 'Delete') {
			// Check if any edges are selected
			const selectedEdges = $flowEdges.filter((edge: any) => edge.selected);
			if (selectedEdges.length > 0) {
				event.preventDefault();
				selectedEdges.forEach((edge: any) => {
					removeEdge(edge.id);
				});
			}
			
			// Check if any nodes are selected
			const selectedNodes = $flowNodes.filter((node: any) => node.selected);
			if (selectedNodes.length > 0) {
				event.preventDefault();
				selectedNodes.forEach((node: any) => {
					removeNode(node.id);
					if ($selectedNode?.id === node.id) {
						selectedNode.set(null);
					}
				});
			}
		}
	};
</script>

<svelte:window bind:innerWidth={windowWidth} />

<div 
	class="flow-editor-container w-full h-full relative"
	on:keydown={handleKeyDown}
	role="application"
	tabindex="-1"
>
	{#key flowKey}
		<SvelteFlow
			nodes={flowNodes}
			edges={flowEdges}
			{nodeTypes}
			on:nodeclick={handleNodeClick}
			on:paneclick={handlePaneClick}
			on:connect={handleConnect}
			on:nodeschange={handleNodesChange}
			on:edgeschange={handleEdgesChange}
			deleteKeyCode={null}
			multiSelectionKeyCode={null}
			selectionKeyCode={null}
			edgesUpdatable={true}
			edgesFocusable={true}
			panOnDrag={[1, 2]}
			defaultEdgeOptions={{
				type: 'default',
				style: 'stroke-width: 3;'
			}}
			fitView
			class="bg-gray-50 dark:bg-gray-900"
		>
		<Background
			variant="dots"
			gap={16}
			size={1}
			color="#94a3b8"
		/>
		<Controls />
		<MiniMap
			nodeColor="#3b82f6"
			maskColor="rgb(0, 0, 0, 0.1)"
		/>
		
		<!-- Mode Toggle Panel - Responsive -->
		<Panel position="top-center" class="m-2 md:m-4">
			<div class="flex items-center gap-1 md:gap-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-1">
				<button
					on:click={() => viewMode = 'edit'}
					class="px-2 py-1 md:px-4 md:py-2 rounded-md font-medium transition-all text-xs md:text-sm {viewMode === 'edit' 
						? 'bg-blue-600 text-white shadow-md' 
						: 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
				>
					<span class="hidden sm:inline">✏️ Edit Mode</span>
					<span class="sm:hidden">✏️ Edit</span>
				</button>
				<button
					on:click={() => viewMode = 'execution'}
					class="px-2 py-1 md:px-4 md:py-2 rounded-md font-medium transition-all text-xs md:text-sm {viewMode === 'execution' 
						? 'bg-green-600 text-white shadow-md' 
						: 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
				>
					<span class="hidden sm:inline">📊 Execution History</span>
					<span class="sm:hidden">📊 History</span>
				</button>
				
				<!-- Clear Results Button (only show if results exist) -->
				{#if Object.keys(lastExecutionResults).length > 0}
					<div class="w-px h-6 bg-gray-300 dark:bg-gray-600"></div>
					<button
						on:click={handleClearResults}
						class="px-2 py-1 md:px-3 md:py-2 rounded-md font-medium text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all flex items-center gap-1"
						title="Clear execution results"
					>
						<span class="hidden sm:inline">🗑️ Clear Results</span>
						<span class="sm:hidden">🗑️</span>
					</button>
				{/if}
			</div>
		</Panel>
		
		<!-- Top Panel with Add Node Button - Responsive -->
		<Panel position="top-left" class="m-2 md:m-4">
			<button
				on:click={toggleNodeLibrary}
				class="px-3 py-2 md:px-5 md:py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all flex items-center gap-2 border-2 border-blue-500 text-sm md:text-base"
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
					{#if showNodeLibrary}
						<line x1="5" y1="12" x2="19" y2="12" />
					{:else}
						<line x1="12" y1="5" x2="12" y2="19" />
						<line x1="5" y1="12" x2="19" y2="12" />
					{/if}
				</svg>
				{showNodeLibrary ? 'Hide Nodes' : '+ Add Nodes'}
			</button>
		</Panel>
		
		<!-- Instructions Panel - Responsive -->
		{#if $flowNodes.length === 0}
			<Panel position="top-center" class="m-2 md:m-4">
				<div class="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-600 rounded-lg shadow-xl p-4 md:p-6 max-w-xs md:max-w-lg">
					<h3 class="text-lg font-bold mb-3 text-blue-900 dark:text-blue-100">👋 Welcome to Flow Builder!</h3>
					<div class="space-y-2 text-sm text-gray-700 dark:text-gray-300">
						<p class="font-medium">To get started:</p>
						<ol class="list-decimal list-inside space-y-1 ml-2">
							<li>Click the <strong>"+ Add Nodes"</strong> button on the left</li>
							<li>Select a node type (Input, Model, or Output)</li>
							<li>Drag nodes to position them</li>
							<li>Connect nodes by dragging from output to input</li>
						</ol>
					</div>
				</div>
			</Panel>
		{/if}
	</SvelteFlow>
	{/key}
	
	<!-- Node Library Panel - Responsive -->
	{#if showNodeLibrary}
		<div class="absolute z-10 nopan nodrag nowheel
			left-4 right-4 bottom-4 max-h-96
			md:left-4 md:right-auto md:top-20 md:bottom-auto md:max-h-none
			w-full md:w-72 max-w-md md:max-w-none
			overflow-y-auto md:overflow-visible">
			<NodeLibrary on:addnode={(e) => handleAddNode(e.detail.type)} />
		</div>
	{/if}
	
	<!-- Node Configuration Panel - Responsive -->
	{#if showNodeConfig && $selectedNode}
		<div class="absolute z-10 nopan nodrag nowheel
			left-4 right-4 bottom-4 max-h-[70vh]
			md:right-4 md:left-auto md:top-4 md:bottom-4 md:max-h-none
			w-auto md:w-80
			overflow-y-auto md:overflow-visible">
			<NodeConfig
				node={$selectedNode}
				nodes={$flowNodes}
				edges={$flowEdges}
				{viewMode}
				executionResult={selectedNodeExecutionResult}
				on:update={(e) => updateNodeData($selectedNode.id, e.detail)}
				on:delete={() => handleNodeDelete($selectedNode.id)}
				on:close={() => selectedNode.set(null)}
			/>
		</div>
	{/if}
</div>

<style>
	:global(.flow-editor-container .svelte-flow) {
		width: 100%;
		height: 100%;
	}
	
	:global(.svelte-flow__node) {
		border: none;
		outline: none;
		box-shadow: none;
		padding: 0;
		margin: 0;
		box-sizing: border-box;
		width: fit-content !important;
		height: fit-content !important;
		max-width: 400px;
	}
	
	/* Ensure inner node content determines the size */
	:global(.svelte-flow__node > div) {
		box-sizing: border-box;
		display: block;
	}
	
	/* Handle positioning - center on node borders */
	:global(.svelte-flow__handle) {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		border: 2px solid white;
		transform: translate(-50%, -50%);
	}
	
	:global(.svelte-flow__handle-left) {
		left: 0;
		top: 50%;
		transform: translate(-50%, -50%);
	}
	
	:global(.svelte-flow__handle-right) {
		right: 0;
		top: 50%;
		transform: translate(50%, -50%);
	}
	
	:global(.svelte-flow__handle-top) {
		top: 0;
		left: 50%;
		transform: translate(-50%, -50%);
	}
	
	:global(.svelte-flow__handle-bottom) {
		bottom: 0;
		left: 50%;
		transform: translate(-50%, 50%);
	}
	
	
	/* Make edges thicker and easier to select */
	:global(.svelte-flow__edge-path) {
		stroke-width: 3;
	}
	
	/* Invisible wider hitbox for easier selection */
	:global(.svelte-flow__edge-interaction) {
		stroke-width: 20 !important;
	}
	
	/* Visual feedback when hovering */
	:global(.svelte-flow__edge:hover .svelte-flow__edge-path) {
		stroke-width: 4;
	}
	
	/* Visual feedback when selected */
	:global(.svelte-flow__edge.selected .svelte-flow__edge-path) {
		stroke: #3b82f6 !important;
		stroke-width: 4;
	}
	
	:global(.svelte-flow__edge.animated path) {
		stroke-dasharray: 5;
		animation: dashdraw 0.5s linear infinite;
	}
	
	@keyframes dashdraw {
		from {
			stroke-dashoffset: 10;
		}
	}
</style>
