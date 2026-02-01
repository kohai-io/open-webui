import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface ScheduledPrompt {
	id: string;
	user_id: string;
	name: string;
	cron_expression: string;
	timezone: string;
	enabled: boolean;
	model_id: string;
	system_prompt: string | null;
	prompt: string;
	chat_id: string | null;
	create_new_chat: boolean;
	last_run_at: number | null;
	next_run_at: number | null;
	last_status: string | null;
	last_error: string | null;
	run_count: number;
	created_at: number;
	updated_at: number;
}

export interface ScheduledPromptForm {
	name: string;
	cron_expression: string;
	timezone?: string;
	enabled?: boolean;
	model_id: string;
	system_prompt?: string | null;
	prompt: string;
	create_new_chat?: boolean;
}

export interface ScheduledPromptUpdateForm {
	name?: string;
	cron_expression?: string;
	timezone?: string;
	enabled?: boolean;
	model_id?: string;
	system_prompt?: string | null;
	prompt?: string;
	create_new_chat?: boolean;
}

export const getScheduledPrompts = async (token: string = ''): Promise<ScheduledPrompt[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/scheduled-prompts/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res as ScheduledPrompt[];
};

export const getScheduledPromptById = async (
	token: string,
	id: string
): Promise<ScheduledPrompt> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/scheduled-prompts/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res as ScheduledPrompt;
};

export const createScheduledPrompt = async (
	token: string,
	form: ScheduledPromptForm
): Promise<ScheduledPrompt> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/scheduled-prompts/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res as ScheduledPrompt;
};

export const updateScheduledPromptById = async (
	token: string,
	id: string,
	form: ScheduledPromptUpdateForm
): Promise<ScheduledPrompt> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/scheduled-prompts/${id}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(form)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res as ScheduledPrompt;
};

export const toggleScheduledPrompt = async (
	token: string,
	id: string
): Promise<ScheduledPrompt> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/scheduled-prompts/${id}/toggle`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res as ScheduledPrompt;
};

export const runScheduledPromptNow = async (
	token: string,
	id: string
): Promise<{ success: boolean; message: string; chat_id?: string }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/scheduled-prompts/${id}/run`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteScheduledPromptById = async (token: string, id: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/scheduled-prompts/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
