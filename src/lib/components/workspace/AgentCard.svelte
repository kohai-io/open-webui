<script lang="ts">
	import { getProfileImage, getDescription, type AgentModel } from '$lib/utils/agents';

	export let agent: AgentModel;
	export let onClick: (id: string) => void;
</script>

<button
	on:click={() => onClick(agent.id)}
	class="flex flex-col p-5 bg-white dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-md transition text-left relative group"
>
	<h3 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">
		{agent.name}
	</h3>
	<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 mb-3 flex-1">
		{getDescription(agent)}
	</p>
	<div class="flex justify-end">
		<img
			src={getProfileImage(agent)}
			alt={agent.name}
			class="w-10 h-10 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-700"
		/>
	</div>
</button>
