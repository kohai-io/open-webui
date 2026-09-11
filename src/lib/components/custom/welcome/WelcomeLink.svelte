<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { config } from '$lib/stores';
	import Home from '$lib/components/icons/Home.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	export let compact = false;
	export let onNavigate: () => void = () => {};

	const i18n: Writable<i18nType> = getContext('i18n');
</script>

{#if $config?.features?.enable_welcome_page}
	<div class={compact ? '' : 'px-[0.4375rem] text-gray-800 dark:text-gray-200'}>
		<Tooltip content={$i18n.t('Home')} placement={compact ? 'right' : 'top'}>
			<a
				href="/welcome"
				aria-label={$i18n.t('Home')}
				draggable="false"
				class={compact
					? 'cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition'
					: 'flex w-full items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition'}
				on:click={(event) => {
					event.preventDefault();
					event.stopPropagation();
					goto('/welcome');
					onNavigate();
				}}
			>
				<div class={compact ? 'flex items-center justify-center size-9' : 'self-center'}>
					<Home className="size-4.5" />
				</div>
				{#if !compact}
					<span class="text-sm font-primary">{$i18n.t('Home')}</span>
				{/if}
			</a>
		</Tooltip>
	</div>
{/if}
