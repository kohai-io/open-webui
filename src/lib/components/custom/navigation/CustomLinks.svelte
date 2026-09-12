<script lang="ts">
	import { getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import WelcomeLink from '../welcome/WelcomeLink.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let compact = false;
	export let onNavigate: () => void = () => {};
	const i18n: Writable<I18n> = getContext('i18n');
</script>

<WelcomeLink {compact} {onNavigate} />
<div class={compact ? '' : 'px-[0.4375rem] text-gray-800 dark:text-gray-200'}>
	<Tooltip content={$i18n.t('Media')} placement={compact ? 'right' : 'top'}>
		<a
			href="/media"
			aria-label={$i18n.t('Media')}
			aria-current={$page.url.pathname === '/media' ? 'page' : undefined}
			draggable="false"
			class={compact
				? 'cursor-pointer flex rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition'
				: 'flex w-full items-center space-x-3 rounded-2xl px-2.5 py-2 hover:bg-gray-100 dark:hover:bg-gray-900 transition'}
			on:click={(event) => {
				if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
				event.preventDefault();
				event.stopPropagation();
				goto('/media');
				onNavigate();
			}}
		>
			<div class={compact ? 'flex items-center justify-center size-9' : 'self-center'}>
				<Photo className="size-4.5" />
			</div>
			{#if !compact}<span class="text-sm font-primary">{$i18n.t('Media')}</span>{/if}
		</a>
	</Tooltip>
</div>
