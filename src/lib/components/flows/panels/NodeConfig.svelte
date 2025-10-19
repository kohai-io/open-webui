<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { getModels as getAPIModels } from '$lib/apis';
	import { getFiles } from '$lib/apis/files';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { models as modelsStore } from '$lib/stores';
	import type { FlowNode, FlowEdge, ModelNodeData, InputNodeData, OutputNodeData, KnowledgeNodeData } from '$lib/types/flows';
	
	export let node: FlowNode;
	export let nodes: FlowNode[] = [];
	export let edges: FlowEdge[] = [];
	
	const dispatch = createEventDispatcher();
	
	let models: any[] = [];
	let loadingModels = false;
	let showAdvancedSettings = false;
	let mediaFiles: any[] = [];
	let loadingFiles = false;
	let knowledgeBases: any[] = [];
	let loadingKnowledgeBases = false;
	
	// Local state for editing (cast as any to work with union types in Svelte 4)
	let localData: any = { ...node.data };
	
	// Helper to get nodes connected to current node
	function getConnectedSourceNodes(): Array<{id: string, label: string, type: string}> {
		const sourceEdges = edges.filter(e => e.target === node.id);
		
		return sourceEdges.map(edge => {
			const sourceNode = nodes.find(n => n.id === edge.source);
			return {
				id: sourceNode?.id || edge.source,
				label: sourceNode?.data?.label || sourceNode?.type || 'Unknown',
				type: sourceNode?.type || 'unknown'
			};
		}).filter(n => n.id);
	}
	
	// Get array-capable source nodes (websearch, knowledge, etc.)
	$: arraySourceOptions = getConnectedSourceNodes().filter(n => 
		['websearch', 'knowledge', 'loop', 'input'].includes(n.type)
	);
	
	// Initialize config object for transform nodes if it doesn't exist
	if (node.type === 'transform' && !localData.config) {
		localData.config = {};
	}
	
	onMount(async () => {
		if (node.type === 'model') {
			await loadModels();
		} else if (node.type === 'input') {
			await loadMediaFiles();
		} else if (node.type === 'knowledge') {
			await loadKnowledgeBases();
		}
	});
	
	const loadModels = async () => {
		// First check if models are already in the store
		const storeModels = $modelsStore;
		if (storeModels && storeModels.length > 0) {
			models = storeModels.filter((model: any) => !model.is_hidden);
			return;
		}
		
		// If not, fetch from API
		loadingModels = true;
		try {
			const token = localStorage.getItem('token') || '';
			// Get all models from API
			const data = await getAPIModels(token);
			if (data) {
				// Filter to only show enabled models (not hidden)
				models = data.filter((model: any) => !model.is_hidden);
				
				// Update the global store too
				modelsStore.set(models);
			}
		} catch (error) {
			console.error('Error loading models:', error);
		} finally {
			loadingModels = false;
		}
	};
	
	const loadMediaFiles = async () => {
		loadingFiles = true;
		try {
			const token = localStorage.getItem('token') || '';
			const data = await getFiles(token);
			if (data) {
				// Filter to only media files (images, videos, audio)
				const filtered = data.filter((file: any) => {
					const type = file.meta?.content_type || '';
					return type.startsWith('image/') || type.startsWith('video/') || type.startsWith('audio/');
				});
				// Sort by updated_at or created_at, latest first
				mediaFiles = filtered.sort((a: any, b: any) => {
					const dateA = a.updated_at || a.created_at || 0;
					const dateB = b.updated_at || b.created_at || 0;
					return dateB - dateA;
				});
			}
		} catch (error) {
			console.error('Error loading media files:', error);
		} finally {
			loadingFiles = false;
		}
	};

	const loadKnowledgeBases = async () => {
		loadingKnowledgeBases = true;
		try {
			const token = localStorage.getItem('token') || '';
			const data = await getKnowledgeBases(token);
			if (data) {
				knowledgeBases = data;
			}
		} catch (error) {
			console.error('Error loading knowledge bases:', error);
		} finally {
			loadingKnowledgeBases = false;
		}
	};
	
	const updateData = () => {
		dispatch('update', localData);
	};
	
	const handleDelete = () => {
		dispatch('delete');
	};
	
	const handleClose = () => {
		dispatch('close');
	};
	
	const handleModelChange = (e: Event) => {
		const target = e.target as HTMLSelectElement;
		const selectedModel = models.find((m) => m.id === target.value);
		if (selectedModel) {
			localData = {
				...localData,
				modelId: selectedModel.id,
				modelName: selectedModel.name
			};
			updateData();
		}
	};
	
	$: if (node) {
		localData = { ...node.data };
	}
</script>

<div class="node-config nopan nodrag nowheel bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg h-full flex flex-col" style="pointer-events: auto; z-index: 1000;">
	<!-- Header -->
	<div class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
		<h3 class="font-semibold text-gray-900 dark:text-gray-100">Node Configuration</h3>
		<button
			on:click={handleClose}
			class="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-5 h-5"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<line x1="18" y1="6" x2="6" y2="18" />
				<line x1="6" y1="6" x2="18" y2="18" />
			</svg>
		</button>
	</div>
	
	<!-- Content -->
	<div class="flex-1 overflow-y-auto p-4 space-y-4">
		<!-- Label -->
		<div>
			<label for="node-label" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
				Label
			</label>
			<input
				id="node-label"
				type="text"
				value={localData.label}
				on:input={(e) => {
					const target = e.target;
					if (target instanceof HTMLInputElement) {
						localData.label = target.value;
					}
				}}
				on:blur={updateData}
				class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
			/>
		</div>
		
		<!-- Advanced Settings Toggle -->
		{#if ['loop', 'conditional', 'websearch', 'knowledge'].includes(node.type)}
			<div class="flex items-center justify-between py-2">
				<button
					type="button"
					on:click={() => showAdvancedSettings = !showAdvancedSettings}
					class="text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 flex items-center gap-1"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-3 h-3 transition-transform {showAdvancedSettings ? 'rotate-90' : ''}"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<polyline points="9 18 15 12 9 6" />
					</svg>
					{showAdvancedSettings ? 'Hide' : 'Show'} Advanced Options
				</button>
			</div>
		{/if}
		
		{#if node.type === 'input'}
			<!-- Input Node Config -->
			<div>
				<label for="input-value" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Input Value
				</label>
				<textarea
					id="input-value"
					value={localData.value}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLTextAreaElement) {
							localData.value = target.value;
						}
					}}
					on:blur={updateData}
					placeholder="Enter input text..."
					rows="4"
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>
			</div>
			
			<div>
				<label for="input-placeholder" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Placeholder
				</label>
				<input
					id="input-placeholder"
					type="text"
					value={localData.placeholder}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLInputElement) {
							localData.placeholder = target.value;
						}
					}}
					on:blur={updateData}
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>
			</div>
			
			<div>
				<div class="flex items-center justify-between mb-2">
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
						Media File (Optional)
					</label>
					{#if localData.mediaFileId}
						<button
							type="button"
							on:click={() => {
								localData = {
									...localData,
									mediaFileId: undefined,
									mediaFileName: undefined,
									mediaFileType: undefined
								};
								updateData();
							}}
							class="text-xs text-red-600 dark:text-red-400 hover:underline"
						>
							Clear Selection
						</button>
					{/if}
				</div>
				{#if loadingFiles}
					<div class="text-sm text-gray-500">Loading media files...</div>
				{:else if mediaFiles.length === 0}
					<p class="text-xs text-gray-500 dark:text-gray-400 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
						No media files available. Upload images, videos, or audio files to use them as input.
					</p>
				{:else}
					<div class="nopan nodrag nowheel max-h-64 overflow-y-auto border border-gray-300 dark:border-gray-600 rounded-lg p-2 bg-gray-50 dark:bg-gray-900">
						<div class="grid grid-cols-3 gap-2">
							{#each mediaFiles as file}
								<button
									type="button"
									on:click={() => {
										localData = {
											...localData,
											mediaFileId: file.id,
											mediaFileName: file.filename,
											mediaFileType: file.meta?.content_type || ''
										};
										updateData();
									}}
									class="relative aspect-square rounded-lg overflow-hidden border-2 transition-all {localData.mediaFileId === file.id ? 'border-blue-500 ring-2 ring-blue-300' : 'border-gray-200 dark:border-gray-700 hover:border-blue-300'}"
									title={file.filename}
								>
									{#if file.meta?.content_type?.startsWith('image/')}
										<img 
											src={`/api/v1/files/${file.id}/content`}
											alt={file.filename}
											class="w-full h-full object-cover"
											loading="lazy"
										/>
									{:else if file.meta?.content_type?.startsWith('video/')}
										<div class="w-full h-full bg-gray-900 flex items-center justify-center">
											<span class="text-2xl">🎥</span>
										</div>
									{:else if file.meta?.content_type?.startsWith('audio/')}
										<div class="w-full h-full bg-gray-900 flex items-center justify-center">
											<span class="text-2xl">🎵</span>
										</div>
									{:else}
										<div class="w-full h-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
											<span class="text-2xl">📎</span>
										</div>
									{/if}
									{#if localData.mediaFileId === file.id}
										<div class="absolute top-1 right-1 bg-blue-500 text-white rounded-full p-1">
											<svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
											</svg>
										</div>
									{/if}
								</button>
							{/each}
						</div>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
						Click on a media file to select it as input.
					</p>
				{/if}
			</div>
		{:else if node.type === 'model'}
			<!-- Model Node Config -->
			<div>
				<label for="model-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Model
				</label>
				{#if loadingModels}
					<div class="text-sm text-gray-500">Loading models...</div>
				{:else}
					<select
						id="model-select"
						value={localData.modelId}
						on:change={handleModelChange}
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					>
						<option value="">Select a model</option>
						{#each models as model}
							<option value={model.id}>{model.name}</option>
						{/each}
					</select>
				{/if}
			</div>
			
			<div>
				<label for="model-prompt" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Prompt
				</label>
				<textarea
					id="model-prompt"
					value={localData.prompt}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLTextAreaElement) {
							localData.prompt = target.value;
						}
					}}
					on:blur={updateData}
					placeholder="Enter prompt... Use {'{'}{'{'} input {'}'}{'}'}  to reference previous node output"
					rows="6"
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Use <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">{'{'}{'{'} input {'}'}{'}'}  </code> to reference the previous node's output
				</p>
			</div>
			
			<!-- Advanced Settings Toggle -->
			<div class="flex items-center justify-between">
				<button
					type="button"
					on:click={() => showAdvancedSettings = !showAdvancedSettings}
					class="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
				>
					<span>Advanced Settings</span>
					<svg
						class="w-4 h-4 transform transition-transform {showAdvancedSettings ? 'rotate-180' : ''}"
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
					>
						<path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
					</svg>
				</button>
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={localData.useAdvancedSettings}
						on:change={updateData}
						class="nodrag w-4 h-4 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
					/>
					<span class="text-xs text-gray-600 dark:text-gray-400">Enable</span>
				</label>
			</div>
			
			{#if showAdvancedSettings}
				<div class="space-y-4 pt-2 border-t border-gray-200 dark:border-gray-700">
					<div>
						<label for="model-temp" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							Temperature: {localData.temperature || 0.7}
						</label>
						<input
							id="model-temp"
							type="range"
							min="0"
							max="2"
							step="0.1"
							bind:value={localData.temperature}
							on:change={updateData}
							class="nodrag w-full"
						/>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							Controls randomness (0=focused, 2=creative)
						</p>
					</div>
					
					<div>
						<label for="model-tokens" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							Max Tokens
						</label>
						<input
							id="model-tokens"
							type="number"
							value={localData.max_tokens}
							on:input={(e) => {
								const target = e.target;
								if (target instanceof HTMLInputElement) {
									localData.max_tokens = target.valueAsNumber;
								}
							}}
							on:blur={updateData}
							placeholder="Leave empty for default"
							class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						/>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							Maximum response length
						</p>
					</div>
				</div>
			{/if}
		{:else if node.type === 'knowledge'}
			<!-- Knowledge Node Config -->
			<div>
				<label for="knowledge-base-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Knowledge Base
				</label>
				{#if loadingKnowledgeBases}
					<div class="text-sm text-gray-500">Loading knowledge bases...</div>
				{:else if knowledgeBases.length === 0}
					<p class="text-xs text-gray-500 dark:text-gray-400 p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700">
						No knowledge bases available. Create a knowledge base first to use this node.
					</p>
				{:else}
					<select
						id="knowledge-base-select"
						value={localData.knowledgeBaseId}
						on:change={(e) => {
							const target = e.target;
							if (target instanceof HTMLSelectElement) {
								const selectedKB = knowledgeBases.find(kb => kb.id === target.value);
								localData.knowledgeBaseId = target.value;
								localData.knowledgeBaseName = selectedKB?.name || '';
								updateData();
							}
						}}
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
					>
						<option value="">Select a knowledge base</option>
						{#each knowledgeBases as kb}
							<option value={kb.id}>{kb.name}</option>
						{/each}
					</select>
				{/if}
			</div>
			
			<div>
				<label for="knowledge-query" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Query
				</label>
				<textarea
					id="knowledge-query"
					value={localData.query}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLTextAreaElement) {
							localData.query = target.value;
						}
					}}
					on:blur={updateData}
					placeholder="Enter query... Use {'{'}{'{'} input {'}'}{'}'}  to reference previous node"
					rows="4"
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
				/>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Use <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">{'{'}{'{'} input {'}'}{'}'}  </code> to reference the previous node's output
				</p>
			</div>
			
			<div>
				<label for="knowledge-topk" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Top K Results: {localData.topK || 4}
				</label>
				<input
					id="knowledge-topk"
					type="range"
					min="1"
					max="20"
					value={localData.topK || 4}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLInputElement) {
							localData.topK = parseInt(target.value);
						}
					}}
					on:change={updateData}
					class="nopan nodrag nowheel w-full"
				/>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Number of relevant chunks to retrieve
				</p>
			</div>
			
			<div>
				<label for="knowledge-confidence" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Confidence Threshold: {localData.confidenceThreshold || 0}
				</label>
				<input
					id="knowledge-confidence"
					type="range"
					min="0"
					max="1"
					step="0.05"
					value={localData.confidenceThreshold || 0}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLInputElement) {
							localData.confidenceThreshold = parseFloat(target.value);
						}
					}}
					on:change={updateData}
					class="nopan nodrag nowheel w-full"
				/>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Minimum relevance score (0 = all results)
				</p>
			</div>
			
			<div class="space-y-2">
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={localData.useReranking}
						on:change={updateData}
						class="nodrag w-4 h-4 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
					/>
					<span class="text-sm text-gray-700 dark:text-gray-300">Use Reranking</span>
				</label>
				<p class="text-xs text-gray-500 dark:text-gray-400 ml-6">
					Rerank results for better relevance (slower but more accurate)
				</p>
				
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={localData.hybridSearch}
						on:change={updateData}
						class="nodrag w-4 h-4 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
					/>
					<span class="text-sm text-gray-700 dark:text-gray-300">Hybrid Search</span>
				</label>
				<p class="text-xs text-gray-500 dark:text-gray-400 ml-6">
					Combine semantic and keyword search
				</p>
				
				<label class="flex items-center gap-2 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={localData.includeMetadata}
						on:change={updateData}
						class="nodrag w-4 h-4 text-purple-600 rounded focus:ring-2 focus:ring-purple-500"
					/>
					<span class="text-sm text-gray-700 dark:text-gray-300">Include Metadata</span>
				</label>
				<p class="text-xs text-gray-500 dark:text-gray-400 ml-6">
					Include source file information in results
				</p>
			</div>
		{:else if node.type === 'websearch'}
			<!-- Web Search Node Config -->
			<div>
				<label for="websearch-query" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Search Query
				</label>
				<textarea
					id="websearch-query"
					value={localData.query}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLTextAreaElement) {
							localData.query = target.value;
						}
					}}
					on:blur={updateData}
					placeholder="Enter search query... Use {'{'}{'{'} input {'}'}{'}'}  to reference previous node"
					rows="3"
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
				/>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Use <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">{'{'}{'{'} input {'}'}{'}'}  </code> to reference the previous node's output
				</p>
			</div>
			
			<div>
				<label for="websearch-maxresults" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Max Results: {localData.maxResults || 5}
				</label>
				<input
					id="websearch-maxresults"
					type="range"
					min="1"
					max="20"
					value={localData.maxResults || 5}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLInputElement) {
							localData.maxResults = parseInt(target.value);
						}
					}}
					on:change={updateData}
					class="nopan nodrag nowheel w-full"
				/>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Maximum number of search results to retrieve
				</p>
			</div>
			
			<div class="p-3 bg-cyan-50 dark:bg-cyan-900/20 rounded-lg border border-cyan-200 dark:border-cyan-800">
				<p class="text-xs text-gray-700 dark:text-gray-300 mb-2">
					<strong>Output Structure:</strong> Returns an array of results, each with:
				</p>
				<ul class="text-xs text-gray-600 dark:text-gray-400 list-disc list-inside space-y-1">
					<li><code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">title</code> - Page title</li>
					<li><code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">url</code> - Source URL</li>
					<li><code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">content</code> - Full content</li>
					<li><code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">snippet</code> - Short preview</li>
				</ul>
				<p class="text-xs text-gray-700 dark:text-gray-300 mt-2">
					<strong>Loop over results:</strong> Use <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">{'{'}{'{'} websearch.output.results {'}'}{'}'}</code> in Loop node
				</p>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					💡 You can use node type (e.g., <code>websearch</code>) instead of full ID
				</p>
			</div>
		{:else if node.type === 'transform'}
			<!-- Transform Node Config -->
			<div>
				<label for="transform-operation" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Operation
				</label>
				<select
					id="transform-operation"
					value={localData.operation || ''}
					on:change={(e) => {
						const target = e.target;
						if (target instanceof HTMLSelectElement) {
							localData.operation = target.value;
							updateData();
						}
					}}
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				>
					<option value="">Select operation</option>
					<option value="uppercase">Uppercase</option>
					<option value="lowercase">Lowercase</option>
					<option value="trim">Trim Whitespace</option>
					<option value="replace">Find & Replace</option>
					<option value="extract">Extract JSON Field</option>
					<option value="template">Apply Template</option>
				</select>
			</div>
			
			{#if localData.operation === 'replace'}
				<div>
					<label for="transform-pattern" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Find Pattern (Regex)
					</label>
					<input
						id="transform-pattern"
						type="text"
						value={localData.config?.pattern || ''}
						on:input={(e) => {
							const target = e.target;
							if (target instanceof HTMLInputElement) {
								localData.config = { ...localData.config, pattern: target.value };
							}
						}}
						on:blur={updateData}
						placeholder="e.g., hello"
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>
				<div>
					<label for="transform-replacement" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Replace With
					</label>
					<input
						id="transform-replacement"
						type="text"
						value={localData.config?.replacement || ''}
						on:input={(e) => {
							const target = e.target;
							if (target instanceof HTMLInputElement) {
								localData.config = { ...localData.config, replacement: target.value };
							}
						}}
						on:blur={updateData}
						placeholder="e.g., goodbye"
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>
			{:else if localData.operation === 'extract'}
				<div>
					<label for="transform-field" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						JSON Field Name
					</label>
					<input
						id="transform-field"
						type="text"
						value={localData.config?.field || ''}
						on:input={(e) => {
							const target = e.target;
							if (target instanceof HTMLInputElement) {
								localData.config = { ...localData.config, field: target.value };
							}
						}}
						on:blur={updateData}
						placeholder="e.g., name"
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
				</div>
			{:else if localData.operation === 'template'}
				<div>
					<label for="transform-template" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Template
					</label>
					<textarea
						id="transform-template"
						value={localData.config?.template || ''}
						on:input={(e) => {
							const target = e.target;
							if (target instanceof HTMLTextAreaElement) {
								localData.config = { ...localData.config, template: target.value };
							}
						}}
						on:blur={updateData}
						placeholder="e.g., The result is: {'{'}{'{'} input {'}'}{'}'}"
						rows="3"
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					/>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Use <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">{'{'}{'{'} input {'}'}{'}'}  </code> to reference the input
					</p>
				</div>
			{/if}
		{:else if node.type === 'conditional'}
			<!-- Conditional Node Config -->
			<div>
				<label for="conditional-condition" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Condition Value
				</label>
				<textarea
					id="conditional-condition"
					value={localData.condition}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLTextAreaElement) {
							localData.condition = target.value;
						}
					}}
					on:blur={updateData}
					placeholder="Enter value to test... Use {'{'}{'{'} input {'}'}{'}'}  to reference previous node"
					rows="2"
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
				/>
			</div>
			
			<div>
				<label for="conditional-operator" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Operator
				</label>
				<select
					id="conditional-operator"
					value={localData.operator || 'equals'}
					on:change={(e) => {
						const target = e.target;
						if (target instanceof HTMLSelectElement) {
							localData.operator = target.value;
							updateData();
						}
					}}
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
				>
					<option value="equals">Equals</option>
					<option value="not_equals">Not Equals</option>
					<option value="contains">Contains</option>
					<option value="greater">Greater Than</option>
					<option value="less">Less Than</option>
					<option value="regex">Regex Match</option>
				</select>
			</div>
			
			<div>
				<label for="conditional-compare" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Compare To
				</label>
				<input
					id="conditional-compare"
					type="text"
					value={localData.compareValue}
					on:input={(e) => {
						const target = e.target;
						if (target instanceof HTMLInputElement) {
							localData.compareValue = target.value;
						}
					}}
					on:blur={updateData}
					placeholder="Value to compare against"
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-amber-500 focus:border-transparent"
				/>
			</div>
			
			<div class="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
				<p class="text-xs text-gray-700 dark:text-gray-300">
					<strong>Flow:</strong> Connect the TRUE output (green) for when condition passes, and FALSE output (red) for when it fails.
				</p>
			</div>
		{:else if node.type === 'loop'}
			<!-- Loop Node Config -->
			<div>
				<label for="loop-type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Loop Type
				</label>
				<select
					id="loop-type"
					value={localData.loopType || 'count'}
					on:change={(e) => {
						const target = e.target;
						if (target instanceof HTMLSelectElement) {
							localData.loopType = target.value;
							updateData();
						}
					}}
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
				>
					<option value="count">Count (N times)</option>
					<option value="array">Array (For Each)</option>
					<option value="until">Until (Condition)</option>
				</select>
			</div>
			
			{#if localData.loopType === 'count' || localData.loopType === 'until'}
				<div>
					<label for="loop-max" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Max Iterations: {localData.maxIterations || 5}
					</label>
					<input
						id="loop-max"
						type="range"
						min="1"
						max="100"
						value={localData.maxIterations || 5}
						on:input={(e) => {
							const target = e.target;
							if (target instanceof HTMLInputElement) {
								localData.maxIterations = parseInt(target.value);
							}
						}}
						on:change={updateData}
						class="nopan nodrag nowheel w-full"
					/>
				</div>
			{/if}
			
			{#if localData.loopType === 'array'}
				<div>
					<label for="loop-array-source" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						What to loop over?
					</label>
					
					{#if arraySourceOptions.length > 0}
						<select
							id="loop-array-source"
							value={localData.arrayPath || ''}
							on:change={(e) => {
								const target = e.target;
								if (target instanceof HTMLSelectElement) {
									localData.arrayPath = target.value;
									updateData();
								}
							}}
							class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
						>
							<option value="">Select source...</option>
							{#each arraySourceOptions as source}
								{#if source.type === 'websearch'}
									<option value={`{{${source.type}.output.results}}`}>{source.label} → Results</option>
								{:else if source.type === 'knowledge'}
									<option value={`{{${source.type}.output.chunks}}`}>{source.label} → Chunks</option>
								{:else if source.type === 'input'}
									<option value={`{{${source.type}.output}}`}>{source.label}</option>
								{:else}
									<option value={`{{${source.type}.output}}`}>{source.label}</option>
								{/if}
							{/each}
						</select>
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							✅ Auto-detected from connected nodes
						</p>
					{:else}
						<div class="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
							<p class="text-xs text-gray-700 dark:text-gray-300">
								⚠️ Connect a Web Search or Knowledge node first
							</p>
						</div>
					{/if}
					
					<!-- Advanced: Manual input -->
					{#if showAdvancedSettings}
						<div class="mt-2">
							<label for="loop-array-manual" class="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
								Or enter manually:
							</label>
							<input
								id="loop-array-manual"
								type="text"
								value={localData.arrayPath}
								on:input={(e) => {
									const target = e.target;
									if (target instanceof HTMLInputElement) {
										localData.arrayPath = target.value;
									}
								}}
								on:blur={updateData}
								placeholder="e.g., {'{'}{'{'} websearch.output.results {'}'}{'}'}"
								class="nopan nodrag nowheel w-full px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
							/>
						</div>
					{/if}
				</div>
			{/if}
			
			{#if localData.loopType === 'until'}
				<div>
					<label for="loop-break" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Break Condition
					</label>
					<input
						id="loop-break"
						type="text"
						value={localData.breakCondition}
						on:input={(e) => {
							const target = e.target;
							if (target instanceof HTMLInputElement) {
								localData.breakCondition = target.value;
							}
						}}
						on:blur={updateData}
						placeholder="e.g., done or complete"
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
					/>
				</div>
			{/if}
			
			<div class="p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg border border-indigo-200 dark:border-indigo-800">
				<p class="text-xs text-gray-700 dark:text-gray-300 mb-2">
					<strong>EACH</strong> output fires for every iteration. <strong>DONE</strong> output fires when loop completes.
				</p>
				<p class="text-xs text-gray-600 dark:text-gray-400">
					<strong>Tip:</strong> Loop over web search results using <code class="bg-gray-100 dark:bg-gray-700 px-1 rounded">{'{'}{'{'} websearch.output.results {'}'}{'}'}</code>
				</p>
			</div>
		{:else if node.type === 'merge'}
			<!-- Merge Node Config -->
			<div>
				<label for="merge-strategy" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Merge Strategy
				</label>
				<select
					id="merge-strategy"
					value={localData.strategy || 'concat'}
					on:change={(e) => {
						const target = e.target;
						if (target instanceof HTMLSelectElement) {
							localData.strategy = target.value;
							updateData();
						}
					}}
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
				>
					<option value="concat">Concatenate (join strings)</option>
					<option value="array">Array (combine as list)</option>
					<option value="first">First (take first input)</option>
					<option value="last">Last (take last input)</option>
				</select>
			</div>
			
			{#if localData.strategy === 'concat'}
				<div>
					<label for="merge-separator" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Separator
					</label>
					<input
						id="merge-separator"
						type="text"
						value={localData.separator}
						on:input={(e) => {
							const target = e.target;
							if (target instanceof HTMLInputElement) {
								localData.separator = target.value;
							}
						}}
						on:blur={updateData}
						placeholder="\\n"
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
					/>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						String to insert between merged values (use \\n for newline)
					</p>
				</div>
			{/if}
			
			<div class="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg border border-yellow-200 dark:border-yellow-800">
				<p class="text-xs text-gray-700 dark:text-gray-300">
					<strong>Note:</strong> Connect multiple nodes to the Merge node inputs. All inputs must complete before merge executes.
				</p>
			</div>
		{:else if node.type === 'output'}
			<!-- Output Node Config -->
			<div>
				<label for="output-format" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
					Output Format
				</label>
				<select
					id="output-format"
					value={localData.format || 'text'}
					on:change={(e) => {
						const target = e.target;
						if (target instanceof HTMLSelectElement) {
							localData.format = target.value;
							// Initialize fileType if switching to file format
							if (target.value === 'file' && !localData.fileType) {
								localData.fileType = 'image';
							}
							updateData();
						}
					}}
					class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				>
					<option value="text">Text</option>
					<option value="json">JSON</option>
					<option value="markdown">Markdown</option>
					<option value="file">File (Image/Video/Audio)</option>
				</select>
			</div>
			
			{#if localData.format === 'file'}
				<div>
					<label for="output-file-type" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						File Type
					</label>
					<select
						id="output-file-type"
						value={localData.fileType || 'image'}
						on:change={(e) => {
							const target = e.target;
							if (target instanceof HTMLSelectElement) {
								localData.fileType = target.value;
								updateData();
							}
						}}
						class="nopan nodrag nowheel w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					>
						<option value="image">Image</option>
						<option value="video">Video</option>
						<option value="audio">Audio</option>
					</select>
				</div>
			{/if}
	{/if}
	</div>
	
	<!-- Footer -->
	<div class="p-4 border-t border-gray-200 dark:border-gray-700">
		<button
			on:click={handleDelete}
			class="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
		>
			Delete Node
		</button>
	</div>
</div>
