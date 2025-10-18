<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { createNewFlow } from '$lib/apis/flows';
	import { toast } from 'svelte-sonner';
	import FlowEditor from '$lib/components/flows/FlowEditor.svelte';
	import { currentFlow, flowNodes, flowEdges, clearFlow, saveFlowState } from '$lib/stores/flows';
	import type { Flow } from '$lib/types/flows';

	let flowName = '';
	let flowDescription = '';
	let saving = false;

	onMount(() => {
		// Initialize empty flow
		clearFlow();
		currentFlow.set({
			id: '',
			name: 'Untitled Flow',
			description: '',
			nodes: [],
			edges: [],
			created_at: Date.now(),
			updated_at: Date.now()
		});
	});

	const handleSave = async () => {
		if (!flowName.trim()) {
			toast.error('Please enter a flow name');
			return;
		}

		saving = true;
		try {
			const token = localStorage.getItem('token') || '';
			const flowState = saveFlowState();
			
			if (!flowState) {
				toast.error('No flow data to save');
				return;
			}

			const newFlow: Partial<Flow> = {
				name: flowName,
				description: flowDescription,
				nodes: flowState.nodes,
				edges: flowState.edges
			};

			const created = await createNewFlow(token, newFlow);
			if (created) {
				toast.success('Flow created successfully');
				goto(`/workspace/flows/${created.id}`);
			}
		} catch (error) {
			console.error('Error creating flow:', error);
			toast.error('Failed to create flow');
		} finally {
			saving = false;
		}
	};

	const handleCancel = () => {
		goto('/workspace/flows');
	};
</script>

<div class="flex flex-col h-full">
	<!-- Header -->
	<div class="flex items-center justify-between mb-4 p-4 border-b border-gray-200 dark:border-gray-700">
		<div class="flex-1 max-w-xl">
			<input
				type="text"
				bind:value={flowName}
				placeholder="Enter flow name..."
				class="w-full text-2xl font-semibold bg-transparent border-none focus:outline-none focus:ring-0 p-0"
			/>
			<input
				type="text"
				bind:value={flowDescription}
				placeholder="Add description (optional)..."
				class="w-full text-sm text-gray-500 dark:text-gray-400 bg-transparent border-none focus:outline-none focus:ring-0 p-0 mt-1"
			/>
		</div>
		<div class="flex items-center gap-2">
			<button
				on:click={handleCancel}
				class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
			>
				Cancel
			</button>
			<button
				on:click={handleSave}
				disabled={saving || !flowName.trim()}
				class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{saving ? 'Saving...' : 'Save Flow'}
			</button>
		</div>
	</div>

	<!-- Flow Editor -->
	<div class="flex-1">
		<FlowEditor />
	</div>
</div>
