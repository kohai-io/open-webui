import { writable, derived, get } from 'svelte/store';
import type { Flow, FlowNode, FlowEdge, FlowExecutionContext } from '$lib/types/flows';

// Store for all flows
export const flows = writable<Flow[]>([]);

// Store for currently active flow in editor
export const currentFlow = writable<Flow | null>(null);

// Store for flow nodes
export const flowNodes = writable<FlowNode[]>([]);

// Store for flow edges
export const flowEdges = writable<FlowEdge[]>([]);

// Store for selected node
export const selectedNode = writable<FlowNode | null>(null);

// Store for execution context
export const executionContext = writable<FlowExecutionContext | null>(null);

// Store for execution status
export const isExecuting = writable<boolean>(false);

// Derived store for flow validation
export const isFlowValid = derived([flowNodes, flowEdges], ([$nodes, $edges]) => {
	if ($nodes.length === 0) return false;

	// Check for at least one input and one output node
	const hasInput = $nodes.some((node) => node.type === 'input');
	const hasOutput = $nodes.some((node) => node.type === 'output');

	// Check for orphaned nodes (except input nodes)
	const nodeIds = new Set($nodes.map((n) => n.id));
	const connectedNodes = new Set<string>();

	$edges.forEach((edge) => {
		connectedNodes.add(edge.source);
		connectedNodes.add(edge.target);
	});

	const orphanedNodes = $nodes.filter(
		(node) => node.type !== 'input' && !connectedNodes.has(node.id)
	);

	return hasInput && hasOutput && orphanedNodes.length === 0;
});

// Helper functions
export const addNode = (node: FlowNode) => {
	flowNodes.update((nodes) => [...nodes, node]);
};

export const updateNode = (nodeId: string, updates: Partial<FlowNode>) => {
	flowNodes.update((nodes) =>
		nodes.map((node) => (node.id === nodeId ? { ...node, ...updates } : node))
	);
};

export const updateNodeData = (nodeId: string, data: Partial<FlowNode['data']>) => {
	flowNodes.update((nodes) =>
		nodes.map((node) =>
			node.id === nodeId ? { ...node, data: { ...node.data, ...data } } : node
		)
	);
};

export const removeNode = (nodeId: string) => {
	flowNodes.update((nodes) => nodes.filter((node) => node.id !== nodeId));
	// Also remove connected edges
	flowEdges.update((edges) =>
		edges.filter((edge) => edge.source !== nodeId && edge.target !== nodeId)
	);
};

export const addEdge = (edge: FlowEdge) => {
	flowEdges.update((edges) => [...edges, edge]);
};

export const removeEdge = (edgeId: string) => {
	flowEdges.update((edges) => edges.filter((edge) => edge.id !== edgeId));
};

export const clearFlow = () => {
	flowNodes.set([]);
	flowEdges.set([]);
	selectedNode.set(null);
	executionContext.set(null);
};

export const loadFlow = (flow: Flow) => {
	currentFlow.set(flow);
	flowNodes.set(flow.nodes);
	flowEdges.set(flow.edges);
	selectedNode.set(null);
	executionContext.set(null);
};

export const saveFlowState = (): Flow | null => {
	const flow = get(currentFlow);
	if (!flow) return null;

	return {
		...flow,
		nodes: get(flowNodes),
		edges: get(flowEdges),
		updated_at: Date.now()
	};
};

// Generate unique node ID
export const generateNodeId = (type: string): string => {
	return `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

// Generate unique edge ID
export const generateEdgeId = (source: string, target: string): string => {
	return `edge_${source}_${target}_${Date.now()}`;
};

// Reset execution state
export const resetExecutionState = () => {
	flowNodes.update((nodes) =>
		nodes.map((node) => ({
			...node,
			data: { ...node.data, status: 'idle', error: undefined }
		}))
	);
	executionContext.set(null);
	isExecuting.set(false);
};
