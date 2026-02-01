<script lang="ts">
	export let title: string;
</script>

<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
	<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">{title}</h3>
	<slot />
</div>
