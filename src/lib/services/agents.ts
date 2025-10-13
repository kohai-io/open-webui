/**
 * Service for fetching and managing agents data
 */

import { getModels } from '$lib/apis';
import { getModels as getWorkspaceModels } from '$lib/apis/models';
import { getFunctions } from '$lib/apis/functions';
import { categorizeAgents, type CategorizedAgents, type AgentModel } from '$lib/utils/agents';

export interface AgentsDataConfig {
	token: string;
	connections?: any;
	currentUserId: string;
}

/**
 * Fetch and categorize all agents and models
 * This consolidates the data fetching logic from the agents page
 */
export const fetchAgentsData = async (config: AgentsDataConfig): Promise<CategorizedAgents> => {
	const { token, connections, currentUserId } = config;

	// Fetch all data in parallel
	const [allModelsData, workspaceModelsData, functionsData] = await Promise.all([
		getModels(token, connections),
		getWorkspaceModels(token),
		getFunctions(token)
	]);

	// Categorize the data
	return categorizeAgents(
		allModelsData || [],
		workspaceModelsData || [],
		functionsData || [],
		currentUserId
	);
};
