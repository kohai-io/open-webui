<script lang="ts">
	import { getContext } from 'svelte';
	import { config, user, showSearch } from '$lib/stores';
	import Search from '$lib/components/layout/Sidebar/icons/Search.svelte';
	import Notes from '$lib/components/layout/Sidebar/icons/Notes.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import { mediaText } from '../media/copy';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';

	const i18n: Writable<I18n> = getContext('i18n');
	$: notesEnabled =
		($config?.features?.enable_notes ?? false) &&
		($user?.role === 'admin' || ($user?.permissions?.features?.notes ?? true));
	$: actions = [
		{
			id: 'search',
			label: $i18n.t('Search'),
			icon: Search,
			href: undefined,
			description: $i18n.t('searchDescription', {
				ns: 'customWelcome',
				defaultValue: 'Find past chats'
			})
		},
		...(notesEnabled
			? [
					{
						id: 'notes',
						label: $i18n.t('Notes'),
						icon: Notes,
						href: '/notes',
						description: $i18n.t('notesDescription', {
							ns: 'customWelcome',
							defaultValue: 'Capture ideas'
						})
					}
				]
			: []),
		{
			id: 'media',
			label: mediaText($i18n, 'title'),
			icon: Photo,
			href: '/media',
			description: $i18n.t('mediaDescription', {
				ns: 'customWelcome',
				defaultValue: 'Browse your media'
			})
		}
	];
</script>

<section aria-labelledby="welcome-quick-actions-title" class="w-full">
	<h2
		id="welcome-quick-actions-title"
		class="mb-3 text-sm font-medium text-gray-600 dark:text-gray-400"
	>
		{$i18n.t('Quick Actions')}
	</h2>
	<div class="grid gap-2 sm:gap-3 {notesEnabled ? 'grid-cols-3' : 'grid-cols-2'}">
		{#each actions as action (action.id)}
			<svelte:element
				this={action.href ? 'a' : 'button'}
				href={action.href}
				type={action.href ? undefined : 'button'}
				aria-label={action.label}
				aria-describedby={`welcome-quick-${action.id}-description`}
				on:click={() => {
					if (action.id === 'search') showSearch.set(true);
				}}
				class="group flex min-w-0 flex-col items-start gap-3 rounded-2xl border border-gray-200 bg-gray-50/50 p-3 text-left text-gray-700 transition-colors hover:border-gray-300 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 active:bg-gray-100 dark:border-gray-800 dark:bg-gray-850/50 dark:text-gray-300 dark:hover:border-gray-700 dark:hover:bg-gray-850 dark:focus-visible:ring-offset-gray-900 dark:active:bg-gray-850 sm:flex-row sm:items-center sm:p-4"
			>
				<span class="shrink-0" aria-hidden="true">
					<svelte:component this={action.icon} className="size-5" strokeWidth="1.5" />
				</span>
				<span class="min-w-0">
					<span class="block text-sm font-medium text-gray-900 dark:text-gray-100"
						>{action.label}</span
					>
					<span
						id={`welcome-quick-${action.id}-description`}
						class="mt-1 block text-xs leading-4 text-gray-500 dark:text-gray-400"
						>{action.description}</span
					>
				</span>
			</svelte:element>
		{/each}
	</div>
</section>
