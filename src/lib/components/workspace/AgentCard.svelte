<script lang="ts">
	import { getProfileImage, getDescription, type AgentModel } from '$lib/utils/agents';
	import AgentMenu from './Agents/AgentMenu.svelte';
	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	
	export let agent: AgentModel;
	export let onClick: (id: string) => void;
	export let hasWriteAccess: boolean = false;
	export let onEdit: ((agent: AgentModel) => void) | undefined = undefined;
	export let onClone: ((agent: AgentModel) => void) | undefined = undefined;
	export let onExport: ((agent: AgentModel) => void) | undefined = undefined;
	export let onCopyLink: ((agent: AgentModel) => void) | undefined = undefined;
	export let onHide: ((agent: AgentModel) => void) | undefined = undefined;
	export let onDelete: ((agent: AgentModel) => void) | undefined = undefined;
</script>

<div
	class="flex flex-col p-5 bg-white dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-md transition relative group"
>
	<button
		on:click={() => onClick(agent.id)}
		class="text-left w-full h-full absolute inset-0 z-0"
		aria-label="Open {agent.name}"
	></button>
	
	<div class="flex justify-between items-start mb-2 relative z-10">
		<h3 class="text-base font-semibold text-gray-900 dark:text-gray-100 flex-1 pr-2">
			{agent.name}
		</h3>
		{#if onEdit || onClone || onExport || onCopyLink || onHide || onDelete}
			<div class="opacity-0 group-hover:opacity-100 transition-opacity">
				<AgentMenu
					{agent}
					{hasWriteAccess}
					editHandler={() => onEdit?.(agent)}
					cloneHandler={() => onClone?.(agent)}
					exportHandler={() => onExport?.(agent)}
					copyLinkHandler={() => onCopyLink?.(agent)}
					hideHandler={() => onHide?.(agent)}
					deleteHandler={() => onDelete?.(agent)}
					onClose={() => {}}
				>
					<div class="self-center w-fit p-1 text-sm dark:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-xl">
						<EllipsisHorizontal className="size-5" />
					</div>
				</AgentMenu>
			</div>
		{/if}
	</div>
	
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
</div>
