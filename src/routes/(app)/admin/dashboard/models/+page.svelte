<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getDashboardModels } from '$lib/apis/dashboard';

	const i18n = getContext('i18n');

	let loading = true;
	let data: any = null;
	let page = 1;
	let limit = 50;
	let sortBy = 'messages';
	let order = 'desc';

	const formatNumber = (num: number): string => {
		if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
		if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
		return num.toLocaleString();
	};

	const loadModels = async () => {
		loading = true;
		try {
			data = await getDashboardModels(localStorage.token, page, limit, sortBy, order);
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to load models'));
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
		loadModels();
	};

	const handlePageChange = (newPage: number) => {
		page = newPage;
		loadModels();
	};

	onMount(() => {
		loadModels();
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
					{$i18n.t('All Models')}
				</h1>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					{#if data}
						{data.total} {$i18n.t('models used')}
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
			on:click={loadModels}
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
		<!-- Models Table -->
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead class="bg-gray-50 dark:bg-gray-700/50">
						<tr>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('name')}>
									{$i18n.t('Model')}
									{#if sortBy === 'name'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								{$i18n.t('Type')}
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
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('chats')}>
									{$i18n.t('Chats')}
									{#if sortBy === 'chats'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('users')}>
									{$i18n.t('Users')}
									{#if sortBy === 'users'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('tokens_in')}>
									{$i18n.t('Tokens In')}
									{#if sortBy === 'tokens_in'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('tokens_out')}>
									{$i18n.t('Tokens Out')}
									{#if sortBy === 'tokens_out'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
							<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
								<button class="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200" on:click={() => handleSort('tokens')}>
									{$i18n.t('Total Tokens')}
									{#if sortBy === 'tokens'}
										<span>{order === 'desc' ? '↓' : '↑'}</span>
									{/if}
								</button>
							</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
						{#each data.models as model}
							<tr
								class="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
								on:click={() => goto(`/admin/dashboard/models/${encodeURIComponent(model.id)}`)}
							>
								<td class="px-4 py-3">
									<div class="flex items-center gap-3">
										<div class="w-8 h-8 rounded-full {model.is_agent ? 'bg-gradient-to-br from-purple-500 to-pink-600' : 'bg-gradient-to-br from-green-500 to-teal-600'} flex items-center justify-center text-white text-sm font-medium">
											{model.is_agent ? '🤖' : '⚡'}
										</div>
										<div>
											<div class="font-medium text-gray-900 dark:text-gray-100">{model.name}</div>
											{#if model.name !== model.id}
												<div class="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs">{model.id}</div>
											{/if}
										</div>
									</div>
								</td>
								<td class="px-4 py-3">
									<span class="px-2 py-1 text-xs font-medium rounded-full {model.is_agent ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'}">
										{model.is_agent ? 'Agent' : 'Model'}
									</span>
									{#if !model.is_configured}
										<span class="ml-1 px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
											External
										</span>
									{/if}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(model.messages)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(model.chats)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(model.users)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(model.tokens_in)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(model.tokens_out)}
								</td>
								<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
									{formatNumber(model.tokens)}
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

		{#if data.models?.length === 0}
			<div class="text-center py-12 text-gray-500 dark:text-gray-400">
				{$i18n.t('No models found')}
			</div>
		{/if}
	{/if}
</div>
