<script lang="ts">
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let title: string;
	export let items: Array<{ name: string; value: number; subtitle?: string }> = [];
	export let valueLabel: string = '';

	const formatNumber = (num: number): string => {
		if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
		if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
		return num.toLocaleString();
	};
</script>

<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
	<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">{title}</h3>
	
	{#if items.length === 0}
		<p class="text-sm text-gray-500 dark:text-gray-400 text-center py-4">{$i18n.t('No data available')}</p>
	{:else}
		<div class="space-y-3">
			{#each items.slice(0, 10) as item, index}
				{@const maxValue = Math.max(...items.map(i => i.value))}
				{@const percentage = maxValue > 0 ? (item.value / maxValue) * 100 : 0}
				<div class="flex items-center gap-3">
					<span class="w-6 text-sm font-medium text-gray-400 dark:text-gray-500">
						{index + 1}.
					</span>
					<div class="flex-1 min-w-0">
						<div class="flex items-center justify-between mb-1">
							<span class="text-sm font-medium text-gray-700 dark:text-gray-300 truncate" title={item.name}>
								{item.name}
							</span>
							<span class="text-sm text-gray-500 dark:text-gray-400 ml-2 whitespace-nowrap">
								{formatNumber(item.value)} {valueLabel}
							</span>
						</div>
						<div class="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
							<div 
								class="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-300"
								style="width: {percentage}%"
							></div>
						</div>
						{#if item.subtitle}
							<span class="text-xs text-gray-400 dark:text-gray-500">{item.subtitle}</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
