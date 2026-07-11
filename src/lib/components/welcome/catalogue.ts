export type WelcomeCatalogueItem = {
	id: string;
	name: string;
	tags: string[];
	kind: 'agent' | 'model';
};

export const orderWelcomeAgents = <T extends { id: string }>(
	items: T[],
	storedIds: string[]
): T[] => {
	const byId = new Map(items.map((item) => [item.id, item]));
	const ordered = storedIds.flatMap((id) => {
		const item = byId.get(id);
		if (!item) return [];
		byId.delete(id);
		return [item];
	});
	return [...ordered, ...byId.values()];
};

export const buildWelcomeChatQuery = ({
	message,
	webSearchEnabled = false,
	imageGenerationEnabled = false,
	codeInterpreterEnabled = false,
	selectedToolIds = []
}: {
	message: string;
	webSearchEnabled?: boolean;
	imageGenerationEnabled?: boolean;
	codeInterpreterEnabled?: boolean;
	selectedToolIds?: string[];
}): string => {
	const params = new URLSearchParams({ q: message.trim() });
	if (webSearchEnabled) params.set('web-search', 'true');
	if (imageGenerationEnabled) params.set('image-generation', 'true');
	if (codeInterpreterEnabled) params.set('code-interpreter', 'true');
	if (selectedToolIds.length) params.set('tools', selectedToolIds.join(','));
	return params.toString();
};

const tagsFor = (item: any): string[] =>
	(item?.meta?.tags ?? item?.tags ?? []).flatMap((tag: any) =>
		typeof tag === 'string' ? [tag] : typeof tag?.name === 'string' ? [tag.name] : []
	);

export const classifyWelcomeCatalogue = (
	executableModels: any[],
	workspaceModels: any[],
	functions: any[]
): { agents: WelcomeCatalogueItem[]; models: WelcomeCatalogueItem[] } => {
	const workspaceById = new Map(workspaceModels.map((item) => [item.id, item]));
	const agentIds = new Set([
		...workspaceModels
			.filter((item) => item.is_active && item.base_model_id)
			.map((item) => item.id),
		...functions.filter((item) => item.is_active).map((item) => item.id)
	]);
	const catalogue = executableModels.map((model) => {
		const workspace = workspaceById.get(model.id);
		return {
			id: model.id,
			name: workspace?.name ?? model.name ?? model.id,
			tags: tagsFor(workspace ?? model),
			kind: agentIds.has(model.id) ? ('agent' as const) : ('model' as const)
		};
	});

	return {
		agents: catalogue.filter((item) => item.kind === 'agent'),
		models: catalogue.filter((item) => item.kind === 'model')
	};
};
