<script lang="ts">
	import { getContext } from 'svelte';
	import { config } from '$lib/stores';
	import Home from '$lib/components/icons/Home.svelte';
	import NavigationLink from '../navigation/NavigationLink.svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	export let compact = false;
	export let onNavigate: () => void = () => {};

	const i18n: Writable<i18nType> = getContext('i18n');
</script>

{#if $config?.features?.enable_welcome_page}
	<NavigationLink href="/welcome" label={$i18n.t('Home')} {compact} {onNavigate}>
		<Home className="size-4" strokeWidth="1.5" />
	</NavigationLink>
{/if}
