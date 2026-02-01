<script lang="ts">
	export let title: string;
	export let href: string = '';
</script>

<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
	<div class="flex items-center justify-between mb-4">
		<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{title}</h3>
		{#if href}
			<a
				{href}
				class="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1"
			>
				View all
				<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
				</svg>
			</a>
		{/if}
	</div>
	<slot />
</div>
