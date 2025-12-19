<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { getModels } from '$lib/apis';
	import type { VideoSegment } from '$lib/types/video';

	export let segment: VideoSegment | null = null;
	export let visible: boolean = false;

	const dispatch = createEventDispatcher();

	let models: any[] = [];
	let selectedModel: string = '';
	let prompt: string = '';
	let loading: boolean = false;
	let loadingModels: boolean = false;

	onMount(async () => {
		await loadModels();
	});

	const loadModels = async () => {
		loadingModels = true;
		try {
			const token = localStorage.getItem('token') || '';
			models = await getModels(token);
			if (models.length > 0) {
				selectedModel = models[0].id;
			}
		} catch (error) {
			console.error('Error loading models:', error);
			toast.error('Failed to load models');
		} finally {
			loadingModels = false;
		}
	};

	const handleSubmit = async () => {
		if (!selectedModel || !prompt.trim()) {
			toast.error('Please select a model and enter a prompt');
			return;
		}

		loading = true;
		try {
			dispatch('submit', {
				segmentId: segment?.id,
				modelId: selectedModel,
				prompt: prompt.trim()
			});
			visible = false;
			prompt = '';
		} catch (error) {
			console.error('Error submitting to model:', error);
			toast.error('Failed to submit to model');
		} finally {
			loading = false;
		}
	};

	const handleClose = () => {
		visible = false;
		prompt = '';
	};

	$: segmentDuration = segment ? (segment.endTime - segment.startTime).toFixed(2) : '0.00';
</script>

{#if visible}
	<div class="fixed inset-0 z-[9999] flex items-center justify-center">
		<div class="absolute inset-0 bg-black/60" on:click={handleClose}></div>
		
		<div class="relative bg-gray-900 border border-gray-700 rounded-lg shadow-xl w-full max-w-2xl mx-4 p-6">
			<div class="flex items-center justify-between mb-6">
				<h2 class="text-xl font-semibold text-white">Send Segment to Model</h2>
				<button
					on:click={handleClose}
					class="text-gray-400 hover:text-white transition-colors"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<line x1="18" y1="6" x2="6" y2="18"/>
						<line x1="6" y1="6" x2="18" y2="18"/>
					</svg>
				</button>
			</div>

			{#if segment}
				<div class="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
					<div class="text-sm text-gray-400 mb-2">Segment Info</div>
					<div class="grid grid-cols-2 gap-4 text-sm">
						<div>
							<span class="text-gray-500">Timeline:</span>
							<span class="text-white ml-2">{segment.startTime.toFixed(2)}s - {segment.endTime.toFixed(2)}s</span>
						</div>
						<div>
							<span class="text-gray-500">Duration:</span>
							<span class="text-white ml-2">{segmentDuration}s</span>
						</div>
						<div>
							<span class="text-gray-500">Source:</span>
							<span class="text-white ml-2">{segment.sourceStartTime.toFixed(2)}s - {segment.sourceEndTime.toFixed(2)}s</span>
						</div>
						<div>
							<span class="text-gray-500">Media ID:</span>
							<span class="text-white ml-2 font-mono text-xs">{segment.mediaId.slice(-8)}</span>
						</div>
					</div>
				</div>
			{/if}

			<div class="space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">Select Model</label>
					{#if loadingModels}
						<div class="flex items-center justify-center h-12 bg-gray-800 rounded-lg">
							<div class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
						</div>
					{:else}
						<select
							bind:value={selectedModel}
							class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						>
							{#each models as model}
								<option value={model.id}>{model.name || model.id}</option>
							{/each}
						</select>
					{/if}
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">Prompt</label>
					<textarea
						bind:value={prompt}
						placeholder="Describe what you want the model to do with this segment... (e.g., 'Enhance this video', 'Add slow motion effect', 'Generate music for this clip')"
						rows="6"
						class="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
					></textarea>
				</div>
			</div>

			<div class="flex items-center justify-end gap-3 mt-6">
				<button
					on:click={handleClose}
					class="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
				>
					Cancel
				</button>
				<button
					on:click={handleSubmit}
					disabled={loading || !selectedModel || !prompt.trim()}
					class="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
				>
					{#if loading}
						<div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
						Processing...
					{:else}
						<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
							<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
						</svg>
						Send to Model
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
