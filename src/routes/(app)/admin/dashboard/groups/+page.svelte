<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getDashboardGroups } from '$lib/apis/dashboard';

	const i18n = getContext('i18n');

	let loading = true;
	let data: any = null;
	let page = 1;
	let limit = 50;
	let sortBy = 'members';
	let order = 'desc';

	const formatNumber = (num: number): string => {
		if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
		if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
		return num.toLocaleString();
	};

	const loadGroups = async () => {
		loading = true;
		try {
			data = await getDashboardGroups(localStorage.token, page, limit, sortBy, order);
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to load groups'));
		}
		loading = false;
	};

	const handleSort = (field: string) => {
		if (sortBy === field) {
			order = order === 'desc' ? 'asc' : 'desc';
		} else {
			sortBy = field;
			order = 'desc';
		}
		loadGroups();
	};

	const handlePageChange = (newPage: number) => {
		page = newPage;
		loadGroups();
	};

	onMount(() => {
		loadGroups();
	});
</script>

<div class="flex flex-col gap-4 p-4 md:p-6 max-w-7xl mx-auto">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-4">
			<a
				href="/admin/dashboard"
				class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</a>
			<div>
				<h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
					{$i18n.t('All Groups')}
				</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{#if data}
						{data.total} {$i18n.t('groups')}
						{#if data.generated_at}
							<span class="ml-2">•</span>
							<span class="ml-2">{$i18n.t('Generated')}: {new Date(data.generated_at).toLocaleString()}</span>
						{/if}
					{/if}
				</p>
			</div>
		</div>
		<button
			class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
			on:click={loadGroups}
			disabled={loading}
		>
			{$i18n.t('Refresh')}
		</button>
	</div>

	{#if loading && !data}
		<div class="flex items-center justify-center h-64">
			<svg class="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
			</svg>
		</div>
	{:else if data}
		<!-- Groups Table -->
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead class="bg-gray-50 dark:bg-gray-700/50">
						<tr>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('name')}>
									{$i18n.t('Group')}
									{#if sortBy === 'name'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('members')}>
									{$i18n.t('Members')}
									{#if sortBy === 'members'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('chats')}>
									{$i18n.t('Chats')}
									{#if sortBy === 'chats'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('messages')}>
									{$i18n.t('Messages')}
									{#if sortBy === 'messages'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('tokens')}>
									{$i18n.t('Tokens')}
									{#if sortBy === 'tokens'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each data.groups as group}
							<tr
								class="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
								on:click={() => goto(`/admin/dashboard/groups/${group.id}`)}
							>
								<td class="px-4 py-3">
									<div>
										<div class="font-medium text-gray-900 dark:text-gray-100">{group.name}</div>
										{#if group.description}
											<div class="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs">{group.description}</div>
										{/if}
									</div>
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(group.members)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(group.chats)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(group.messages)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(group.tokens)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>

			<!-- Pagination -->
			{#if data.pages > 1}
				<div class="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
					<div class="text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('Page')} {data.page} {$i18n.t('of')} {data.pages}
					</div>
					<div class="flex gap-2">
						<button
							class="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
							disabled={page === 1}
							on:click={() => handlePageChange(page - 1)}
						>
							{$i18n.t('Previous')}
						</button>
						<button
							class="px-3 py-1 text-sm rounded border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50"
							disabled={page === data.pages}
							on:click={() => handlePageChange(page + 1)}
						>
							{$i18n.t('Next')}
						</button>
					</div>
				</div>
			{/if}
		</div>

		{#if data.groups?.length === 0}
			<div class="text-center py-12 text-gray-500 dark:text-gray-400">
				{$i18n.t('No groups found')}
			</div>
		{/if}
	{/if}
</div>
