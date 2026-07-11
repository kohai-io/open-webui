<script lang="ts">
	import { onMount } from 'svelte';
	import { getModelItems } from '$lib/apis/models';
	import { getFunctions } from '$lib/apis/functions';
	import { models, user } from '$lib/stores';
	import {
		classifyWelcomeCatalogue,
		type WelcomeCatalogueItem
	} from '$lib/components/welcome/catalogue';

	let agents: WelcomeCatalogueItem[] = [];
	let baseModels: WelcomeCatalogueItem[] = [];
	let loading = true;
	let unavailable = false;

	const loadWorkspaceModels = async (): Promise<any[]> => {
		const items: any[] = [];
		for (let page = 1; ; page += 1) {
			const response = await getModelItems(localStorage.token, '', '', '', '', '', page);
			const pageItems = response?.items ?? [];
			items.push(...pageItems);
			if (items.length >= (response?.total ?? 0) || pageItems.length === 0) return items;
		}
	};

	onMount(async () => {
		try {
			const [workspaceModels, functions] = await Promise.all([
				loadWorkspaceModels(),
				getFunctions(localStorage.token)
			]);
			const catalogue = classifyWelcomeCatalogue($models, workspaceModels, functions ?? []);
			agents = catalogue.agents;
			baseModels = catalogue.models;
		} catch (error) {
			console.error('Failed to load Welcome catalogue', error);
			unavailable = true;
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head><title>Welcome</title></svelte:head>

<main class="h-full overflow-y-auto bg-white text-gray-950 dark:bg-gray-950 dark:text-gray-50">
	<div class="mx-auto w-full max-w-7xl px-6 py-12 md:px-10 md:py-20">
		<header class="max-w-5xl">
			<p
				class="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-600 dark:text-emerald-400"
			>
				Welcome back
			</p>
			<h1 class="mt-5 text-6xl font-semibold tracking-[-0.07em] md:text-8xl lg:text-9xl">
				{$user?.name ?? 'Open WebUI'}
			</h1>
			<p class="mt-6 max-w-3xl text-lg text-gray-600 dark:text-gray-300 md:text-2xl">
				Choose an authorised agent or model and start a new chat.
			</p>
			<div class="mt-7 flex flex-wrap gap-4 text-sm font-medium">
				<a
					class="rounded-full bg-gray-950 px-5 py-3 text-white dark:bg-white dark:text-gray-950"
					href="/?chat=true">New chat</a
				>
				<a
					class="rounded-full border border-gray-300 px-5 py-3 dark:border-gray-700"
					href="/workspace/models">Manage agents</a
				>
			</div>
		</header>

		{#if loading}
			<p class="mt-20 text-gray-500">Loading your catalogue…</p>
		{:else if unavailable}
			<p class="mt-20 text-red-600 dark:text-red-400">Your catalogue could not be loaded.</p>
		{:else}
			<section class="mt-20" aria-labelledby="welcome-agents-heading">
				<p
					class="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-600 dark:text-emerald-400"
				>
					Agents
				</p>
				<h2
					id="welcome-agents-heading"
					class="mt-3 text-4xl font-semibold tracking-tight md:text-6xl"
				>
					Agents ready to work
				</h2>
				{@render Catalogue(agents, 'No agents are available to this account yet.')}
			</section>

			<section class="mt-20" aria-labelledby="welcome-models-heading">
				<p
					class="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-600 dark:text-emerald-400"
				>
					Models
				</p>
				<h2
					id="welcome-models-heading"
					class="mt-3 text-4xl font-semibold tracking-tight md:text-6xl"
				>
					Models in reach
				</h2>
				{@render Catalogue(baseModels, 'No models are available to this account yet.')}
			</section>
		{/if}
	</div>
</main>

{#snippet Catalogue(items: WelcomeCatalogueItem[], empty: string)}
	{#if items.length === 0}
		<p class="mt-7 text-gray-500 dark:text-gray-400">{empty}</p>
	{:else}
		<div class="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
			{#each items as item (item.id)}
				<article
					class="flex min-h-48 flex-col justify-between rounded-2xl border border-gray-200 bg-gray-50 p-6 dark:border-gray-800 dark:bg-gray-900"
				>
					<div>
						<h3 class="text-xl font-semibold">{item.name}</h3>
						<p class="mt-3 text-sm text-gray-500 dark:text-gray-400">
							{item.tags.length ? item.tags.join(' · ') : item.kind}
						</p>
					</div>
					<a
						class="mt-8 w-fit rounded-full bg-gray-950 px-4 py-2 text-sm font-semibold text-white dark:bg-white dark:text-gray-950"
						href={`/?models=${encodeURIComponent(item.id)}`}>Open chat ↗</a
					>
				</article>
			{/each}
		</div>
	{/if}
{/snippet}
