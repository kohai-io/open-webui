import { WEBUI_API_BASE_URL } from '$lib/constants';

export const getDashboardStats = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/stats`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDashboardUsers = async (
	token: string,
	page: number = 1,
	limit: number = 50,
	sortBy: string = 'chats',
	order: string = 'desc'
) => {
	let error = null;

	const params = new URLSearchParams({
		page: page.toString(),
		limit: limit.toString(),
		sort_by: sortBy,
		order: order
	});

	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/users?${params}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDashboardUserDetail = async (token: string, userId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/users/${userId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDashboardGroups = async (
	token: string,
	page: number = 1,
	limit: number = 50,
	sortBy: string = 'members',
	order: string = 'desc'
) => {
	let error = null;

	const params = new URLSearchParams({
		page: page.toString(),
		limit: limit.toString(),
		sort_by: sortBy,
		order: order
	});

	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/groups?${params}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDashboardGroupDetail = async (token: string, groupId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/groups/${groupId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDashboardModels = async (
	token: string,
	page: number = 1,
	limit: number = 50,
	sortBy: string = 'messages',
	order: string = 'desc'
) => {
	let error = null;

	const params = new URLSearchParams({
		page: page.toString(),
		limit: limit.toString(),
		sort_by: sortBy,
		order: order
	});

	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/models?${params}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getDashboardModelDetail = async (token: string, modelId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/dashboard/models/${encodeURIComponent(modelId)}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
