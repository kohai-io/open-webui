/**
 * Utility functions for working with agents and models
 */

export interface AgentModel {
	id: string;
	name: string;
	is_active?: boolean;
	user_id?: string;
	base_model_id?: string;
	meta?: {
		profile_image_url?: string;
		description?: string;
	};
	info?: {
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
	// Merge workspace metadata with all models
	const mergedModels = allModels.map(m => {
		const workspaceModel = workspaceModels.find(wm => wm.id === m.id);
		return workspaceModel ? { ...m, ...workspaceModel } : m;
	});

	// Get function IDs and assistant IDs for categorization
	const functionIds = new Set(functions.map(a => a.id));
	const assistantIds = new Set(workspaceModels.filter(m => m.base_model_id).map(m => m.id));
	const agentIds = new Set([...functionIds, ...assistantIds]);

	// Foundational models (base models, not agents/assistants)
	const foundationalModels = mergedModels.filter(m => 
		m.is_active !== false && 
		!agentIds.has(m.id)
	);

	// All agents (includes both assistants and functions/pipelines)
	const allAgents = mergedModels.filter(m => 
		m.is_active !== false && 
		agentIds.has(m.id)
	);

	// Separate into user-created, shared (other users), and system agents (functions/pipelines)
	const myAgents = allAgents.filter(m => m.user_id === currentUserId);
	const systemAgents = allAgents.filter(m => functionIds.has(m.id));
	const sharedAgents = allAgents.filter(m => 
		!functionIds.has(m.id) && // Not a system function
		m.user_id !== currentUserId    // Not created by current user
	);

	return {
		foundationalModels,
		myAgents,
		sharedAgents,
		systemAgents
	};
};
