<script lang="ts">
	import { SvelteFlow, Controls, Background, MiniMap, Panel } from '@xyflow/svelte';
	import { writable } from 'svelte/store';
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
	
	// Node components
	import InputNode from './nodes/InputNode.svelte';
	import ModelNode from './nodes/ModelNode.svelte';
	import OutputNode from './nodes/OutputNode.svelte';
	import TransformNode from './nodes/TransformNode.svelte';
	import KnowledgeNode from './nodes/KnowledgeNode.svelte';
	import WebSearchNode from './nodes/WebSearchNode.svelte';
	
	// Panels
	import NodeLibrary from './panels/NodeLibrary.svelte';
	import NodeConfig from './panels/NodeConfig.svelte';
	
	const nodeTypes = {
		model: ModelNode,
		input: InputNode,
		output: OutputNode,
		transform: TransformNode,
		knowledge: KnowledgeNode,
		websearch: WebSearchNode
	};
	
	let showNodeLibrary = true;
	let showNodeConfig = false;
	
	$: showNodeConfig = $selectedNode !== null;
	
	const handleNodeClick = (event: CustomEvent) => {
		const node = event.detail.node as FlowNode;
		selectedNode.set(node);
	};
	
	const handlePaneClick = () => {
		selectedNode.set(null);
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
			data: nodeData
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

<div 
	class="flow-editor-container w-full h-full relative"
	on:keydown={handleKeyDown}
	role="application"
	tabindex="-1"
>
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
		
		<!-- Top Panel with Add Node Button -->
		<Panel position="top-left" class="m-4">
			<button
				on:click={toggleNodeLibrary}
				class="px-5 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all flex items-center gap-2 border-2 border-blue-500"
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
		
		<!-- Instructions Panel -->
		{#if $flowNodes.length === 0}
			<Panel position="top-center" class="m-4">
				<div class="bg-blue-50 dark:bg-blue-900/20 border-2 border-blue-300 dark:border-blue-600 rounded-lg shadow-xl p-6 max-w-lg">
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
	
	<!-- Node Library Panel -->
	{#if showNodeLibrary}
		<div class="absolute left-4 top-20 z-10 nopan nodrag nowheel">
			<NodeLibrary on:addnode={(e) => handleAddNode(e.detail.type)} />
		</div>
	{/if}
	
	<!-- Node Configuration Panel -->
	{#if showNodeConfig && $selectedNode}
		<div class="absolute right-4 top-4 bottom-4 w-80 z-10 nopan nodrag nowheel">
			<NodeConfig
				node={$selectedNode}
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
