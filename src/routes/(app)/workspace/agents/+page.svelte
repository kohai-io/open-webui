<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { config, settings, user } from '$lib/stores';
	import { fetchAgentsData } from '$lib/services/agents';
	import { 
		deleteModelById,
		updateModelById,
		getModelItems as getWorkspaceModels
	} from '$lib/apis/models';
	import { getGroups } from '$lib/apis/groups';
	import { copyToClipboard } from '$lib/utils';
	import type { AgentModel } from '$lib/utils/agents';
	import AgentSection from '$lib/components/workspace/Agents/AgentSection.svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;
	
	const i18n: Writable<i18nType> = getContext('i18n');

	let group_ids: string[] = [];

	let foundationalModels: AgentModel[] = [];
	let myAgents: AgentModel[] = [];
	let sharedAgents: AgentModel[] = [];
	let systemAgents: AgentModel[] = [];
	let loading = true;

	let expandedFoundational = false;
	let expandedMyAgents = true;
	let expandedSharedAgents = false;
	let expandedSystemAgents = false;

	const navigateToChat = (id: string) => {
		goto(`/?models=${encodeURIComponent(id)}`);
	};

	const checkWriteAccess = (agent: AgentModel): boolean => {
		if (!$user) return false;
		
		// Admin has access to everything
		if ($user.role === 'admin') return true;
		
		// Owner has write access
		const userId = agent.user_id || agent.info?.user_id;
		if (userId === $user.id) return true;
		
		// Check group-based write access
		if (agent.access_control?.write) {
			const writeGroupIds = agent.access_control.write.group_ids || [];
			const writeUserIds = agent.access_control.write.user_ids || [];
			
			if (writeUserIds.includes($user.id)) return true;
			if (writeGroupIds.some((gid: string) => group_ids.includes(gid))) return true;
		}
		
		return false;
	};

	const refreshAgents = async () => {
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
		} catch (error) {
			console.error('Error loading agents:', error);
			throw error;
		}
	};

	const handleEdit = (agent: AgentModel) => {
		goto(`/workspace/models/edit?id=${encodeURIComponent(agent.id)}`);
	};

	const handleClone = async (agent: AgentModel) => {
		sessionStorage.model = JSON.stringify({
			...agent,
			id: `${agent.id}-clone`,
			name: `${agent.name} (Clone)`
		});
		goto('/workspace/models/create');
	};

	const handleExport = async (agent: AgentModel) => {
		let blob = new Blob([JSON.stringify([agent])], {
			type: 'application/json'
		});
		saveAs(blob, `${agent.id}-${Date.now()}.json`);
		toast.success($i18n.t('Exported {{name}}', { name: agent.name }));
	};

	const handleCopyLink = async (agent: AgentModel) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(agent.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	const handleHide = async (agent: AgentModel) => {
		const updatedAgent = {
			...agent,
			meta: {
				...agent.meta,
				hidden: !(agent?.meta?.hidden ?? false)
			}
		};

		const res = await updateModelById(localStorage.token, agent.id, updatedAgent);

		if (res) {
			toast.success(
				$i18n.t(`Model {{name}} is now {{status}}`, {
					name: agent.name,
					status: updatedAgent.meta.hidden ? 'hidden' : 'visible'
				})
			);
			await refreshAgents();
		}
	};

	const handleDelete = async (agent: AgentModel) => {
		if (!confirm($i18n.t('Are you sure you want to delete {{name}}?', { name: agent.name }))) {
			return;
		}

		const res = await deleteModelById(localStorage.token, agent.id).catch((e) => {
			toast.error(`${e}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t(`Deleted {{name}}`, { name: agent.name }));
			await refreshAgents();
		}
	};

	onMount(async () => {
		try {
			const groups = await getGroups(localStorage.token);
			group_ids = groups.map((group: any) => group.id);
			
			await refreshAgents();
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
				{checkWriteAccess}
				onEdit={handleEdit}
				onClone={handleClone}
				onExport={handleExport}
				onCopyLink={handleCopyLink}
				onHide={handleHide}
				onDelete={handleDelete}
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
				{checkWriteAccess}
				onEdit={handleEdit}
				onClone={handleClone}
				onExport={handleExport}
				onCopyLink={handleCopyLink}
				onHide={handleHide}
				onDelete={handleDelete}
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
