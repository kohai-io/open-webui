<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import Plus from '$lib/components/icons/Plus.svelte';

	const i18n: Writable<I18n> = getContext('i18n');
</script>

<a
	href="/workspace/models/create"
	class="flex w-full min-w-0 items-center gap-3 rounded-2xl border border-dashed border-gray-200 bg-gray-50/50 p-3 text-left text-gray-700 transition-colors hover:border-gray-300 hover:bg-gray-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-400 focus-visible:ring-offset-2 active:bg-gray-100 dark:border-gray-800 dark:bg-gray-850/50 dark:text-gray-300 dark:hover:border-gray-700 dark:hover:bg-gray-850 dark:focus-visible:ring-gray-500 dark:focus-visible:ring-offset-gray-900 dark:active:bg-gray-850 sm:p-4"
>
	<span class="shrink-0" aria-hidden="true"><Plus className="size-5" strokeWidth="1.5" /></span>
	<span class="min-w-0">
		<span class="block text-sm font-medium text-gray-900 dark:text-gray-100">
			{$i18n.t('Create agent')}
		</span>
		<span class="mt-1 block text-xs leading-4 text-gray-500 dark:text-gray-400">
			Add a new agent
		</span>
	</span>
</a>
