<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getDashboardGroupDetail } from '$lib/apis/dashboard';
	import BarChart from '$lib/components/admin/Dashboard/BarChart.svelte';
	import StatCard from '$lib/components/admin/Dashboard/StatCard.svelte';
	import ChartCard from '$lib/components/admin/Dashboard/ChartCard.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let data: any = null;

	$: groupId = $page.params.id;

	const formatNumber = (num: number): string => {
		if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
		if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
		return num.toLocaleString();
	};

	const formatDate = (timestamp: number): string => {
		if (!timestamp) return 'Never';
		return new Date(timestamp * 1000).toLocaleString();
	};

	const loadGroup = async () => {
		loading = true;
		try {
			data = await getDashboardGroupDetail(localStorage.token, groupId);
			if (data?.error) {
				toast.error(data.error);
				goto('/admin/dashboard/groups');
			}
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to load group details'));
		}
		loading = false;
	};

	onMount(() => {
		loadGroup();
	});
</script>

<div class="flex flex-col gap-4 p-4 md:p-6 max-w-7xl mx-auto">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-4">
			<a
				href="/admin/dashboard/groups"
				class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</a>
			{#if data?.group}
				<div>
					<h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
						{data.group.name}
					</h1>
					{#if data.group.description}
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{data.group.description}
						</p>
					{/if}
				</div>
			{/if}
		</div>
		<button
			class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
			on:click={loadGroup}
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
	{:else if data?.group}
		<!-- Stats Cards -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			<StatCard
				title={$i18n.t('Members')}
				value={formatNumber(data.stats.members)}
				icon="👥"
			/>
			<StatCard
				title={$i18n.t('Total Chats')}
				value={formatNumber(data.stats.chats)}
				icon="💬"
			/>
			<StatCard
				title={$i18n.t('Messages')}
				value={formatNumber(data.stats.messages)}
				icon="📝"
			/>
			{#if data.stats.spend > 0}
				<StatCard
					title={$i18n.t('Total Spend')}
					value={'$' + data.stats.spend.toFixed(2)}
					icon="💰"
				/>
			{:else}
				<StatCard
					title={$i18n.t('Total Tokens')}
					value={formatNumber(data.stats.tokens.total)}
					icon="🔢"
				/>
			{/if}
		</div>

		<!-- Charts Row -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<!-- Top Models -->
			<ChartCard title={$i18n.t('Top Models Used')}>
				{#if data.models?.length > 0}
					<BarChart
						labels={data.models.map((m) => m.name.length > 25 ? m.name.substring(0, 25) + '...' : m.name)}
						data={data.models.map((m) => m.messages)}
						colors="rgba(147, 51, 234, 0.8)"
						height={180}
						horizontal={true}
					/>
				{:else}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">{$i18n.t('No model usage data')}</div>
				{/if}
			</ChartCard>

			<!-- Token Breakdown -->
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">{$i18n.t('Token Usage')}</h3>
				<div class="grid grid-cols-3 gap-4 text-center">
					<div>
						<div class="text-2xl font-bold text-blue-600">{formatNumber(data.stats.tokens.input)}</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Input')}</div>
					</div>
					<div>
						<div class="text-2xl font-bold text-purple-600">{formatNumber(data.stats.tokens.output)}</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Output')}</div>
					</div>
					<div>
						<div class="text-2xl font-bold text-gray-700 dark:text-gray-300">{formatNumber(data.stats.tokens.total)}</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total')}</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Members Table -->
		{#if data.members?.length > 0}
			<div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
				<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
					<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{$i18n.t('Members')} ({data.members.length})</h3>
				</div>
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead class="bg-gray-50 dark:bg-gray-700/50">
							<tr>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									{$i18n.t('User')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									{$i18n.t('Role')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									{$i18n.t('Chats')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									{$i18n.t('Messages')}
								</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									{$i18n.t('Tokens')}
								</th>
								{#if data.stats.spend > 0}
									<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
										{$i18n.t('Spend')}
									</th>
								{/if}
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
									{$i18n.t('Last Active')}
								</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each data.members as member}
								<tr
									class="hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-pointer transition-colors"
									on:click={() => goto(`/admin/dashboard/users/${member.id}`)}
								>
									<td class="px-4 py-3">
										<div class="flex items-center gap-3">
											<div class="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-sm font-medium">
												{member.name?.charAt(0)?.toUpperCase() || '?'}
											</div>
											<div>
												<div class="font-medium text-gray-900 dark:text-gray-100">{member.name}</div>
												<div class="text-xs text-gray-500 dark:text-gray-400">{member.email}</div>
											</div>
										</div>
									</td>
									<td class="px-4 py-3">
										<span class="px-2 py-1 text-xs font-medium rounded-full {member.role === 'admin' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'}">
											{member.role}
										</span>
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{formatNumber(member.chats)}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{formatNumber(member.messages)}
									</td>
									<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
										{formatNumber(member.tokens)}
									</td>
									{#if data.stats.spend > 0}
										<td class="px-4 py-3 text-gray-700 dark:text-gray-300">
											${member.spend?.toFixed(2) || '0.00'}
										</td>
									{/if}
									<td class="px-4 py-3 text-gray-500 dark:text-gray-400 text-sm">
										{formatDate(member.last_active_at)}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{/if}
	{/if}
</div>
