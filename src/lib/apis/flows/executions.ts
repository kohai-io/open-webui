import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface FlowExecutionResult {
	flow_id: string;
	status: 'success' | 'error' | 'aborted';
	inputs?: Record<string, any>;
	outputs?: Record<string, any>;
	node_results?: Record<string, any>;
	errors?: Record<string, string>;
	execution_time: number;
}

export interface FlowExecutionListItem {
	id: string;
	flow_id: string;
	status: string;
	execution_time: number;
	created_at: number;
}

export interface FlowExecutionDetail extends FlowExecutionListItem {
	user_id: string;
	inputs?: Record<string, any>;
	outputs?: Record<string, any>;
	node_results?: Record<string, any>;
	errors?: Record<string, string>;
	meta: Record<string, any>;
}

export interface FlowExecutionStats {
	total_executions: number;
	success_count: number;
	error_count: number;
	aborted_count: number;
	avg_execution_time: number;
	last_execution_at?: number;
}

/**
 * Save a flow execution result
 */
export const saveFlowExecution = async (
	token: string,
	flowId: string,
	execution: FlowExecutionResult
): Promise<FlowExecutionDetail | null> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/flows/${flowId}/executions`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(execution)
		});

		if (!res.ok) {
			const error = await res.json();
			console.error('Failed to save execution:', error);
			return null;
		}

		return await res.json();
	} catch (error) {
		console.error('Error saving flow execution:', error);
		return null;
	}
};

/**
 * Get execution history for a flow (paginated)
 */
export const getFlowExecutions = async (
	token: string,
	flowId: string,
	page: number = 1
): Promise<FlowExecutionListItem[]> => {
	try {
		const res = await fetch(
			`${WEBUI_API_BASE_URL}/flows/${flowId}/executions?page=${page}`,
			{
				method: 'GET',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				}
			}
		);

		if (!res.ok) {
			throw await res.json();
		}

		return await res.json();
	} catch (error) {
		console.error('Error fetching flow executions:', error);
		throw error;
	}
};

/**
 * Get a specific execution by ID
 */
export const getFlowExecutionById = async (
	token: string,
	flowId: string,
	executionId: string
): Promise<FlowExecutionDetail | null> => {
	try {
		const res = await fetch(
			`${WEBUI_API_BASE_URL}/flows/${flowId}/executions/${executionId}`,
			{
				method: 'GET',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				}
			}
		);

		if (!res.ok) {
			throw await res.json();
		}

		return await res.json();
	} catch (error) {
		console.error('Error fetching flow execution:', error);
		return null;
	}
};

/**
 * Get execution statistics for a flow
 */
export const getFlowExecutionStats = async (
	token: string,
	flowId: string
): Promise<FlowExecutionStats | null> => {
	try {
		const res = await fetch(
			`${WEBUI_API_BASE_URL}/flows/${flowId}/executions/stats`,
			{
				method: 'GET',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				}
			}
		);

		if (!res.ok) {
			throw await res.json();
		}

		return await res.json();
	} catch (error) {
		console.error('Error fetching flow execution stats:', error);
		return null;
	}
};

/**
 * Delete a specific execution
 */
export const deleteFlowExecution = async (
	token: string,
	flowId: string,
	executionId: string
): Promise<boolean> => {
	try {
		const res = await fetch(
			`${WEBUI_API_BASE_URL}/flows/${flowId}/executions/${executionId}`,
			{
				method: 'DELETE',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				}
			}
		);

		if (!res.ok) {
			throw await res.json();
		}

		return await res.json();
	} catch (error) {
		console.error('Error deleting flow execution:', error);
		return false;
	}
};

/**
 * Delete all executions for a flow
 */
export const deleteAllFlowExecutions = async (
	token: string,
	flowId: string
): Promise<boolean> => {
	try {
		const res = await fetch(
			`${WEBUI_API_BASE_URL}/flows/${flowId}/executions`,
			{
				method: 'DELETE',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token}`
				}
			}
		);

		if (!res.ok) {
			throw await res.json();
		}

		return await res.json();
	} catch (error) {
		console.error('Error deleting all flow executions:', error);
		return false;
	}
};
