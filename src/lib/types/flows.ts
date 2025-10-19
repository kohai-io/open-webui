// Flow-based model pipeline type definitions

export type NodeType = 'input' | 'model' | 'output' | 'transform' | 'conditional' | 'loop' | 'merge' | 'knowledge' | 'websearch';

export type NodeStatus = 'idle' | 'running' | 'success' | 'error';

export interface Position {
	x: number;
	y: number;
}

export interface BaseNodeData {
	label: string;
	status?: NodeStatus;
	error?: string;
}

export interface InputNodeData extends BaseNodeData {
	value: string;
	placeholder?: string;
	mediaFileId?: string;
	mediaFileName?: string;
	mediaFileType?: string;
}

export interface ModelNodeData extends BaseNodeData {
	modelId: string;
	modelName?: string;
	prompt: string;
	useAdvancedSettings?: boolean;
	temperature?: number;
	max_tokens?: number;
	top_p?: number;
	frequency_penalty?: number;
	presence_penalty?: number;
	stream?: boolean;
}

export interface OutputNodeData extends BaseNodeData {
	format?: 'text' | 'json' | 'markdown' | 'file';
	fileType?: 'image' | 'video' | 'audio';
	fileId?: string;
	value?: string;
}

export interface TransformNodeData {
	label: string;
	operation: 'uppercase' | 'lowercase' | 'trim' | 'replace' | 'extract' | 'template';
	config: {
		field?: string;
		template?: string;
		pattern?: string;
		replacement?: string;
	};
	status?: 'running' | 'success' | 'error';
	error?: string;
}

export interface ConditionalNodeData extends BaseNodeData {
	condition: string;
	operator: 'equals' | 'contains' | 'greater' | 'less' | 'regex';
	value: string;
}

export interface LoopNodeData extends BaseNodeData {
	maxIterations: number;
	currentIteration?: number;
	breakCondition?: string;
}

export interface MergeNodeData extends BaseNodeData {
	strategy: 'concat' | 'first' | 'last' | 'custom';
	separator?: string;
}

export interface KnowledgeNodeData extends BaseNodeData {
	knowledgeBaseId?: string;
	knowledgeBaseName?: string;
	query?: string;
	topK?: number;
	confidenceThreshold?: number;
	useReranking?: boolean;
	hybridSearch?: boolean;
	includeMetadata?: boolean;
	result?: any;
}

export interface WebSearchNodeData extends BaseNodeData {
	query?: string;
	engine?: string;
	maxResults?: number;
	result?: any;
}

export type NodeData =
	| InputNodeData
	| ModelNodeData
	| OutputNodeData
	| TransformNodeData
	| ConditionalNodeData
	| LoopNodeData
	| MergeNodeData
	| KnowledgeNodeData
	| WebSearchNodeData;

export interface FlowNode {
	id: string;
	type: NodeType;
	position: Position;
	data: NodeData;
	width?: number;
	height?: number;
}

export interface FlowEdge {
	id: string;
	source: string;
	target: string;
	sourceHandle?: string;
	targetHandle?: string;
	label?: string;
	animated?: boolean;
}

export interface Flow {
	id: string;
	name: string;
	description?: string;
	nodes: FlowNode[];
	edges: FlowEdge[];
	created_at: number;
	updated_at: number;
	user_id?: string;
	meta?: {
		tags?: string[];
		category?: string;
		version?: number;
	};
}

export interface FlowExecutionContext {
	flowId: string;
	nodeResults: Map<string, any>;
	errors: Map<string, string>;
	startTime: number;
	variables: Map<string, any>;
}

export interface FlowExecutionResult {
	flowId: string;
	status: 'success' | 'error' | 'partial' | 'cancelled';
	nodeResults: Record<string, any>;
	errors?: Record<string, string>;
	executionTime: number;
	timestamp: number;
}

export interface FlowTemplate {
	id: string;
	name: string;
	description: string;
	category: string;
	icon?: string;
	nodes: FlowNode[];
	edges: FlowEdge[];
}

export interface FlowExport {
	version: string;
	flow: Omit<Flow, 'id' | 'user_id' | 'created_at' | 'updated_at'>;
	exportedAt: number;
}
