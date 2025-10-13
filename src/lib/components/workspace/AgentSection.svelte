<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import AgentCard from './AgentCard.svelte';
	import type { AgentModel } from '$lib/utils/agents';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let title: string;
	export let description: string;
	export let agents: AgentModel[];
	export let expanded: boolean;
	export let onToggle: () => void;
	export let onAgentClick: (id: string) => void;
	export let emptyMessage: string;
	export let countLabel: string = 'agents';
	export let showCreateButton: boolean = false;
	export let createHref: string = '/workspace/models/create';
	export let createLabel: string = 'Create';
</script>

<section>
	<button
		on:click={onToggle}
		class="flex items-center justify-between w-full mb-4 hover:opacity-80 transition"
	>
		<div class="flex items-center gap-3">
			<svg
				class="w-5 h-5 transition-transform {expanded ? 'rotate-90' : ''}"
				fill="none"
				stroke="currentColor"
				viewBox="0 0 24 24"
			>
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
			<div class="text-left">
				<h2 class="text-xl font-semibold">
					{title}
				</h2>
				<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					{description}
				</p>
			</div>
		</div>
		<div class="flex items-center gap-3">
			<span class="text-sm text-gray-500">
				{agents.length} {$i18n.t(countLabel)}
			</span>
			{#if showCreateButton}
				<a
					href={createHref}
					class="flex items-center gap-2 px-3 py-1.5 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-lg hover:bg-gray-800 dark:hover:bg-gray-100 transition text-sm"
					on:click={(e) => e.stopPropagation()}
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					{$i18n.t(createLabel)}
				</a>
			{/if}
		</div>
	</button>

	{#if expanded}
		<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
			{#each agents as agent}
				<AgentCard {agent} onClick={onAgentClick} />
			{/each}
		</div>

		{#if agents.length === 0}
			<div class="text-center py-8 text-gray-500">
				{$i18n.t(emptyMessage)}
				{#if showCreateButton}
					<a href={createHref} class="block mt-2 text-blue-500 hover:underline">
						{$i18n.t('Create your first agent')}
					</a>
				{/if}
			</div>
		{/if}
	{/if}
</section>
