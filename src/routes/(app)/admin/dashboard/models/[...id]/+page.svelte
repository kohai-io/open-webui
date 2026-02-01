<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { page } from '$app/stores';
	import { toast } from 'svelte-sonner';
	import { getDashboardModelDetail } from '$lib/apis/dashboard';
	import BarChart from '$lib/components/admin/Dashboard/BarChart.svelte';

	const i18n = getContext('i18n');

	let loading = true;
	let data: any = null;

	$: modelId = $page.params.id;

	const formatNumber = (num: number): string => {
		if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
		if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
		return num.toLocaleString();
	};

	const formatDate = (timestamp: number): string => {
		if (!timestamp) return '-';
		return new Date(timestamp * 1000).toLocaleDateString();
	};

	const loadModelDetail = async () => {
		if (!modelId) return;
		loading = true;
		try {
			data = await getDashboardModelDetail(localStorage.token, modelId);
		} catch (err) {
			console.error(err);
			toast.error($i18n.t('Failed to load model details'));
		}
		loading = false;
	};

	onMount(() => {
		loadModelDetail();
	});

	$: if (modelId) {
		loadModelDetail();
	}
</script>

<div class="flex flex-col gap-4 p-4 md:p-6 max-w-7xl mx-auto">
	{#if loading && !data}
		<div class="flex items-center justify-center h-64">
			<svg class="animate-spin h-8 w-8 text-blue-600" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
				<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
			</svg>
		</div>
	{:else if data}
		<!-- Header -->
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<a
					href="/admin/dashboard/models"
					class="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
					</svg>
				</a>
				<div class="flex items-center gap-4">
					{#if data.model.profile_image_url}
						<img src={data.model.profile_image_url} alt={data.model.name} class="w-12 h-12 rounded-full" />
					{:else}
						<div class="w-12 h-12 rounded-full {data.model.is_agent ? 'bg-gradient-to-br from-purple-500 to-pink-600' : 'bg-gradient-to-br from-green-500 to-teal-600'} flex items-center justify-center text-white text-xl font-medium">
							{data.model.is_agent ? '🤖' : '⚡'}
						</div>
					{/if}
					<div>
						<div class="flex items-center gap-2">
							<h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
								{data.model.name}
							</h1>
							<span class="px-2 py-1 text-xs font-medium rounded-full {data.model.is_agent ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400' : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'}">
								{data.model.is_agent ? 'Agent' : 'Model'}
							</span>
							{#if !data.model.is_configured}
								<span class="px-2 py-1 text-xs font-medium rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
									External
								</span>
							{/if}
						</div>
						{#if data.model.description}
							<p class="text-sm text-gray-500 dark:text-gray-400">{data.model.description}</p>
						{:else}
							<p class="text-sm text-gray-500 dark:text-gray-400">{data.model.id}</p>
						{/if}
					</div>
				</div>
			</div>
			<button
				class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
				on:click={loadModelDetail}
				disabled={loading}
			>
				{$i18n.t('Refresh')}
			</button>
		</div>

		<!-- Stats Cards -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="text-2xl font-bold text-gray-800 dark:text-gray-100">{formatNumber(data.stats.messages)}</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Messages')}</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="text-2xl font-bold text-gray-800 dark:text-gray-100">{formatNumber(data.stats.chats)}</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Chats')}</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="text-2xl font-bold text-gray-800 dark:text-gray-100">{formatNumber(data.stats.users)}</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Users')}</div>
			</div>
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
				<div class="text-2xl font-bold text-gray-800 dark:text-gray-100">{formatNumber(data.stats.tokens.total)}</div>
				<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total Tokens')}</div>
			</div>
		</div>

		<!-- Charts Row -->
		<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
			<!-- Activity Chart -->
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">{$i18n.t('Message Activity')}</h3>
				<BarChart
					labels={[$i18n.t('Today'), $i18n.t('Week'), $i18n.t('Month'), $i18n.t('Quarter')]}
					data={[data.activity.today, data.activity.week, data.activity.month, data.activity.quarter]}
					colors={['#3b82f6', '#6366f1', '#8b5cf6', '#a855f7']}
				/>
			</div>

			<!-- Top Users Chart -->
			<div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">{$i18n.t('Top Users')}</h3>
				{#if data.top_users?.length > 0}
					<BarChart
						labels={data.top_users.map((u: any) => u.name)}
						data={data.top_users.map((u: any) => u.messages)}
						colors="#10b981"
						horizontal={true}
					/>
				{:else}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">
						{$i18n.t('No user data')}
					</div>
				{/if}
			</div>
		</div>

		<!-- Token Breakdown -->
		<div class="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
			<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">{$i18n.t('Token Usage')}</h3>
			<div class="grid grid-cols-3 gap-4">
				<div class="text-center">
					<div class="text-xl font-bold text-blue-600">{formatNumber(data.stats.tokens.input)}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Input Tokens')}</div>
				</div>
				<div class="text-center">
					<div class="text-xl font-bold text-green-600">{formatNumber(data.stats.tokens.output)}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Output Tokens')}</div>
				</div>
				<div class="text-center">
					<div class="text-xl font-bold text-purple-600">{formatNumber(data.stats.tokens.total)}</div>
					<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Total Tokens')}</div>
				</div>
			</div>
		</div>

		<!-- Recent Chats -->
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
			<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
				<h3 class="text-lg font-semibold text-gray-800 dark:text-gray-100">{$i18n.t('Recent Chats')}</h3>
			</div>
			{#if data.recent_chats?.length > 0}
				<div class="divide-y divide-gray-200 dark:divide-gray-700">
					{#each data.recent_chats as chat}
						<div class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50">
							<div class="flex items-center justify-between">
								<div>
									<div class="font-medium text-gray-900 dark:text-gray-100">{chat.title}</div>
									<div class="text-sm text-gray-500 dark:text-gray-400">
										{chat.user_name} • {chat.messages} {$i18n.t('messages')} • {formatNumber(chat.tokens)} {$i18n.t('tokens')}
									</div>
								</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">
									{formatDate(chat.updated_at)}
								</div>
							</div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="text-center py-8 text-gray-500 dark:text-gray-400">
					{$i18n.t('No recent chats')}
				</div>
			{/if}
		</div>
	{/if}
</div>
