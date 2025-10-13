<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { config, settings, user } from '$lib/stores';
	import { fetchAgentsData } from '$lib/services/agents';
	import type { AgentModel } from '$lib/utils/agents';
	import AgentSection from '$lib/components/workspace/AgentSection.svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	
	const i18n: Writable<i18nType> = getContext('i18n');

	let foundationalModels: AgentModel[] = [];
	let myAgents: AgentModel[] = [];
	let sharedAgents: AgentModel[] = [];
	let systemAgents: AgentModel[] = [];
	let loading = true;

	let expandedFoundational = false;
	let expandedMyAgents = true;
	let expandedSharedAgents = false;
	let expandedSystemAgents = true;

	const navigateToChat = (id: string) => {
		goto(`/?models=${encodeURIComponent(id)}`);
	};

	onMount(async () => {
		try {
			const token = localStorage?.token ?? '';
			const connections = $config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null;
			
			const categorized = await fetchAgentsData({
				token,
				connections,
				currentUserId: $user?.id ?? ''
			});

			foundationalModels = categorized.foundationalModels;
			myAgents = categorized.myAgents;
			sharedAgents = categorized.sharedAgents;
			systemAgents = categorized.systemAgents;

			loading = false;
		} catch (error) {
			console.error('Error loading agents:', error);
			loading = false;
		}
	});
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
			<AgentSection
				title={$i18n.t('My Agents')}
				description={$i18n.t('Agents you created')}
				agents={myAgents}
				expanded={expandedMyAgents}
				onToggle={() => expandedMyAgents = !expandedMyAgents}
				onAgentClick={navigateToChat}
				emptyMessage="No agents created yet"
				showCreateButton={true}
			/>

			<!-- System Agents Section -->
			<AgentSection
				title={$i18n.t('System Agents')}
				description={$i18n.t('Functions and pipelines made available by admins')}
				agents={systemAgents}
				expanded={expandedSystemAgents}
				onToggle={() => expandedSystemAgents = !expandedSystemAgents}
				onAgentClick={navigateToChat}
				emptyMessage="No system agents available"
			/>

			<!-- Shared Agents Section -->
			<AgentSection
				title={$i18n.t('Shared Agents')}
				description={$i18n.t('Agents shared by other users')}
				agents={sharedAgents}
				expanded={expandedSharedAgents}
				onToggle={() => expandedSharedAgents = !expandedSharedAgents}
				onAgentClick={navigateToChat}
				emptyMessage="No shared agents available"
			/>

			<!-- Foundational Models Section -->
			<AgentSection
				title={$i18n.t('Foundational models')}
				description={$i18n.t('Models from providers like OpenAI and Google')}
				agents={foundationalModels}
				expanded={expandedFoundational}
				onToggle={() => expandedFoundational = !expandedFoundational}
				onAgentClick={navigateToChat}
				emptyMessage="No foundational models available"
				countLabel="models"
			/>
		</div>
	{/if}
</div>
