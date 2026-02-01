<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import {
		getScheduledPrompts,
		deleteScheduledPromptById,
		toggleScheduledPrompt,
		runScheduledPromptNow,
		type ScheduledPrompt
	} from '$lib/apis/scheduled-prompts';
	import { getModels } from '$lib/apis';
	import { models, user } from '$lib/stores';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Switch from '$lib/components/common/Switch.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Play from '$lib/components/icons/Play.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';

	import ScheduledPromptModal from './ScheduledPromptModal.svelte';

	const i18n = getContext('i18n');

	export let scheduledPrompts: ScheduledPrompt[] = [];

	let query = '';
	let filteredPrompts: ScheduledPrompt[] = [];

	let showDeleteConfirm = false;
	let showModal = false;
	let selectedPrompt: ScheduledPrompt | null = null;
	let deleteId: string | null = null;
	let runningId: string | null = null;

	$: if (scheduledPrompts && query !== undefined) {
		filteredPrompts = scheduledPrompts.filter(
			(p) =>
				query === '' ||
				p.name.toLowerCase().includes(query.toLowerCase()) ||
				p.prompt.toLowerCase().includes(query.toLowerCase())
		);
	}

	const formatDate = (timestamp: number | null) => {
		if (!timestamp) return '-';
		return new Date(timestamp * 1000).toLocaleString();
	};

	const formatCron = (cron: string) => {
		const parts = cron.split(' ');
		if (parts.length !== 5) return cron;

		const [minute, hour, day, month, weekday] = parts;

		if (cron === '* * * * *') return 'Every minute';
		if (minute !== '*' && hour !== '*' && day === '*' && month === '*' && weekday === '*') {
			return `Daily at ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
		}
		if (minute !== '*' && hour !== '*' && weekday !== '*' && day === '*' && month === '*') {
			const days: Record<string, string> = {
				'0': 'Sun',
				'1': 'Mon',
				'2': 'Tue',
				'3': 'Wed',
				'4': 'Thu',
				'5': 'Fri',
				'6': 'Sat',
				'7': 'Sun',
				'1-5': 'Weekdays',
				'0,6': 'Weekends'
			};
			return `${days[weekday] || weekday} at ${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`;
		}

		return cron;
	};

	const handleToggle = async (prompt: ScheduledPrompt) => {
		try {
			const updated = await toggleScheduledPrompt(localStorage.token, prompt.id);
			scheduledPrompts = scheduledPrompts.map((p) => (p.id === updated.id ? updated : p));
			toast.success(updated.enabled ? 'Scheduled prompt enabled' : 'Scheduled prompt disabled');
		} catch (error) {
			toast.error(`Failed to toggle: ${error}`);
		}
	};

	const handleDelete = async () => {
		if (!deleteId) return;
		try {
			await deleteScheduledPromptById(localStorage.token, deleteId);
			scheduledPrompts = scheduledPrompts.filter((p) => p.id !== deleteId);
			toast.success('Scheduled prompt deleted');
		} catch (error) {
			toast.error(`Failed to delete: ${error}`);
		}
		deleteId = null;
		showDeleteConfirm = false;
	};

	const handleRunNow = async (prompt: ScheduledPrompt) => {
		runningId = prompt.id;
		try {
			const result = await runScheduledPromptNow(localStorage.token, prompt.id);
			if (result.success) {
				toast.success('Scheduled prompt executed successfully');
				if (result.chat_id) {
					goto(`/c/${result.chat_id}`);
				}
			}
			// Refresh the list
			scheduledPrompts = await getScheduledPrompts(localStorage.token);
		} catch (error) {
			toast.error(`Execution failed: ${error}`);
		}
		runningId = null;
	};

	const handleEdit = (prompt: ScheduledPrompt) => {
		selectedPrompt = prompt;
		showModal = true;
	};

	const handleCreate = () => {
		selectedPrompt = null;
		showModal = true;
	};

	const handleModalClose = async () => {
		showModal = false;
		selectedPrompt = null;
		// Refresh the list
		scheduledPrompts = await getScheduledPrompts(localStorage.token);
	};

	onMount(async () => {
		if ($models.length === 0) {
			models.set(await getModels(localStorage.token));
		}
	});
</script>

<ConfirmDialog
	bind:show={showDeleteConfirm}
	on:confirm={handleDelete}
	title="Delete Scheduled Prompt"
	message="Are you sure you want to delete this scheduled prompt? This action cannot be undone."
/>

{#if showModal}
	<ScheduledPromptModal
		bind:show={showModal}
		prompt={selectedPrompt}
		on:close={handleModalClose}
	/>
{/if}

<div class="flex flex-col h-full">
	<div class="flex flex-col gap-4 px-4 py-4 md:px-8 md:py-6">
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<div class="text-xl font-semibold">{$i18n.t('Scheduled Prompts')}</div>
			</div>
			<div class="flex items-center gap-2">
				<Tooltip content={$i18n.t('Create Scheduled Prompt')}>
					<button
						class="p-2 rounded-lg bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition"
						on:click={handleCreate}
					>
						<Plus className="size-4" />
					</button>
				</Tooltip>
			</div>
		</div>

		<div class="flex items-center gap-2">
			<div class="flex-1 relative">
				<input
					type="text"
					bind:value={query}
					placeholder={$i18n.t('Search scheduled prompts...')}
					class="w-full pl-10 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm"
				/>
				<Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
			</div>
		</div>
	</div>

	<div class="flex-1 overflow-auto px-4 md:px-8">
		{#if filteredPrompts.length === 0}
			<div class="flex flex-col items-center justify-center h-64 text-gray-500">
				<div class="text-lg font-medium mb-2">No scheduled prompts</div>
				<div class="text-sm">Create your first scheduled prompt to automate tasks</div>
			</div>
		{:else}
			<div class="overflow-x-auto">
				<table class="w-full text-sm">
					<thead class="text-left text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
						<tr>
							<th class="py-3 px-2 font-medium">Enabled</th>
							<th class="py-3 px-2 font-medium">Name</th>
							<th class="py-3 px-2 font-medium">Schedule</th>
							<th class="py-3 px-2 font-medium">Model</th>
							<th class="py-3 px-2 font-medium">Last Run</th>
							<th class="py-3 px-2 font-medium">Next Run</th>
							<th class="py-3 px-2 font-medium">Status</th>
							<th class="py-3 px-2 font-medium">Runs</th>
							<th class="py-3 px-2 font-medium">Actions</th>
						</tr>
					</thead>
					<tbody>
						{#each filteredPrompts as prompt (prompt.id)}
							<tr class="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-850">
								<td class="py-3 px-2">
									<Switch
										bind:state={prompt.enabled}
										on:change={() => handleToggle(prompt)}
									/>
								</td>
								<td class="py-3 px-2">
									<div class="font-medium">{prompt.name}</div>
									<div class="text-xs text-gray-500 truncate max-w-xs" title={prompt.prompt}>
										{prompt.prompt.substring(0, 50)}{prompt.prompt.length > 50 ? '...' : ''}
									</div>
								</td>
								<td class="py-3 px-2">
									<Tooltip content={prompt.cron_expression}>
										<span class="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
											{formatCron(prompt.cron_expression)}
										</span>
									</Tooltip>
								</td>
								<td class="py-3 px-2">
									<span class="text-xs">{prompt.model_id}</span>
								</td>
								<td class="py-3 px-2 text-xs text-gray-500">
									{formatDate(prompt.last_run_at)}
								</td>
								<td class="py-3 px-2 text-xs text-gray-500">
									{formatDate(prompt.next_run_at)}
								</td>
								<td class="py-3 px-2">
									{#if prompt.last_status === 'success'}
										<span class="text-xs bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-2 py-1 rounded">
											Success
										</span>
									{:else if prompt.last_status === 'error'}
										<Tooltip content={prompt.last_error || 'Unknown error'}>
											<span class="text-xs bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 px-2 py-1 rounded cursor-help">
												Error
											</span>
										</Tooltip>
									{:else if prompt.last_status === 'running'}
										<span class="text-xs bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-2 py-1 rounded">
											Running
										</span>
									{:else}
										<span class="text-xs text-gray-400">-</span>
									{/if}
								</td>
								<td class="py-3 px-2 text-center">
									{prompt.run_count}
								</td>
								<td class="py-3 px-2">
									<div class="flex items-center gap-1">
										<Tooltip content={$i18n.t('Run Now')}>
											<button
												class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition disabled:opacity-50"
												on:click={() => handleRunNow(prompt)}
												disabled={runningId === prompt.id}
											>
												{#if runningId === prompt.id}
													<Spinner className="size-4" />
												{:else}
													<Play className="size-4" />
												{/if}
											</button>
										</Tooltip>
										<Tooltip content={$i18n.t('Edit')}>
											<button
												class="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition"
												on:click={() => handleEdit(prompt)}
											>
												<Pencil className="size-4" />
											</button>
										</Tooltip>
										<Tooltip content={$i18n.t('Delete')}>
											<button
												class="p-1.5 rounded hover:bg-red-100 dark:hover:bg-red-900 text-red-500 transition"
												on:click={() => {
													deleteId = prompt.id;
													showDeleteConfirm = true;
												}}
											>
												<GarbageBin className="size-4" />
											</button>
										</Tooltip>
									</div>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	</div>
</div>
