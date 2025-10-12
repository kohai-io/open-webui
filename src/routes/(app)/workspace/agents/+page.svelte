<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { config, models, settings, user } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { getModels as getWorkspaceModels } from '$lib/apis/models';
	import { getFunctions } from '$lib/apis/functions';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	
	const i18n = getContext('i18n');

	let foundationalModels = [];
	let myAgents = [];
	let sharedAgents = [];
	let systemAgents = [];
	let loading = true;

	let expandedFoundational = false;
	let expandedMyAgents = true;
	let expandedSharedAgents = false;
	let expandedSystemAgents = true;

	onMount(async () => {
		try {
			// Fetch all data in parallel - same approach as admin panel
			const connections = $config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null;
			const [allModelsData, workspaceModelsData, functionsData] = await Promise.all([
				getModels(localStorage.token, connections),
				getWorkspaceModels(localStorage.token),
				getFunctions(localStorage.token)
			]);

			// Merge workspace metadata (including profile images) with all models
			const mergedModels = (allModelsData || []).map(m => {
				const workspaceModel = (workspaceModelsData || []).find(wm => wm.id === m.id);
				return workspaceModel ? { ...m, ...workspaceModel } : m;
			});

			// Get function IDs and assistant IDs for categorization
			const functionIds = new Set((functionsData || []).map(a => a.id));
			const assistantIds = new Set((workspaceModelsData || []).filter(m => m.base_model_id).map(m => m.id));
			const agentIds = new Set([...functionIds, ...assistantIds]);

			// Foundational models (base models, not agents/assistants)
			foundationalModels = mergedModels.filter(m => 
				m.is_active !== false && 
				!agentIds.has(m.id)
			);

			// All agents (includes both assistants and functions/pipelines)
			const allAgents = mergedModels.filter(m => 
				m.is_active !== false && 
				agentIds.has(m.id)
			);

			// Separate into user-created, shared (other users), and system agents (functions/pipelines)
			myAgents = allAgents.filter(m => m.user_id === $user?.id);
			systemAgents = allAgents.filter(m => functionIds.has(m.id));
			sharedAgents = allAgents.filter(m => 
				!functionIds.has(m.id) && // Not a system function
				m.user_id !== $user?.id    // Not created by current user
			);

			loading = false;
		} catch (error) {
			console.error('Error loading models:', error);
			loading = false;
		}
	});

	const navigateToModel = (modelId: string) => {
		// Navigate to chat with this model selected
		window.location.href = `/?models=${encodeURIComponent(modelId)}`;
	};

	const navigateToAgent = (agentId: string) => {
		// Navigate to chat with this agent selected
		window.location.href = `/?models=${encodeURIComponent(agentId)}`;
	};
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="mb-6">
		<div class="text-2xl font-semibold mb-2">
			{$i18n.t('Agents')}
		</div>
		<div class="text-sm text-gray-500 dark:text-gray-400">
			{$i18n.t('Browse your agents, shared agents, system agents, and foundational models')}
		</div>
	</div>

	{#if loading}
		<div class="flex justify-center items-center h-64">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 dark:border-gray-100"></div>
		</div>
	{:else}
		<div class="flex flex-col gap-8 pb-8">
			<!-- My Agents Section -->
			<section>
				<button
					on:click={() => expandedMyAgents = !expandedMyAgents}
					class="flex items-center justify-between w-full mb-4 hover:opacity-80 transition"
				>
					<div class="flex items-center gap-3">
						<svg
							class="w-5 h-5 transition-transform {expandedMyAgents ? 'rotate-90' : ''}"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
						<div class="text-left">
							<h2 class="text-xl font-semibold">
								{$i18n.t('My Agents')}
							</h2>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Agents you created')}
							</p>
						</div>
					</div>
					<div class="flex items-center gap-3">
						<span class="text-sm text-gray-500">
							{myAgents.length} {$i18n.t('agents')}
						</span>
						<a
							href="/workspace/models/create"
							class="flex items-center gap-2 px-3 py-1.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition text-sm"
							on:click={(e) => e.stopPropagation()}
						>
							<Plus />
							{$i18n.t('Create')}
						</a>
					</div>
				</button>

				{#if expandedMyAgents}
					<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
						{#each myAgents as agent}
							<button
								on:click={() => navigateToAgent(agent.id)}
								class="flex flex-col items-center gap-2 p-3 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
							>
								<img
									src={agent?.meta?.profile_image_url ?? agent?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
									alt={agent.name}
									class="w-8 h-8 rounded-full object-cover"
								/>
								<div class="text-center w-full">
									<div class="text-sm font-medium truncate">{agent.name}</div>
								</div>
							</button>
						{/each}
					</div>

					{#if myAgents.length === 0}
						<div class="text-center py-8 text-gray-500">
							{$i18n.t('No agents created yet')}
							<a href="/workspace/models/create" class="block mt-2 text-blue-500 hover:underline">
								{$i18n.t('Create your first agent')}
							</a>
						</div>
					{/if}
				{/if}
			</section>

			<!-- System Agents Section -->
			<section>
				<button
					on:click={() => expandedSystemAgents = !expandedSystemAgents}
					class="flex items-center justify-between w-full mb-4 hover:opacity-80 transition"
				>
					<div class="flex items-center gap-3">
						<svg
							class="w-5 h-5 transition-transform {expandedSystemAgents ? 'rotate-90' : ''}"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
						<div class="text-left">
							<h2 class="text-xl font-semibold">
								{$i18n.t('System Agents')}
							</h2>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Functions and pipelines made available by admins')}
							</p>
						</div>
					</div>
					<span class="text-sm text-gray-500">
						{systemAgents.length} {$i18n.t('agents')}
					</span>
				</button>

				{#if expandedSystemAgents}
					<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
						{#each systemAgents as agent}
							<button
								on:click={() => navigateToAgent(agent.id)}
								class="flex flex-col items-center gap-2 p-3 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
							>
								<img
									src={agent?.meta?.profile_image_url ?? agent?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
									alt={agent.name}
									class="w-8 h-8 rounded-full object-cover"
								/>
								<div class="text-center w-full">
									<div class="text-sm font-medium truncate">{agent.name}</div>
								</div>
							</button>
						{/each}
					</div>

					{#if systemAgents.length === 0}
						<div class="text-center py-8 text-gray-500">
							{$i18n.t('No system agents available')}
						</div>
					{/if}
				{/if}
			</section>

			<!-- Shared Agents Section -->
			<section>
				<button
					on:click={() => expandedSharedAgents = !expandedSharedAgents}
					class="flex items-center justify-between w-full mb-4 hover:opacity-80 transition"
				>
					<div class="flex items-center gap-3">
						<svg
							class="w-5 h-5 transition-transform {expandedSharedAgents ? 'rotate-90' : ''}"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
						<div class="text-left">
							<h2 class="text-xl font-semibold">
								{$i18n.t('Shared Agents')}
							</h2>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Agents shared by other users')}
							</p>
						</div>
					</div>
					<span class="text-sm text-gray-500">
						{sharedAgents.length} {$i18n.t('agents')}
					</span>
				</button>

				{#if expandedSharedAgents}
					<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
						{#each sharedAgents as agent}
							<button
								on:click={() => navigateToAgent(agent.id)}
								class="flex flex-col items-center gap-2 p-3 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
							>
								<img
									src={agent?.meta?.profile_image_url ?? agent?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
									alt={agent.name}
									class="w-8 h-8 rounded-full object-cover"
								/>
								<div class="text-center w-full">
									<div class="text-sm font-medium truncate">{agent.name}</div>
								</div>
							</button>
						{/each}
					</div>

					{#if sharedAgents.length === 0}
						<div class="text-center py-8 text-gray-500">
							{$i18n.t('No shared agents available')}
						</div>
					{/if}
				{/if}
			</section>

			<!-- Foundational Models Section -->
			<section>
				<button
					on:click={() => expandedFoundational = !expandedFoundational}
					class="flex items-center justify-between w-full mb-4 hover:opacity-80 transition"
				>
					<div class="flex items-center gap-3">
						<svg
							class="w-5 h-5 transition-transform {expandedFoundational ? 'rotate-90' : ''}"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
						</svg>
						<div class="text-left">
							<h2 class="text-xl font-semibold">
								{$i18n.t('Foundational models')}
							</h2>
							<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
								{$i18n.t('Models from providers like OpenAI and Google')}
							</p>
						</div>
					</div>
					<span class="text-sm text-gray-500">
						{foundationalModels.length} {$i18n.t('models')}
					</span>
				</button>

				{#if expandedFoundational}
					<div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
						{#each foundationalModels as model}
							<button
								on:click={() => navigateToModel(model.id)}
								class="flex flex-col items-center gap-2 p-3 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
							>
								<img
									src={model?.meta?.profile_image_url ?? model?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
									alt={model.name}
									class="w-8 h-8 rounded-full object-cover"
								/>
								<div class="text-center w-full">
									<div class="text-sm font-medium truncate">{model.name}</div>
								</div>
							</button>
						{/each}
					</div>

					{#if foundationalModels.length === 0}
						<div class="text-center py-8 text-gray-500">
							{$i18n.t('No foundational models available')}
						</div>
					{/if}
				{/if}
			</section>
		</div>
	{/if}
</div>
