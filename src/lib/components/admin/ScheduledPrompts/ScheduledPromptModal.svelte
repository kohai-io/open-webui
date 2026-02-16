<script lang="ts">
	import { createEventDispatcher, getContext, onMount, tick } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		createScheduledPrompt,
		updateScheduledPromptById,
		type ScheduledPrompt,
		type ScheduledPromptForm
	} from '$lib/apis/scheduled-prompts';
	import { models } from '$lib/stores';
	import { getModels } from '$lib/apis';

	import Modal from '$lib/components/common/Modal.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;
	export let prompt: ScheduledPrompt | null = null;

	let name = '';
	let cronExpression = '0 9 * * *';
	let timezone = 'UTC';
	let modelId = '';
	let systemPrompt = '';
	let promptText = '';
	let createNewChat = true;
	let enabled = true;
	let functionCallingMode: 'default' | 'native' | 'auto' = 'default';

	let loading = false;
	let initialized = false;

	// Common cron presets
	const cronPresets = [
		{ label: 'Every minute', value: '* * * * *' },
		{ label: 'Every hour', value: '0 * * * *' },
		{ label: 'Daily at 9am', value: '0 9 * * *' },
		{ label: 'Daily at 6pm', value: '0 18 * * *' },
		{ label: 'Weekdays at 9am', value: '0 9 * * 1-5' },
		{ label: 'Weekly (Monday 9am)', value: '0 9 * * 1' },
		{ label: 'Monthly (1st at 9am)', value: '0 9 1 * *' }
	];

	// Common timezones
	const timezones = [
		'UTC',
		'America/New_York',
		'America/Chicago',
		'America/Denver',
		'America/Los_Angeles',
		'Europe/London',
		'Europe/Paris',
		'Europe/Berlin',
		'Asia/Tokyo',
		'Asia/Shanghai',
		'Asia/Singapore',
		'Australia/Sydney'
	];

	const initForm = async () => {
		// Ensure models are loaded
		if ($models.length === 0) {
			models.set(await getModels(localStorage.token));
		}
		await tick();

		if (prompt) {
			// Edit mode
			name = prompt.name;
			cronExpression = prompt.cron_expression;
			timezone = prompt.timezone;
			modelId = prompt.model_id;
			systemPrompt = prompt.system_prompt || '';
			promptText = prompt.prompt;
			createNewChat = prompt.create_new_chat;
			enabled = prompt.enabled;
			functionCallingMode = prompt.function_calling_mode || 'default';
		} else {
			// Create mode - reset form
			name = '';
			cronExpression = '0 9 * * *';
			timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
			modelId = $models.length > 0 ? $models[0].id : '';
			systemPrompt = '';
			promptText = '';
			createNewChat = true;
			enabled = true;
			functionCallingMode = 'default';
		}
		initialized = true;
	};

	$: if (show && !initialized) {
		initForm();
	}

	$: if (!show) {
		initialized = false;
	}

	const handleSubmit = async () => {
		if (!name.trim()) {
			toast.error('Name is required');
			return;
		}
		if (!cronExpression.trim()) {
			toast.error('Schedule is required');
			return;
		}
		if (!modelId) {
			toast.error('Model is required');
			return;
		}
		if (!promptText.trim()) {
			toast.error('Prompt is required');
			return;
		}

		loading = true;

		try {
			const formData: ScheduledPromptForm = {
				name: name.trim(),
				cron_expression: cronExpression.trim(),
				timezone,
				enabled,
				model_id: modelId,
				system_prompt: systemPrompt.trim() || null,
				prompt: promptText.trim(),
				create_new_chat: createNewChat,
				function_calling_mode: functionCallingMode
			};

			if (prompt) {
				// Update existing
				await updateScheduledPromptById(localStorage.token, prompt.id, formData);
				toast.success('Scheduled prompt updated');
			} else {
				// Create new
				await createScheduledPrompt(localStorage.token, formData);
				toast.success('Scheduled prompt created');
			}

			dispatch('close');
		} catch (error) {
			toast.error(`Failed to save: ${error}`);
		}

		loading = false;
	};

	const handleClose = () => {
		dispatch('close');
	};
</script>

<Modal bind:show size="lg" on:close={handleClose}>
	<div class="px-6 py-5">
		<div class="text-lg font-semibold mb-4">
			{prompt ? 'Edit Scheduled Prompt' : 'Create Scheduled Prompt'}
		</div>

		<form on:submit|preventDefault={handleSubmit} class="flex flex-col gap-4">
			<!-- Name -->
			<div>
				<label class="block text-sm font-medium mb-1" for="name">Name</label>
				<input
					id="name"
					type="text"
					bind:value={name}
					placeholder="Daily summary, Weekly report, etc."
					class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm"
				/>
			</div>

			<!-- Function Calling Mode -->
			<div>
				<label class="block text-sm font-medium mb-1" for="function-calling-mode">
					Function Calling Mode
					<Tooltip content="Choose how tools are orchestrated for this prompt">
						<span class="text-gray-400 cursor-help">ⓘ</span>
					</Tooltip>
				</label>
				<select
					id="function-calling-mode"
					bind:value={functionCallingMode}
					class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm"
				>
					<option value="default">Default (server-orchestrated)</option>
					<option value="native">Native (model-driven)</option>
					<option value="auto">Auto (inherit model setting)</option>
				</select>
			</div>

			<!-- Schedule -->
			<div>
				<label class="block text-sm font-medium mb-1" for="cron">
					Schedule (Cron Expression)
					<Tooltip content="Format: minute hour day month weekday">
						<span class="text-gray-400 cursor-help">ⓘ</span>
					</Tooltip>
				</label>
				<div class="flex gap-2">
					<input
						id="cron"
						type="text"
						bind:value={cronExpression}
						placeholder="0 9 * * *"
						class="flex-1 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm font-mono"
					/>
					<select
						class="px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm"
						on:change={(e) => {
							if (e.currentTarget.value) {
								cronExpression = e.currentTarget.value;
								e.currentTarget.value = '';
							}
						}}
					>
						<option value="">Presets...</option>
						{#each cronPresets as preset}
							<option value={preset.value}>{preset.label}</option>
						{/each}
					</select>
				</div>
				<div class="text-xs text-gray-500 mt-1">
					<a href="https://crontab.guru/" target="_blank" rel="noopener" class="underline">
						Cron expression help
					</a>
				</div>
			</div>

			<!-- Timezone -->
			<div>
				<label class="block text-sm font-medium mb-1" for="timezone">Timezone</label>
				<select
					id="timezone"
					bind:value={timezone}
					class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm"
				>
					{#each timezones as tz}
						<option value={tz}>{tz}</option>
					{/each}
				</select>
			</div>

			<!-- Model -->
			<div>
				<label class="block text-sm font-medium mb-1" for="model">Model</label>
				<select
					id="model"
					bind:value={modelId}
					class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm"
				>
					{#each $models as model}
						<option value={model.id}>{model.name || model.id}</option>
					{/each}
				</select>
			</div>

			<!-- System Prompt (optional) -->
			<div>
				<label class="block text-sm font-medium mb-1" for="system">
					System Prompt
					<span class="text-gray-400 font-normal">(optional)</span>
				</label>
				<textarea
					id="system"
					bind:value={systemPrompt}
					placeholder="You are a helpful assistant..."
					rows="2"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm resize-none"
				></textarea>
			</div>

			<!-- Prompt -->
			<div>
				<label class="block text-sm font-medium mb-1" for="prompt">Prompt</label>
				<textarea
					id="prompt"
					bind:value={promptText}
					placeholder="What would you like the AI to do?"
					rows="4"
					class="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-850 text-sm resize-none"
				></textarea>
			</div>

			<!-- Options -->
			<div class="flex items-center gap-6">
				<label class="flex items-center gap-2 cursor-pointer">
					<input type="checkbox" bind:checked={createNewChat} class="rounded" />
					<span class="text-sm">Create new chat each time</span>
				</label>
				<label class="flex items-center gap-2 cursor-pointer">
					<input type="checkbox" bind:checked={enabled} class="rounded" />
					<span class="text-sm">Enabled</span>
				</label>
			</div>

			<!-- Actions -->
			<div class="flex justify-end gap-2 mt-2">
				<button
					type="button"
					class="px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 text-sm transition"
					on:click={handleClose}
				>
					Cancel
				</button>
				<button
					type="submit"
					class="px-4 py-2 rounded-lg bg-black dark:bg-white text-white dark:text-black hover:opacity-90 text-sm transition disabled:opacity-50"
					disabled={loading}
				>
					{loading ? 'Saving...' : prompt ? 'Update' : 'Create'}
				</button>
			</div>
		</form>
	</div>
</Modal>
