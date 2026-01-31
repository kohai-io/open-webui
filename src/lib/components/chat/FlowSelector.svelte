<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { onMount, getContext } from 'svelte';
	import { flows } from '$lib/stores';
	import { getAccessibleFlows } from '$lib/apis/flows';
	import { flyAndScale } from '$lib/utils/transitions';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import type { Flow } from '$lib/types/flows';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let selectedFlow: Flow | null = null;
	export let disabled = false;

	let show = false;
	let searchValue = '';
	let loading = false;

	$: filteredFlows = ($flows ?? []).filter((flow) =>
		flow.name.toLowerCase().includes(searchValue.toLowerCase())
	);

	const loadFlows = async () => {
		if ($flows === null) {
			loading = true;
			try {
				const accessibleFlows = await getAccessibleFlows(localStorage.token);
				flows.set(accessibleFlows);
			} catch (error) {
				console.error('Error loading flows:', error);
				flows.set([]);
			} finally {
				loading = false;
			}
		}
	};

	onMount(() => {
		loadFlows();
	});

	const selectFlow = (flow: Flow | null) => {
		selectedFlow = flow;
		show = false;
	};
</script>

<div class="flex items-center gap-1">
	{#if selectedFlow}
		<Tooltip content={$i18n.t('Clear flow selection')}>
			<button
				class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
				on:click={() => selectFlow(null)}
				{disabled}
				aria-label="Clear flow selection"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-4 h-4 text-gray-500"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<line x1="18" y1="6" x2="6" y2="18" />
					<line x1="6" y1="6" x2="18" y2="18" />
				</svg>
			</button>
		</Tooltip>
	{/if}

	<DropdownMenu.Root
		bind:open={show}
		onOpenChange={() => {
			searchValue = '';
			loadFlows();
		}}
	>
		<DropdownMenu.Trigger
			class="flex items-center gap-1.5 px-2 py-1 text-sm rounded-lg transition-colors
				{selectedFlow
					? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
					: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'}
				{disabled ? 'opacity-50 cursor-not-allowed' : ''}"
			{disabled}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-4 h-4"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<circle cx="12" cy="5" r="3" />
				<line x1="12" y1="8" x2="12" y2="16" />
				<circle cx="6" cy="19" r="3" />
				<circle cx="18" cy="19" r="3" />
				<line x1="12" y1="16" x2="6" y2="16" />
				<line x1="12" y1="16" x2="18" y2="16" />
			</svg>
			<span class="max-w-24 truncate">
				{selectedFlow ? selectedFlow.name : $i18n.t('Flow')}
			</span>
			<ChevronDown className="w-3 h-3" />
		</DropdownMenu.Trigger>

		<DropdownMenu.Content
			class="z-50 w-64 max-h-80 overflow-hidden rounded-xl bg-white dark:bg-gray-850 shadow-lg border border-gray-200 dark:border-gray-700"
			transition={flyAndScale}
			side="top"
			sideOffset={4}
		>
			<div class="p-2 border-b border-gray-200 dark:border-gray-700">
				<input
					type="text"
					bind:value={searchValue}
					placeholder={$i18n.t('Search flows...')}
					class="w-full px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-800 rounded-lg outline-none"
				/>
			</div>

			<div class="max-h-56 overflow-y-auto p-1">
				{#if loading}
					<div class="flex items-center justify-center py-4">
						<div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
					</div>
				{:else if filteredFlows.length === 0}
					<div class="px-3 py-4 text-sm text-gray-500 text-center">
						{$i18n.t('No flows available')}
					</div>
				{:else}
					{#if selectedFlow}
						<button
							class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors text-gray-500"
							on:click={() => selectFlow(null)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-4 h-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<line x1="18" y1="6" x2="6" y2="18" />
								<line x1="6" y1="6" x2="18" y2="18" />
							</svg>
							{$i18n.t('No flow (use model directly)')}
						</button>
						<hr class="my-1 border-gray-200 dark:border-gray-700" />
					{/if}

					{#each filteredFlows as flow}
						<button
							class="w-full flex items-center gap-2 px-3 py-2 text-sm text-left rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors
								{selectedFlow?.id === flow.id ? 'bg-blue-50 dark:bg-blue-900/20' : ''}"
							on:click={() => selectFlow(flow)}
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-4 h-4 flex-shrink-0 {selectedFlow?.id === flow.id
									? 'text-blue-600'
									: 'text-gray-400'}"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="2"
							>
								<circle cx="12" cy="5" r="3" />
								<line x1="12" y1="8" x2="12" y2="16" />
								<circle cx="6" cy="19" r="3" />
								<circle cx="18" cy="19" r="3" />
								<line x1="12" y1="16" x2="6" y2="16" />
								<line x1="12" y1="16" x2="18" y2="16" />
							</svg>
							<div class="flex-1 min-w-0">
								<div class="font-medium truncate {selectedFlow?.id === flow.id ? 'text-blue-600' : ''}">
									{flow.name}
								</div>
								{#if flow.description}
									<div class="text-xs text-gray-500 truncate">{flow.description}</div>
								{/if}
							</div>
							{#if selectedFlow?.id === flow.id}
								<svg
									xmlns="http://www.w3.org/2000/svg"
									class="w-4 h-4 text-blue-600"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
								>
									<polyline points="20 6 9 17 4 12" />
								</svg>
							{/if}
						</button>
					{/each}
				{/if}
			</div>

			<div class="p-2 border-t border-gray-200 dark:border-gray-700">
				<a
					href="/workspace/flows"
					class="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-4 h-4"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<circle cx="12" cy="12" r="3" />
						<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
					</svg>
					{$i18n.t('Manage Flows')}
				</a>
			</div>
		</DropdownMenu.Content>
	</DropdownMenu.Root>
</div>
