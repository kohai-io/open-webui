<script lang="ts">
	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentDuplicate from '$lib/components/icons/DocumentDuplicate.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import Link from '$lib/components/icons/Link.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import EyeSlash from '$lib/components/icons/EyeSlash.svelte';

	import { config } from '$lib/stores';
	import type { AgentModel } from '$lib/utils/agents';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let agent: AgentModel;
	export let hasWriteAccess: boolean;

	export let editHandler: Function;
	export let cloneHandler: Function;
	export let exportHandler: Function;
	export let copyLinkHandler: Function;
	export let hideHandler: Function;
	export let deleteHandler: Function;
	export let onClose: Function;

	let show = false;
</script>

<Dropdown
	bind:show
	on:change={(e) => {
		if (e.detail === false) {
			onClose();
		}
	}}
>
	<Tooltip content={$i18n.t('More')}>
		<button
			on:click={(e) => {
				e.stopPropagation();
				show = !show;
			}}
		>
			<slot />
		</button>
	</Tooltip>

	<div slot="content">
		<DropdownMenu.Content
			class="w-full max-w-[170px] rounded-2xl p-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
			sideOffset={-2}
			side="bottom"
			align="start"
			transition={flyAndScale}
		>
			{#if hasWriteAccess}
				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						editHandler();
					}}
				>
					<Pencil />
					<div class="flex items-center">{$i18n.t('Edit')}</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						hideHandler();
					}}
				>
					{#if agent?.meta?.hidden ?? false}
						<EyeSlash />
					{:else}
						<Eye />
					{/if}

					<div class="flex items-center">
						{#if agent?.meta?.hidden ?? false}
							{$i18n.t('Show')}
						{:else}
							{$i18n.t('Hide')}
						{/if}
					</div>
				</DropdownMenu.Item>

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						cloneHandler();
					}}
				>
					<DocumentDuplicate />
					<div class="flex items-center">{$i18n.t('Clone')}</div>
				</DropdownMenu.Item>

				<hr class="border-gray-50 dark:border-gray-800 my-1" />

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						exportHandler();
					}}
				>
					<Download />
					<div class="flex items-center">{$i18n.t('Export')}</div>
				</DropdownMenu.Item>

				<hr class="border-gray-50 dark:border-gray-800 my-1" />

				<DropdownMenu.Item
					class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
					on:click={() => {
						deleteHandler();
					}}
				>
					<GarbageBin />
					<div class="flex items-center">{$i18n.t('Delete')}</div>
				</DropdownMenu.Item>
			{/if}

			<DropdownMenu.Item
				class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
				on:click={() => {
					copyLinkHandler();
				}}
			>
				<Link />
				<div class="flex items-center">{$i18n.t('Copy Link')}</div>
			</DropdownMenu.Item>
		</DropdownMenu.Content>
	</div>
</Dropdown>
