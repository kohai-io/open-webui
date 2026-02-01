<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getDashboardStats } from '$lib/apis/dashboard';
	import { user } from '$lib/stores';

	import StatCard from './StatCard.svelte';
	import ChartCard from './ChartCard.svelte';
	import TopList from './TopList.svelte';
	import BarChart from './BarChart.svelte';
	import DoughnutChart from './DoughnutChart.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let stats: any = null;

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

	const loadStats = async () => {
		loading = true;
		try {
			stats = await getDashboardStats(localStorage.token);
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to load dashboard statistics'));
		}
		loading = false;
	};

	onMount(() => {
		loadStats();
	});
</script>

<div class="flex flex-col gap-4 p-4 md:p-6 max-w-7xl mx-auto">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
				{$i18n.t('Admin Dashboard')}
			</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('Platform analytics and statistics')}
			</p>
		</div>
		<button
			class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
			on:click={loadStats}
			disabled={loading}
		>
			{#if loading}
				<svg class="animate-spin h-4 w-4 inline mr-2" viewBox="0 0 24 24">
					<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
					<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
				</svg>
			{/if}
			{$i18n.t('Refresh')}
		</button>
	</div>

	{#if loading && !stats}
		<div class="flex items-center justify-center h-64">
			<svg class="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
			</svg>
		</div>
	{:else if stats}
		<!-- Overview Stats -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			<StatCard
				title={$i18n.t('Total Users')}
				value={formatNumber(stats.users.total)}
				subtitle="{stats.users.active_now} {$i18n.t('online now')}"
				icon="users"
				color="blue"
			/>
			<StatCard
				title={$i18n.t('Total Chats')}
				value={formatNumber(stats.chats.total)}
				subtitle="{stats.chats.activity.today} {$i18n.t('today')}"
				icon="chat"
				color="purple"
			/>
			<StatCard
				title={$i18n.t('Total Tokens')}
				value={formatNumber(stats.tokens.total)}
				subtitle="{formatNumber(stats.tokens.prompt)} {$i18n.t('in')} / {formatNumber(stats.tokens.completion)} {$i18n.t('out')}"
				icon="token"
				color="green"
			/>
			<StatCard
				title={$i18n.t('Files')}
				value={formatNumber(stats.files.total)}
				subtitle={formatBytes(stats.files.size_bytes)}
				icon="file"
				color="orange"
			/>
		</div>

		<!-- User Activity Section -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<ChartCard title={$i18n.t('User Registrations')}>
				<BarChart
					labels={[$i18n.t('Today'), $i18n.t('Week'), $i18n.t('Month'), $i18n.t('Quarter'), $i18n.t('Year')]}
					data={[stats.users.registrations.today, stats.users.registrations.week, stats.users.registrations.month, stats.users.registrations.quarter, stats.users.registrations.year]}
					colors={['rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)', 'rgba(236, 72, 153, 0.8)', 'rgba(34, 197, 94, 0.8)', 'rgba(249, 115, 22, 0.8)']}
					height={160}
				/>
			</ChartCard>

			<ChartCard title={$i18n.t('Active Users')}>
				<BarChart
					labels={[$i18n.t('24h'), $i18n.t('Week'), $i18n.t('Month'), $i18n.t('Quarter'), $i18n.t('All Time')]}
					data={[stats.users.active.day, stats.users.active.week, stats.users.active.month, stats.users.active.quarter, stats.users.active.all_time]}
					colors={['rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)', 'rgba(236, 72, 153, 0.8)', 'rgba(34, 197, 94, 0.8)', 'rgba(99, 102, 241, 0.8)']}
					height={160}
				/>
			</ChartCard>
		</div>

		<!-- User Roles & Chat Activity -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<ChartCard title={$i18n.t('User Roles')}>
				<DoughnutChart
					labels={[$i18n.t('Admins'), $i18n.t('Users'), $i18n.t('Pending')]}
					data={[stats.users.roles.admin, stats.users.roles.user, stats.users.roles.pending]}
					colors={['rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)', 'rgba(249, 115, 22, 0.8)']}
					height={180}
				/>
			</ChartCard>

			<ChartCard title={$i18n.t('Chat Activity')}>
				<BarChart
					labels={[$i18n.t('Today'), $i18n.t('Week'), $i18n.t('Month')]}
					data={[stats.chats.activity.today, stats.chats.activity.week, stats.chats.activity.month]}
					colors={['rgba(147, 51, 234, 0.8)', 'rgba(59, 130, 246, 0.8)', 'rgba(236, 72, 153, 0.8)']}
					height={140}
				/>
				<div class="mt-2 flex justify-center gap-6 text-sm text-gray-500 dark:text-gray-400">
					<span>📌 {stats.chats.pinned} {$i18n.t('pinned')}</span>
					<span>📦 {stats.chats.archived} {$i18n.t('archived')}</span>
				</div>
			</ChartCard>
		</div>

		<!-- Top Users & Models -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<ChartCard title={$i18n.t('Top Users by Chats')}>
				{#if stats.users.top_by_chats && stats.users.top_by_chats.length > 0}
					<BarChart
						labels={stats.users.top_by_chats.map(u => u.name)}
						data={stats.users.top_by_chats.map(u => u.chats)}
						colors="rgba(59, 130, 246, 0.8)"
						height={200}
						horizontal={true}
					/>
				{:else}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">{$i18n.t('No data')}</div>
				{/if}
			</ChartCard>
			<ChartCard title={$i18n.t('Top Models by Usage')}>
				{#if stats.models.top_models && stats.models.top_models.length > 0}
					<BarChart
						labels={stats.models.top_models.map(m => m.name.length > 20 ? m.name.substring(0, 20) + '...' : m.name)}
						data={stats.models.top_models.map(m => m.messages)}
						colors="rgba(147, 51, 234, 0.8)"
						height={200}
						horizontal={true}
					/>
				{:else}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">{$i18n.t('No data')}</div>
				{/if}
			</ChartCard>
		</div>

		<!-- Additional Stats -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			<StatCard
				title={$i18n.t('Knowledge Bases')}
				value={formatNumber(stats.knowledge.total_bases)}
				subtitle="{stats.knowledge.total_documents} {$i18n.t('documents')}"
				icon="book"
				color="indigo"
			/>
			<StatCard
				title={$i18n.t('Groups')}
				value={formatNumber(stats.groups.total)}
				subtitle="{stats.groups.total_members} {$i18n.t('total members')}"
				icon="group"
				color="teal"
			/>
			<StatCard
				title={$i18n.t('Feedback')}
				value={formatNumber(stats.feedback.total)}
				subtitle="{stats.feedback.today} {$i18n.t('today')}"
				icon="star"
				color="yellow"
			/>
			<StatCard
				title={$i18n.t('Models Used')}
				value={formatNumber(stats.models.total_used)}
				subtitle="{stats.models.config?.visible_models || 0} {$i18n.t('visible')}"
				icon="cpu"
				color="cyan"
			/>
		</div>

		<!-- Top Users by Tokens & Top Groups -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<TopList
				title={$i18n.t('Top Users by Tokens')}
				items={stats.users.top_by_tokens.map(u => ({ name: u.name, value: u.total_tokens, subtitle: `${u.chats} chats` }))}
				valueLabel={$i18n.t('tokens')}
			/>
			<TopList
				title={$i18n.t('Top Groups by Members')}
				items={stats.groups.top_groups.map(g => ({ name: g.name, value: g.members }))}
				valueLabel={$i18n.t('members')}
			/>
		</div>

		<!-- Spend Data (if enabled) -->
		{#if stats.spend?.enabled}
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
				<ChartCard title={$i18n.t('Platform Spend (LiteLLM)')}>
					<div class="flex items-center justify-around py-4">
						<div class="text-center">
							<div class="text-3xl font-bold text-green-600 dark:text-green-400">${stats.spend.total.toFixed(2)}</div>
							<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total Spend')}</div>
						</div>
						<div class="text-center">
							<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.spend.users_with_spend}</div>
							<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Users with Spend')}</div>
						</div>
					</div>
				</ChartCard>
				{#if stats.spend.top_users && stats.spend.top_users.length > 0}
					<TopList
						title={$i18n.t('Top Users by Spend')}
						items={stats.spend.top_users.map(u => ({ name: u.name, value: u.spend, subtitle: `${u.chats} chats` }))}
						valueLabel="$"
					/>
				{:else}
					<ChartCard title={$i18n.t('Top Users by Spend')}>
						<div class="text-center py-4 text-gray-500 dark:text-gray-400">
							{$i18n.t('No spend data available. Check LiteLLM connection settings.')}
						</div>
					</ChartCard>
				{/if}
			</div>
		{/if}

		<!-- File Types -->
		{#if stats.files.top_types && stats.files.top_types.length > 0}
			<ChartCard title={$i18n.t('Top File Types')}>
				<BarChart
					labels={stats.files.top_types.map(t => t.type)}
					data={stats.files.top_types.map(t => t.count)}
					colors="rgba(99, 102, 241, 0.8)"
					height={160}
				/>
			</ChartCard>
		{/if}

		<!-- Feedback Ratings -->
		{#if stats.feedback.total > 0}
			<ChartCard title={$i18n.t('Feedback Ratings Distribution')}>
				<BarChart
					labels={Object.keys(stats.feedback.ratings)}
					data={Object.values(stats.feedback.ratings)}
					colors={Object.keys(stats.feedback.ratings).map(r => parseInt(r) <= 3 ? 'rgba(239, 68, 68, 0.8)' : parseInt(r) <= 6 ? 'rgba(245, 158, 11, 0.8)' : 'rgba(34, 197, 94, 0.8)')}
					height={160}
				/>
			</ChartCard>
		{/if}
	{/if}
</div>
