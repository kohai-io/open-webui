<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { config, settings, user, showSidebar } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { getModels as getWorkspaceModels } from '$lib/apis/models';
	import { getFunctions } from '$lib/apis/functions';

	const i18n = getContext('i18n');

	let agents = [];
	let loading = false;

	onMount(async () => {
		loading = true;
		try {
			const connections = $config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null;
			const [allModelsData, workspaceModelsData, functionsData] = await Promise.all([
				getModels(localStorage.token, connections),
				getWorkspaceModels(localStorage.token),
				getFunctions(localStorage.token)
			]);

			// Merge workspace metadata
			const mergedModels = (allModelsData || []).map(m => {
				const workspaceModel = (workspaceModelsData || []).find(wm => wm.id === m.id);
				return workspaceModel ? { ...m, ...workspaceModel } : m;
			});

			// Get agent IDs (assistants + functions)
			const functionIds = new Set((functionsData || []).map(a => a.id));
			const assistantIds = new Set((workspaceModelsData || []).filter(m => m.base_model_id).map(m => m.id));
			const agentIds = new Set([...functionIds, ...assistantIds]);

			// Filter agents
			agents = mergedModels.filter(m => 
				m.is_active !== false && 
				agentIds.has(m.id)
			);
		} catch (error) {
			console.error('Error loading agents:', error);
		} finally {
			loading = false;
		}
	});

	const selectAgent = (agentId: string) => {
		goto(`/?models=${encodeURIComponent(agentId)}`);
	};
</script>

<div class="h-screen max-h-[100dvh] w-full max-w-full flex flex-col overflow-y-auto {$showSidebar
	? 'md:max-w-[calc(100%-260px)]'
	: ''}"
>
	<div class="px-6 py-8 md:px-12 lg:px-20">
		<div class="max-w-6xl mx-auto w-full">
			<!-- Greeting -->
			<div class="mb-8 mt-6">
				<h1 style="font-size: clamp(1.5rem, 4.5vw, 5.5rem); line-height: 1.1;" class="font-semibold mb-1 text-gray-900 dark:text-white">
					<span class="text-blue-600 dark:text-blue-400">Hello, {$user?.name || 'there'}.</span>
				</h1>
				<p style="font-size: clamp(1.5rem, 4.5vw, 5.5rem); line-height: 1.1;" class="font-semibold text-gray-600 dark:text-gray-400">how can I help?</p>
			</div>

			<!-- Chat Input -->
			<div class="mb-12 max-w-4xl">
				<form on:submit|preventDefault={(e) => {
					const formData = new FormData(e.target);
					const message = formData.get('message');
					if (message && message.trim()) {
						goto(`/?q=${encodeURIComponent(message.trim())}`);
					}
				}}>
					<div class="relative">
						<input
							type="text"
							name="message"
							placeholder="Ask me anything..."
							class="w-full px-6 py-4 pr-12 text-lg rounded-2xl bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 text-gray-900 dark:text-white placeholder-gray-400"
						/>
						<button
							type="submit"
							class="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
							</svg>
						</button>
					</div>
				</form>
			</div>

			<!-- Agents Section -->
			<div class="w-full">
			<div class="flex items-center justify-between mb-6">
				<h2 class="text-2xl font-semibold text-gray-800 dark:text-gray-200">Agents</h2>
				<a
					href="/workspace/models-catalog"
					class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
				>
					View all
				</a>
			</div>

			{#if loading}
				<div class="flex justify-center py-16">
					<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
				</div>
			{:else if agents.length === 0}
				<div class="text-center py-16">
					<p class="text-gray-500 dark:text-gray-400 mb-4">No agents available yet.</p>
					<a
						href="/workspace/models-catalog"
						class="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
					>
						Browse Models
					</a>
				</div>
			{:else}
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
					{#each agents.slice(0, 8) as agent}
						<button
							on:click={() => selectAgent(agent.id)}
							class="flex flex-col p-5 bg-white dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-md transition text-left relative group"
						>
							<h3 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">
								{agent.name}
							</h3>
							<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 mb-3 flex-1">
								{agent?.meta?.description ?? agent?.info?.meta?.description ?? 'No description available'}
							</p>
							<div class="flex justify-end">
								<img
									src={agent?.meta?.profile_image_url ?? agent?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
									alt={agent.name}
									class="w-10 h-10 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-700"
								/>
							</div>
						</button>
					{/each}

					<!-- Create Agent Card -->
					<a
						href="/workspace/models/create"
						class="flex flex-col items-center justify-center gap-3 p-5 bg-gray-50 dark:bg-gray-800/50 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 transition"
					>
						<div class="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center">
							<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
							</svg>
						</div>
						<div class="text-sm font-medium text-blue-600 dark:text-blue-400">Create Agent</div>
					</a>
				</div>
			{/if}
		</div>

		<!-- Quick Actions (optional) -->
		<div class="mt-16 w-full">
			<h2 class="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">Quick Actions</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<a
					href="/"
					class="flex items-center gap-3 p-4 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				>
					<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
					</svg>
					<div>
						<div class="font-medium text-gray-900 dark:text-gray-100">New Chat</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">Start a conversation</div>
					</div>
				</a>

				<a
					href="/workspace/models-catalog"
					class="flex items-center gap-3 p-4 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				>
					<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
					</svg>
					<div>
						<div class="font-medium text-gray-900 dark:text-gray-100">Browse Models</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">Explore all models</div>
					</div>
				</a>

				<a
					href="/workspace"
					class="flex items-center gap-3 p-4 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				>
					<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
					<div>
						<div class="font-medium text-gray-900 dark:text-gray-100">Workspace</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">Manage your settings</div>
					</div>
				</a>
			</div>
		</div>
		</div>
	</div>
</div>
