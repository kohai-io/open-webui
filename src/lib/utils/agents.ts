/**
 * Utility functions for working with agents and models
 */

export interface AgentModel {
	id: string;
	name: string;
	is_active?: boolean;
	user_id?: string;
	base_model_id?: string;
	owned_by?: string;
	access_control?: {
		read?: {
			group_ids?: string[];
			user_ids?: string[];
		};
		write?: {
			group_ids?: string[];
			user_ids?: string[];
		};
	};
	meta?: {
		profile_image_url?: string;
		description?: string;
		hidden?: boolean;
	};
	info?: {
		user_id?: string;
		base_model_id?: string;
		meta?: {
			profile_image_url?: string;
			description?: string;
		};
	};
}

/**
 * Get the profile image URL for an agent or model
 * Falls back to default favicon if no image is available
 */
export const getProfileImage = (item: AgentModel): string => {
	return item?.meta?.profile_image_url ?? item?.info?.meta?.profile_image_url ?? '/static/favicon.png';
};

/**
 * Get the description for an agent or model
 * Returns empty string if no description is available
 */
export const getDescription = (item: AgentModel): string => {
	return item?.meta?.description ?? item?.info?.meta?.description ?? '';
};

/**
 * Categorize agents and models into different groups
 */
export interface CategorizedAgents {
	foundationalModels: AgentModel[];
	myAgents: AgentModel[];
	sharedAgents: AgentModel[];
	systemAgents: AgentModel[];
}

export const categorizeAgents = (
	allModels: AgentModel[],
	workspaceModels: AgentModel[],
	functions: any[],
	currentUserId: string
): CategorizedAgents => {
	/**
	 * Categorization Logic:
	 * - allModels: from /api/models (includes base models + custom models)
	 * - workspaceModels: from /api/v1/models/list (only custom models with base_model_id != None)
	 * - functions: from /api/functions (system functions/pipelines)
	 * 
	 * Key distinction:
	 * - Foundational models: Models without base_model_id (even if customized by admin)
	 * - Agents: Models WITH base_model_id (user-created assistants based on foundational models)
	 * 
	 * Models with user_id but without base_model_id are base model overrides (customized foundational models)
	 * and should appear in Foundational Models, not as agents.
	 */

	// Merge workspace metadata with all models
	const mergedModels = allModels.map(m => {
		const workspaceModel = workspaceModels.find(wm => wm.id === m.id);
		return workspaceModel ? { ...m, ...workspaceModel } : m;
	});

	// Get function IDs and assistant IDs for categorization
	const functionIds = new Set(functions.map(a => a.id));
	const assistantIds = new Set(workspaceModels.filter(m => m.base_model_id).map(m => m.id));
	
	// All models from workspaceModels are user-created (includes assistants and custom models)
	const workspaceModelIds = new Set(workspaceModels.map(m => m.id));
	
	// Also check for models with user_id AND base_model_id that might not be in workspaceModels
	// Models with user_id but WITHOUT base_model_id are base model overrides (customized foundational models)
	// and should appear in foundational models, not agents
	const modelsWithUserId = new Set(
		mergedModels
			.filter(m => 
				!workspaceModelIds.has(m.id) && 
				(m.user_id || m.info?.user_id) &&
				(m.base_model_id || m.info?.base_model_id)  // Only if they have a base_model_id
			)
			.map(m => m.id)
	);
	
	const agentIds = new Set([...functionIds, ...assistantIds, ...workspaceModelIds, ...modelsWithUserId]);

	// Foundational models (base models, not agents/assistants)
	// Only models that are not in agentIds are truly foundational
	// agentIds already includes all user-created models (via workspaceModelIds and modelsWithUserId)
	const foundationalModels = mergedModels.filter(m => 
		m.is_active !== false && 
		!agentIds.has(m.id)
	);

	// All agents (includes assistants, functions, and user-created models)
	const allAgents = mergedModels.filter(m => 
		m.is_active !== false && 
		agentIds.has(m.id)
	);

	// Separate into user-created, shared (other users), and system agents (functions/pipelines)
	// Don't include functions in myAgents to avoid duplication with systemAgents
	// Check both m.user_id and m.info?.user_id since backend may place it in different locations
	const myAgents = allAgents.filter(m => {
		const userId = m.user_id || m.info?.user_id;
		return userId === currentUserId && !functionIds.has(m.id);
	});
	
	const systemAgents = allAgents.filter(m => functionIds.has(m.id));
	
	const sharedAgents = allAgents.filter(m => {
		const userId = m.user_id || m.info?.user_id;
		return !functionIds.has(m.id) && userId && userId !== currentUserId;
	});

	return {
		foundationalModels,
		myAgents,
		sharedAgents,
		systemAgents
	};
};
