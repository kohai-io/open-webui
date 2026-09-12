<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import WelcomeLink from '../welcome/WelcomeLink.svelte';
	import { mediaText } from '../media/copy';
	import Photo from '$lib/components/icons/Photo.svelte';
	import NavigationLink from './NavigationLink.svelte';

	export let compact = false;
	export let onNavigate: () => void = () => {};
	const i18n: Writable<I18n> = getContext('i18n');
</script>

<WelcomeLink {compact} {onNavigate} />
<NavigationLink href="/media" label={mediaText($i18n, 'title')} {compact} {onNavigate}>
	<Photo className="size-4" strokeWidth="1.5" />
</NavigationLink>
