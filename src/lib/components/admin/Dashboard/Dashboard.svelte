<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getDashboardStats } from '$lib/apis/dashboard';
	import { user } from '$lib/stores';

	import StatCard from './StatCard.svelte';
	import ChartCard from './ChartCard.svelte';
	import TopList from './TopList.svelte';

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
				<div class="grid grid-cols-3 gap-4 text-center">
					<div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
						<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.users.registrations.today}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Today')}</div>
						{#if stats.users.comparison.registrations.day.delta !== 0}
							<div class="text-xs mt-1 {stats.users.comparison.registrations.day.delta > 0 ? 'text-green-500' : 'text-red-500'}">
								{stats.users.comparison.registrations.day.delta > 0 ? '+' : ''}{stats.users.comparison.registrations.day.delta}
							</div>
						{/if}
					</div>
					<div class="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
						<div class="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.users.registrations.week}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('This Week')}</div>
						{#if stats.users.comparison.registrations.week.delta !== 0}
							<div class="text-xs mt-1 {stats.users.comparison.registrations.week.delta > 0 ? 'text-green-500' : 'text-red-500'}">
								{stats.users.comparison.registrations.week.delta > 0 ? '+' : ''}{stats.users.comparison.registrations.week.delta}
							</div>
						{/if}
					</div>
					<div class="p-3 bg-pink-50 dark:bg-pink-900/20 rounded-lg">
						<div class="text-2xl font-bold text-pink-600 dark:text-pink-400">{stats.users.registrations.month}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('This Month')}</div>
						{#if stats.users.comparison.registrations.month.delta !== 0}
							<div class="text-xs mt-1 {stats.users.comparison.registrations.month.delta > 0 ? 'text-green-500' : 'text-red-500'}">
								{stats.users.comparison.registrations.month.delta > 0 ? '+' : ''}{stats.users.comparison.registrations.month.delta}
							</div>
						{/if}
					</div>
				</div>
			</ChartCard>

			<ChartCard title={$i18n.t('Active Users')}>
				<div class="grid grid-cols-4 gap-3 text-center">
					<div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
						<div class="text-xl font-bold text-blue-600 dark:text-blue-400">{stats.users.active.day}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('24h')}</div>
					</div>
					<div class="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
						<div class="text-xl font-bold text-purple-600 dark:text-purple-400">{stats.users.active.week}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Week')}</div>
					</div>
					<div class="p-3 bg-pink-50 dark:bg-pink-900/20 rounded-lg">
						<div class="text-xl font-bold text-pink-600 dark:text-pink-400">{stats.users.active.month}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Month')}</div>
					</div>
					<div class="p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
						<div class="text-xl font-bold text-green-600 dark:text-green-400">{stats.users.active.all_time}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('All Time')}</div>
					</div>
				</div>
			</ChartCard>
		</div>

		<!-- User Roles & Chat Activity -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<ChartCard title={$i18n.t('User Roles')}>
				<div class="flex items-center justify-around py-4">
					<div class="text-center">
						<div class="w-16 h-16 mx-auto mb-2 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
							<span class="text-xl font-bold text-blue-600 dark:text-blue-400">{stats.users.roles.admin}</span>
						</div>
						<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Admins')}</div>
					</div>
					<div class="text-center">
						<div class="w-16 h-16 mx-auto mb-2 rounded-full bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
							<span class="text-xl font-bold text-purple-600 dark:text-purple-400">{stats.users.roles.user}</span>
						</div>
						<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Users')}</div>
					</div>
					<div class="text-center">
						<div class="w-16 h-16 mx-auto mb-2 rounded-full bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
							<span class="text-xl font-bold text-orange-600 dark:text-orange-400">{stats.users.roles.pending}</span>
						</div>
						<div class="text-sm text-gray-600 dark:text-gray-400">{$i18n.t('Pending')}</div>
					</div>
				</div>
			</ChartCard>

			<ChartCard title={$i18n.t('Chat Activity')}>
				<div class="grid grid-cols-3 gap-4 text-center">
					<div class="p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
						<div class="text-2xl font-bold text-purple-600 dark:text-purple-400">{stats.chats.activity.today}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Today')}</div>
						{#if stats.chats.comparison.day.delta !== 0}
							<div class="text-xs mt-1 {stats.chats.comparison.day.delta > 0 ? 'text-green-500' : 'text-red-500'}">
								{stats.chats.comparison.day.delta > 0 ? '+' : ''}{stats.chats.comparison.day.delta}
							</div>
						{/if}
					</div>
					<div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
						<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{stats.chats.activity.week}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('This Week')}</div>
					</div>
					<div class="p-3 bg-pink-50 dark:bg-pink-900/20 rounded-lg">
						<div class="text-2xl font-bold text-pink-600 dark:text-pink-400">{stats.chats.activity.month}</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('This Month')}</div>
					</div>
				</div>
				<div class="mt-4 flex justify-center gap-6 text-sm text-gray-500 dark:text-gray-400">
					<span>📌 {stats.chats.pinned} {$i18n.t('pinned')}</span>
					<span>📦 {stats.chats.archived} {$i18n.t('archived')}</span>
				</div>
			</ChartCard>
		</div>

		<!-- Top Users & Models -->
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
			<TopList
				title={$i18n.t('Top Users by Chats')}
				items={stats.users.top_by_chats.map(u => ({ name: u.name, value: u.chats, subtitle: `${formatNumber(u.total_tokens)} tokens` }))}
				valueLabel={$i18n.t('chats')}
			/>
			<TopList
				title={$i18n.t('Top Models by Usage')}
				items={stats.models.top_models.map(m => ({ name: m.name, value: m.messages, subtitle: `${formatNumber(m.total_tokens)} tokens` }))}
				valueLabel={$i18n.t('messages')}
			/>
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
				<div class="flex flex-wrap gap-2">
					{#each stats.files.top_types as fileType}
						<div class="px-3 py-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
							<span class="font-medium text-gray-700 dark:text-gray-300">{fileType.type}</span>
							<span class="ml-2 text-sm text-gray-500 dark:text-gray-400">({fileType.count})</span>
						</div>
					{/each}
				</div>
			</ChartCard>
		{/if}

		<!-- Feedback Ratings -->
		{#if stats.feedback.total > 0}
			<ChartCard title={$i18n.t('Feedback Ratings Distribution')}>
				<div class="flex items-end justify-around h-32 px-4">
					{#each Object.entries(stats.feedback.ratings) as [rating, count]}
						{@const maxCount = Math.max(...Object.values(stats.feedback.ratings))}
						{@const height = maxCount > 0 ? (count / maxCount) * 100 : 0}
						<div class="flex flex-col items-center gap-1">
							<div 
								class="w-6 rounded-t transition-all duration-300"
								style="height: {Math.max(height, 4)}%; background-color: {parseInt(rating) <= 3 ? '#ef4444' : parseInt(rating) <= 6 ? '#f59e0b' : '#22c55e'};"
							></div>
							<span class="text-xs text-gray-500 dark:text-gray-400">{rating}</span>
						</div>
					{/each}
				</div>
			</ChartCard>
		{/if}
	{/if}
</div>
