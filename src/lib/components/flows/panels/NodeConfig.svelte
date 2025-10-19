<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { getModels as getAPIModels } from '$lib/apis';
	import { getFiles } from '$lib/apis/files';
	import { getKnowledgeBases } from '$lib/apis/knowledge';
	import { models as modelsStore } from '$lib/stores';
	import type { FlowNode, ModelNodeData, InputNodeData, OutputNodeData, KnowledgeNodeData } from '$lib/types/flows';
	
	export let node: FlowNode;
	
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
				<p class="text-xs text-gray-700 dark:text-gray-300">
					<strong>Note:</strong> Web search uses the configured search engine in your Open WebUI settings. Results are stored in a temporary collection and can be queried by downstream nodes.
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
