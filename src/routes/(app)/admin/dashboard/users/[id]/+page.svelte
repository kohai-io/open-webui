<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import { getDashboardUserDetail } from '$lib/apis/dashboard';
	import BarChart from '$lib/components/admin/Dashboard/BarChart.svelte';
	import StatCard from '$lib/components/admin/Dashboard/StatCard.svelte';
	import ChartCard from '$lib/components/admin/Dashboard/ChartCard.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let data: any = null;

	$: userId = $page.params.id;

	const formatNumber = (num: number): string => {
		if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
		if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
		return num.toLocaleString();
	};

	const formatBytes = (bytes: number): string => {
		if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(2) + ' GB';
		if (bytes >= 1048576) return (bytes / 1048576).toFixed(2) + ' MB';
		if (bytes >= 1024) return (bytes / 1024).toFixed(2) + ' KB';
		return bytes + ' B';
	};

	const formatDate = (timestamp: number): string => {
		if (!timestamp) return 'Never';
		return new Date(timestamp * 1000).toLocaleString();
	};

	const loadUser = async () => {
		loading = true;
		try {
			data = await getDashboardUserDetail(localStorage.token, userId);
			if (data?.error) {
				toast.error(data.error);
				goto('/admin/dashboard/users');
			}
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to load user details'));
		}
		loading = false;
	};

	onMount(() => {
		loadUser();
	});
</script>

<div class="flex flex-col gap-4 p-4 md:p-6 max-w-7xl mx-auto">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-4">
			<a
				href="/admin/dashboard/users"
				class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			</a>
			{#if data?.user}
				<div class="flex items-center gap-3">
					<div class="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-xl font-medium">
						{data.user.name?.charAt(0)?.toUpperCase() || '?'}
					</div>
					<div>
						<h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
							{data.user.name}
						</h1>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{data.user.email}
							<span class="ml-2 px-2 py-0.5 text-xs font-medium rounded-full {data.user.role === 'admin' ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'}">
								{data.user.role}
							</span>
						</p>
					</div>
				</div>
			{/if}
		</div>
		<button
			class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
			on:click={loadUser}
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
	{:else if data?.user}
		<!-- User Info -->
		<div class="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
			<div>
				<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Created')}:</span>
				<span class="ml-2 text-gray-700 dark:text-gray-300">{formatDate(data.user.created_at)}</span>
			</div>
			<div>
				<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Last Active')}:</span>
				<span class="ml-2 text-gray-700 dark:text-gray-300">{formatDate(data.user.last_active_at)}</span>
			</div>
			{#if data.groups?.length > 0}
				<div>
					<span class="text-gray-500 dark:text-gray-400">{$i18n.t('Groups')}:</span>
					<span class="ml-2 text-gray-700 dark:text-gray-300">
						{#each data.groups as group, i}
							<a href="/admin/dashboard/groups/{group.id}" class="text-blue-600 hover:underline">{group.name}</a>{i < data.groups.length - 1 ? ', ' : ''}
						{/each}
					</span>
				</div>
			{/if}
		</div>

		<!-- Stats Cards -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
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
			<StatCard
				title={$i18n.t('Total Tokens')}
				value={formatNumber(data.stats.tokens.total)}
				icon="🔢"
			/>
			{#if data.stats.spend > 0}
				<StatCard
					title={$i18n.t('Spend')}
					value={'$' + data.stats.spend.toFixed(2)}
					icon="💰"
				/>
			{:else}
				<StatCard
					title={$i18n.t('Files')}
					value={formatNumber(data.stats.files)}
					icon="📁"
				/>
			{/if}
		</div>

		<!-- Charts Row -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<!-- Chat Activity -->
			<ChartCard title={$i18n.t('Chat Activity')}>
				<BarChart
					labels={[$i18n.t('Today'), $i18n.t('Week'), $i18n.t('Month'), $i18n.t('Quarter')]}
					data={[data.activity.today, data.activity.week, data.activity.month, data.activity.quarter]}
					colors={['rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)', 'rgba(236, 72, 153, 0.8)', 'rgba(34, 197, 94, 0.8)']}
					height={180}
				/>
			</ChartCard>

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
		</div>

		<!-- Token Breakdown -->
		<div class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">{$i18n.t('Token Usage')}</h3>
			<div class="grid grid-cols-3 gap-4 text-center">
				<div>
					<div class="text-2xl font-bold text-blue-600">{formatNumber(data.stats.tokens.input)}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Input Tokens')}</div>
				</div>
				<div>
					<div class="text-2xl font-bold text-purple-600">{formatNumber(data.stats.tokens.output)}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Output Tokens')}</div>
				</div>
				<div>
					<div class="text-2xl font-bold text-gray-700 dark:text-gray-300">{formatNumber(data.stats.tokens.total)}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total')}</div>
				</div>
			</div>
		</div>

		<!-- Recent Chats -->
		{#if data.recent_chats?.length > 0}
			<div class="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
				<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
					<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{$i18n.t('Recent Chats')}</h3>
				</div>
				<div class="divide-y divide-gray-200 dark:divide-gray-700">
					{#each data.recent_chats as chat}
						<div class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-3">
									{#if chat.pinned}
										<span title="Pinned">📌</span>
									{/if}
									{#if chat.archived}
										<span title="Archived">📦</span>
									{/if}
									<span class="font-medium text-gray-800 dark:text-gray-200">{chat.title}</span>
								</div>
								<div class="flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
									<span>{chat.messages} msgs</span>
									<span>{formatNumber(chat.tokens)} tokens</span>
									<span>{formatDate(chat.updated_at)}</span>
								</div>
							</div>
							{#if chat.models?.length > 0}
								<div class="mt-1 flex gap-1">
									{#each chat.models as model}
										<span class="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-400">
											{model.length > 20 ? model.substring(0, 20) + '...' : model}
										</span>
									{/each}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>
