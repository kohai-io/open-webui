import type { FlowNode, FlowEdge, FlowExecutionContext, FlowExecutionResult } from '$lib/types/flows';
import { chatCompletion } from '$lib/apis/openai';
import { uploadFile } from '$lib/apis/files';
import { queryDoc, processWebSearch, queryCollection } from '$lib/apis/retrieval';
import { getKnowledgeById } from '$lib/apis/knowledge';
import { WEBUI_BASE_URL } from '$lib/constants';

export class FlowExecutor {
	private nodes: Map<string, FlowNode>;
	private edges: FlowEdge[];
	private nodeResults: Map<string, any>;
	private errors: Map<string, string>;
	private adjacencyList: Map<string, string[]>;
	private reverseAdjacencyList: Map<string, string[]>;
	private startTime: number = 0;
	private onNodeStatusChange?: (nodeId: string, status: string, result?: any) => void;
	private aborted: boolean = false;
	private currentController?: AbortController;

	/**
	 * Smart node result lookup - matches by exact ID or by node type prefix
	 * e.g., "websearch" will match "websearch_123_abc" if no exact match found
	 */
	private getNodeResult(nodeId: string): any | undefined {
		let result = this.nodeResults.get(nodeId);
		
		// If not found by exact ID, try to find by node type prefix
		if (result === undefined && !nodeId.includes('_')) {
			for (const [id, res] of this.nodeResults.entries()) {
				if (id.startsWith(nodeId + '_')) {
					return res;
				}
			}
		}
		
		return result;
	}

	constructor(
		nodes: FlowNode[],
		edges: FlowEdge[],
		onNodeStatusChange?: (nodeId: string, status: string, result?: any) => void
	) {
		this.nodes = new Map(nodes.map((n) => [n.id, n]));
		this.edges = edges;
		this.nodeResults = new Map();
		this.errors = new Map();
		this.adjacencyList = new Map();
		this.reverseAdjacencyList = new Map();
		this.onNodeStatusChange = onNodeStatusChange;

		// Build adjacency lists
		this.buildAdjacencyLists();
	}

	private buildAdjacencyLists(): void {
		// Initialize adjacency lists
		this.nodes.forEach((_, nodeId) => {
			this.adjacencyList.set(nodeId, []);
			this.reverseAdjacencyList.set(nodeId, []);
		});

		// Build forward and reverse adjacency lists
		this.edges.forEach((edge) => {
			const sourceList = this.adjacencyList.get(edge.source) || [];
			sourceList.push(edge.target);
			this.adjacencyList.set(edge.source, sourceList);

			const targetList = this.reverseAdjacencyList.get(edge.target) || [];
			targetList.push(edge.source);
			this.reverseAdjacencyList.set(edge.target, targetList);
		});
	}

	private topologicalSort(): string[] {
		const sorted: string[] = [];
		const visited = new Set<string>();
		const visiting = new Set<string>();

		const visit = (nodeId: string): boolean => {
			if (visited.has(nodeId)) return true;
			if (visiting.has(nodeId)) {
				// Cycle detected
				this.errors.set(nodeId, 'Circular dependency detected');
				return false;
			}

			visiting.add(nodeId);

			const dependencies = this.reverseAdjacencyList.get(nodeId) || [];
			for (const depId of dependencies) {
				if (!visit(depId)) return false;
			}

			visiting.delete(nodeId);
			visited.add(nodeId);
			sorted.push(nodeId);

			return true;
		};

		// Visit all nodes
		for (const nodeId of this.nodes.keys()) {
			if (!visited.has(nodeId)) {
				if (!visit(nodeId)) {
					throw new Error('Circular dependency detected in flow');
				}
			}
		}

		return sorted;
	}

	abort(): void {
		this.aborted = true;
		if (this.currentController) {
			this.currentController.abort();
		}
		console.log('Flow execution aborted by user');
	}

	async execute(): Promise<FlowExecutionResult> {
		this.startTime = Date.now();
		this.nodeResults.clear();
		this.errors.clear();
		this.aborted = false;

		try {
			// Get execution order
			const executionOrder = this.topologicalSort();

			// Execute nodes in order
			for (const nodeId of executionOrder) {
				if (this.aborted) {
					throw new Error('Flow execution aborted by user');
				}
				await this.executeNode(nodeId);
			}

			return {
				flowId: '',
				status: this.errors.size > 0 ? 'error' : 'success',
				nodeResults: Object.fromEntries(this.nodeResults),
				errors: this.errors.size > 0 ? Object.fromEntries(this.errors) : undefined,
				executionTime: Date.now() - this.startTime,
				timestamp: Date.now()
			};
		} catch (error) {
			console.error('Flow execution error:', error);
			return {
				flowId: '',
				status: 'error',
				nodeResults: Object.fromEntries(this.nodeResults),
				errors: { global: (error as Error).message },
				executionTime: Date.now() - this.startTime,
				timestamp: Date.now()
			};
		}
	}

	private async executeNode(nodeId: string): Promise<void> {
		const node = this.nodes.get(nodeId);
		if (!node) {
			this.errors.set(nodeId, 'Node not found');
			return;
		}

		// Update status to running
		this.onNodeStatusChange?.(nodeId, 'running');

		try {
			// Get inputs from predecessor nodes
			const inputs = this.getNodeInputs(nodeId);

			let result: any;

			// Execute based on node type
			switch (node.type) {
				case 'input':
					result = await this.executeInputNode(node);
					break;
				case 'model':
					result = await this.executeModelNode(node, inputs);
					break;
				case 'output':
					result = await this.executeOutputNode(node, inputs);
					break;
				case 'transform':
					result = await this.executeTransformNode(node, inputs);
					break;
				case 'knowledge':
					result = await this.executeKnowledgeNode(node, inputs);
					break;
				case 'websearch':
					result = await this.executeWebSearchNode(node, inputs);
					break;
				case 'conditional':
					result = await this.executeConditionalNode(node, inputs);
					break;
				case 'loop':
					result = await this.executeLoopNode(node, inputs);
					break;
				case 'merge':
					result = await this.executeMergeNode(node, inputs);
					break;
				default:
					throw new Error(`Unknown node type: ${node.type}`);
			}

			// Store result
			this.nodeResults.set(nodeId, result);
			this.onNodeStatusChange?.(nodeId, 'success', result);
			
			// Update connected output nodes immediately for real-time display
			await this.updateConnectedOutputNodes(nodeId);
		} catch (error) {
			// Check if this is an abort error
			if (error instanceof Error && (error.name === 'AbortError' || this.aborted)) {
				this.errors.set(nodeId, 'Execution aborted');
				this.onNodeStatusChange?.(nodeId, 'error', { error: 'Aborted' });
			} else {
				const errorMsg = (error as Error).message;
				this.errors.set(nodeId, errorMsg);
				this.onNodeStatusChange?.(nodeId, 'error', { error: errorMsg });
			}
		}
	}

	private getNodeInputs(nodeId: string): any[] {
		const predecessors = this.reverseAdjacencyList.get(nodeId) || [];
		return predecessors.map((predId) => this.nodeResults.get(predId)).filter((r) => r !== undefined);
	}

	private async updateConnectedOutputNodes(nodeId: string): Promise<void> {
		// Find all output nodes connected to this node
		const successors = this.adjacencyList.get(nodeId) || [];
		
		for (const successorId of successors) {
			const successorNode = this.nodes.get(successorId);
			if (successorNode && successorNode.type === 'output') {
				// Get the result from the completed node
				const result = this.nodeResults.get(nodeId);
				if (result !== undefined) {
					// Execute the output node to format the result
					try {
						console.log(`⚡ Updating output node ${successorId} with result from ${nodeId}`);
						const outputResult = await this.executeOutputNode(successorNode, [result]);
						// Update the output node's UI immediately
						this.onNodeStatusChange?.(successorId, 'success', outputResult);
					} catch (error) {
						console.error(`Error updating output node ${successorId}:`, error);
					}
				}
			}
		}
	}

	private async fetchMediaAsDataUri(fileId: string, token: string): Promise<{ dataUri: string; mimeType: string; isVideo: boolean }> {
		try {
			const baseUrl = WEBUI_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : '');
			const url = `${baseUrl}/api/v1/files/${fileId}/content`;
			
			const response = await fetch(url, {
				headers: {
					Authorization: `Bearer ${token}`
				}
			});
			
			if (!response.ok) {
				throw new Error(`Failed to fetch media: ${response.statusText}`);
			}
			
			// Get the blob and convert to base64
			const blob = await response.blob();
			const arrayBuffer = await blob.arrayBuffer();
			const base64 = btoa(
				new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
			);
			
			// Get mime type from response or default to image/png
			const mimeType = response.headers.get('content-type') || 'image/png';
			const isVideo = mimeType.startsWith('video/');
			
			return {
				dataUri: `data:${mimeType};base64,${base64}`,
				mimeType,
				isVideo
			};
		} catch (error) {
			console.error('Error fetching media as data URI:', error);
			throw error;
		}
	}
	
	private async fetchImageAsDataUri(fileId: string, token: string): Promise<string> {
		const result = await this.fetchMediaAsDataUri(fileId, token);
		return result.dataUri;
	}

	private async executeInputNode(node: FlowNode): Promise<string> {
		const data = node.data as any;
		// If there's a media file, return the file ID
		// Otherwise return the text value
		return data.mediaFileId || data.value || '';
	}

	private async executeModelNode(node: FlowNode, inputs: any[]): Promise<string> {
		const data = node.data as any;

		if (!data.modelId) {
			throw new Error('No model selected');
		}

		console.log('=== Model Node Execution ===');
		console.log('Model:', data.modelId);
		console.log('Raw inputs:', inputs);
		console.log('Prompt template:', data.prompt);

		// Interpolate prompt with inputs
		let prompt = data.prompt || '';
		let imageFileIds: string[] = [];
		let textInputs: string[] = [];
		
		// Process all inputs - separate file IDs from text
		for (let i = 0; i < inputs.length; i++) {
			const input = inputs[i];
			console.log(`Input ${i}:`, typeof input, 'Value:', input);
			
			const inputStr = typeof input === 'string' ? input : JSON.stringify(input);
			
			// Check if it's a UUID (file ID)
			if (typeof input === 'string' && /^[a-f0-9-]{36}$/i.test(input.trim())) {
				const fileId = input.trim();
				imageFileIds.push(fileId);
				console.log(`✓ Detected file ID at input ${i}:`, fileId);
			} else {
				// Regular text input
				textInputs.push(inputStr);
				console.log(`✓ Detected text at input ${i}`);
			}
		}
		
		// Build the prompt based on what we have
		if (imageFileIds.length > 0) {
			// We have images
			const filePaths = imageFileIds.map(id => `/api/v1/files/${id}/content`).join('\n');
			
			if (textInputs.length > 0) {
				// We have both images and text inputs
				// For native models: use clean text prompt (images sent separately)
				// For pipelines: prepend file paths to text
				const textPrompt = textInputs.join('\n\n');
				prompt = textPrompt; // Start with clean text
				console.log('✓ Using text inputs (will add file paths for pipelines only)');
			} else if (prompt.includes('{{input}}')) {
				// Template has {{input}} - just remove it for native models
				prompt = prompt.replace(/\{\{\s*input\s*\}\}/g, '').trim();
				if (!prompt) {
					prompt = 'Analyze this image in detail.';
				}
				console.log('✓ Removed {{input}} placeholder for vision model');
			} else if (!prompt) {
				// No custom prompt - check if this looks like a video prompt generator
				if (data.modelId && data.modelId.toLowerCase().includes('video')) {
					prompt = 'Analyze this image and create a detailed cinematic video generation prompt describing camera movements, lighting, atmosphere, and visual techniques to bring this scene to life as a video.';
					console.log('✓ Using default video prompt generation instruction');
				} else {
					prompt = 'Analyze this image in detail.';
					console.log('✓ Using default vision prompt');
				}
			}
			// Note: We'll add file paths back for pipelines later
		} else if (textInputs.length > 0) {
			// Only text inputs, no images
			const combinedText = textInputs.join('\n\n');
			if (prompt.includes('{{input}}')) {
				prompt = prompt.replace(/\{\{\s*input\s*\}\}/g, combinedText);
			} else if (!prompt) {
				prompt = combinedText;
			}
			console.log('✓ Using text inputs');
		} else if (prompt.includes('{{input}}')) {
			// No inputs but has {{input}} template - remove it
			prompt = prompt.replace(/\{\{\s*input\s*\}\}/g, '').trim();
		}

		// Prompt should now contain the file path if we have images
		if (!prompt) {
			throw new Error('No prompt configured');
		}

		// Call the model
		const token = localStorage.getItem('token') || '';
		
		// Detect if this is a pipeline/function (they extract images from content)
		// vs a native model (they use the images array)
		const isPipeline = data.modelId && (
			data.modelId.includes('function') ||
			data.modelId.includes('pipe') ||
			data.modelId.toLowerCase().includes('veo') ||
			data.modelId.toLowerCase().includes('runway') ||
			data.modelId.toLowerCase().includes('kling') ||
			data.modelId.toLowerCase().includes('gemini')
		);
		
		// For pipelines: prepend file paths to content for extraction
		// For native models: keep content clean, use images array
		if (imageFileIds.length > 0 && isPipeline) {
			const filePaths = imageFileIds.map(id => `/api/v1/files/${id}/content`).join('\n');
			prompt = prompt ? `${filePaths}\n\n${prompt}` : filePaths;
			console.log('✓ Added file paths to content for pipeline extraction');
		}
		
		// Create a chat completion request
		// For native models with images, use OpenAI vision API format
		const userMessage: any = {
			role: 'user'
		};
		
		// Add images for models (format depends on pipeline vs native)
		if (imageFileIds.length > 0) {
			if (isPipeline) {
				// Pipelines can work with just file IDs in images array
				userMessage.content = prompt;
				userMessage.images = imageFileIds;
				console.log(`✓ Added file IDs for pipeline:`, imageFileIds);
			} else {
				// Native models use OpenAI vision API format
				// Fetch media (images/videos) and convert to data URIs (base64) since file endpoints require auth
				console.log('⏳ Fetching media and converting to base64 data URIs...');
				try {
					const mediaResults = await Promise.all(
						imageFileIds.map(id => this.fetchMediaAsDataUri(id, token))
					);
					
					const contentItems: any[] = [];
					const videoDataUris: string[] = [];
					
					// Separate videos from images
					for (const media of mediaResults) {
						if (media.isVideo) {
							videoDataUris.push(media.dataUri);
						} else {
							// Add images using image_url format
							contentItems.push({
								type: 'image_url',
								image_url: {
									url: media.dataUri
								}
							});
						}
					}
					
					// For videos, include the data URI in the text content as well
					// This allows pipelines that parse content to find videos
					let finalPrompt = prompt;
					if (videoDataUris.length > 0) {
						finalPrompt = videoDataUris.join('\n') + '\n\n' + prompt;
						console.log('✓ Added video data URIs to text content for pipeline extraction');
					}
					
					// Add text content first
					contentItems.unshift({
						type: 'text',
						text: finalPrompt
					});
					
					// Also add videos as image_url for models that support it
					for (const videoUri of videoDataUris) {
						contentItems.push({
							type: 'image_url',
							image_url: {
								url: videoUri
							}
						});
					}
					
					userMessage.content = contentItems;
					
					const imageCount = mediaResults.filter(m => !m.isVideo).length;
					const videoCount = mediaResults.filter(m => m.isVideo).length;
					console.log(`✓ Formatted ${imageCount} image(s) and ${videoCount} video(s) as base64 data URIs`);
				} catch (error) {
					console.error('Failed to fetch media:', error);
					throw new Error(`Failed to fetch media: ${(error as Error).message}`);
				}
			}
		} else {
			// No images - just text content
			userMessage.content = prompt;
		}
		
		const messages = [userMessage];
		console.log('Final prompt:', prompt);
		
		// Log message but truncate base64 data URIs for readability
		const messageForLogging = { ...userMessage };
		if (Array.isArray(messageForLogging.content)) {
			messageForLogging.content = messageForLogging.content.map((item: any) => {
				if (item.type === 'image_url' && item.image_url?.url?.startsWith('data:')) {
					const dataUrl = item.image_url.url;
					const isVideo = dataUrl.startsWith('data:video/');
					const mediaType = isVideo ? 'video' : 'image';
					return {
						...item,
						image_url: {
							url: `[base64 ${mediaType} ~${Math.round(dataUrl.length / 1024)}KB]`
						}
					};
				}
				return item;
			});
		}
		console.log('Final message:', JSON.stringify(messageForLogging, null, 2));

		try {
			// Build request body with required fields
			const requestBody: any = {
				model: data.modelId,
				messages,
				stream: false,
				session_id: 'flow-execution', // Required by API
				chat_id: `flow-${Date.now()}` // Required by API
			};
			
			// Only include advanced settings if enabled
			if (data.useAdvancedSettings) {
				if (data.temperature !== undefined) {
					requestBody.temperature = data.temperature;
				}
				if (data.max_tokens && !isNaN(data.max_tokens)) {
					requestBody.max_tokens = data.max_tokens;
				}
			}
			
			// Log request body but truncate base64 media
			const requestBodyForLogging = {
				...requestBody,
				messages: requestBody.messages.map((msg: any) => {
					if (Array.isArray(msg.content)) {
						return {
							...msg,
							content: msg.content.map((item: any) => {
								if (item.type === 'image_url' && item.image_url?.url?.startsWith('data:')) {
									const dataUrl = item.image_url.url;
									const isVideo = dataUrl.startsWith('data:video/');
									const mediaType = isVideo ? 'video' : 'image';
									return {
										...item,
										image_url: {
											url: `[base64 ${mediaType} ~${Math.round(dataUrl.length / 1024)}KB]`
										}
									};
								}
								return item;
							})
						};
					}
					return msg;
				})
			};
			console.log('Full request body:', JSON.stringify(requestBodyForLogging, null, 2));
			
			// Using the chatCompletion API - it returns [response, controller]
			const [res, controller] = await chatCompletion(token, requestBody);
			this.currentController = controller;

			console.log('Response status:', res?.status, res?.statusText);
			console.log('Response headers:', res?.headers);

			if (!res || !res.ok) {
				// Try to get error details from response
				let errorDetail = res?.statusText || 'Unknown error';
				try {
					const errorText = await res?.text();
					console.error('Error response body:', errorText);
					if (errorText) {
						try {
							const errorData = JSON.parse(errorText);
							if (errorData?.detail) {
								errorDetail = errorData.detail;
							} else if (errorData?.error) {
								errorDetail = errorData.error;
							}
						} catch (e) {
							errorDetail = errorText;
						}
					}
				} catch (e) {
					// Ignore text read errors
				}
				throw new Error(`API request failed: ${errorDetail}`);
			}

			// Parse the JSON response
			const responseText = await res.text();
			console.log('Raw response text:', responseText.substring(0, 500)); // First 500 chars
			
			const responseData = JSON.parse(responseText);
			console.log('Parsed response data:', responseData);

			// Handle messages array format (Open WebUI format)
			if (responseData && responseData.messages && Array.isArray(responseData.messages)) {
				// Get the last message (assistant's response)
				const lastMessage = responseData.messages[responseData.messages.length - 1];
				if (lastMessage && lastMessage.content) {
					let content = lastMessage.content;
					console.log('Assistant message content:', content);
					
					// Check for error messages
					if (typeof content === 'string') {
						const lowerContent = content.toLowerCase();
						if (
							lowerContent.includes("wasn't able to generate") ||
							lowerContent.includes("unable to generate") ||
							lowerContent.includes("failed to generate") ||
							lowerContent.includes("error generating") ||
							lowerContent.includes("❌ error")
						) {
							console.error('Model returned an error:', content);
							throw new Error(`Model failed: ${content}`);
						}
						
						// Match /api/v1/files/{id}/content or /files/{id}/content
						const fileIdMatch = content.match(/\/(?:api\/v1\/)?files\/([a-f0-9-]+)\/content/);
						if (fileIdMatch) {
							// Found a file ID - return just the ID
							console.log('✓ Extracted file ID from messages:', fileIdMatch[1]);
							console.log('✓ Returning file ID to next node');
							return fileIdMatch[1];
						}
					}
					
					console.log('✓ Returning text content:', content.substring(0, 100));
					return content;
				}
			}
			
			// Handle image generation responses
			if (responseData && responseData.images && responseData.images.length > 0) {
				// Image generation - return first image (base64 or URL)
				return responseData.images[0];
			}
			
			// Handle standard chat completion responses (OpenAI format)
			if (responseData && responseData.choices && responseData.choices[0]) {
				let content = responseData.choices[0].message.content;
				
				// Check for error messages
				if (typeof content === 'string') {
					const lowerContent = content.toLowerCase();
					if (
						lowerContent.includes("wasn't able to generate") ||
						lowerContent.includes("unable to generate") ||
						lowerContent.includes("failed to generate") ||
						lowerContent.includes("error generating") ||
						lowerContent.includes("❌ error")
					) {
						console.error('Model returned an error:', content);
						throw new Error(`Model failed: ${content}`);
					}
					
					// Match /api/v1/files/{id}/content or /files/{id}/content
					const fileIdMatch = content.match(/\/(?:api\/v1\/)?files\/([a-f0-9-]+)\/content/);
					if (fileIdMatch) {
						// Found a file ID - return just the ID
						console.log('Extracted file ID from choices:', fileIdMatch[1]);
						return fileIdMatch[1];
					}
				}
				
				return content;
			}
			
			// Handle other possible response formats
			if (responseData && responseData.data && Array.isArray(responseData.data)) {
				// Some APIs return data array (like DALL-E)
				if (responseData.data[0].url) {
					return responseData.data[0].url;
				}
				if (responseData.data[0].b64_json) {
					return `data:image/png;base64,${responseData.data[0].b64_json}`;
				}
			}

			console.error('Unexpected response format:', responseData);
			throw new Error('Invalid response from model - check console for details');
		} catch (error) {
			// Check if this is an abort error
			if (error instanceof Error && (error.name === 'AbortError' || this.aborted)) {
				console.log('Model execution aborted');
				throw new Error('Execution aborted by user');
			}
			console.error('Model execution error:', error);
			// Better error handling to capture different error formats
			let errorMessage = 'Unknown error';
			if (error instanceof Error) {
				errorMessage = error.message;
			} else if (typeof error === 'string') {
				errorMessage = error;
			} else if (error && typeof error === 'object') {
				errorMessage = JSON.stringify(error);
			}
			throw new Error(`Model execution failed: ${errorMessage}`);
		}
	}

	private async executeOutputNode(node: FlowNode, inputs: any[]): Promise<any> {
		const data = node.data as any;
		const input = inputs[0];

		// Handle file format - upload base64 data to files API or use existing file ID
		if (data.format === 'file') {
			const fileType = data.fileType || 'image';
			
			// Input can be a file ID, URL, or base64 data
			if (typeof input === 'string') {
				// Check if it's base64 data
				if (input.startsWith('data:')) {
					// Base64 data - convert to file and upload
					try {
						const token = localStorage.getItem('token') || '';
						
						// Convert base64 to blob
						const response = await fetch(input);
						const blob = await response.blob();
						
						// Determine file extension based on MIME type
						const mimeType = blob.type;
						let ext = 'bin';
						if (mimeType.startsWith('image/')) ext = mimeType.split('/')[1];
						else if (mimeType.startsWith('video/')) ext = mimeType.split('/')[1];
						else if (mimeType.startsWith('audio/')) ext = mimeType.split('/')[1];
						
						// Create file from blob
						const file = new File([blob], `flow-output.${ext}`, { type: mimeType });
						
						// Upload file
						const uploadResult = await uploadFile(token, file, {
							source: 'flow',
							type: fileType
						});
						
						if (uploadResult && uploadResult.id) {
							return { fileId: uploadResult.id, fileType };
						}
						
						throw new Error('File upload failed');
					} catch (error) {
						throw new Error(`Failed to upload file: ${(error as Error).message}`);
					}
				}
				
				// Check if it's a UUID (file ID)
				if (/^[a-f0-9-]{36}$/i.test(input.trim())) {
					console.log('Using existing file ID:', input);
					return { fileId: input.trim(), fileType };
				}
				
				// Otherwise assume it's a file ID (might not be UUID format)
				console.log('Assuming input is file ID:', input);
				return { fileId: input, fileType };
			}
			
			throw new Error('Invalid file input - expected base64 data or file ID');
		}

		// Handle other formats
		let formattedValue;
		switch (data.format) {
			case 'json':
				try {
					formattedValue = JSON.parse(input);
				} catch {
					formattedValue = input;
				}
				break;
			case 'markdown':
			case 'text':
			default:
				formattedValue = input;
		}
		
		// Return as object with value field so OutputNode can display it
		return { value: formattedValue };
	}

	private async executeTransformNode(node: FlowNode, inputs: any[]): Promise<any> {
		const data = node.data as any;
		const input = inputs[0];
		
		if (!input) {
			throw new Error('No input provided');
		}

		const inputStr = typeof input === 'string' ? input : JSON.stringify(input);

		// Implement transform operations
		switch (data.operation) {
			case 'uppercase':
				return inputStr.toUpperCase();
				
			case 'lowercase':
				return inputStr.toLowerCase();
				
			case 'trim':
				return inputStr.trim();
				
			case 'replace':
				// Replace text based on pattern
				if (!data.config?.pattern) {
					throw new Error('Pattern not configured');
				}
				const replacement = data.config.replacement || '';
				return inputStr.replace(new RegExp(data.config.pattern, 'g'), replacement);
				
			case 'extract':
				// Extract specific fields from JSON
				if (!data.config?.field) {
					throw new Error('Field not configured');
				}
				try {
					const parsed = typeof input === 'string' ? JSON.parse(input) : input;
					return parsed[data.config.field];
				} catch {
					throw new Error('Failed to extract field from input');
				}
				
			case 'template':
				// Apply template with {{input}} placeholder
				if (!data.config?.template) {
					throw new Error('Template not configured');
				}
				return data.config.template.replace(/\{\{\s*input\s*\}\}/g, inputStr);
				
			default:
				return input;
		}
	}

	private async executeKnowledgeNode(node: FlowNode, inputs: any[]): Promise<any> {
		const data = node.data as any;
		
		if (!data.knowledgeBaseId) {
			throw new Error('No knowledge base selected');
		}

		if (!data.query) {
			throw new Error('No query provided');
		}

		console.log('=== Knowledge Node Execution ===');
		console.log('Knowledge Base:', data.knowledgeBaseId);
		console.log('Query template:', data.query);

		// Interpolate query with inputs
		let query = data.query;
		
		// Replace {{input}} with the first input
		if (inputs.length > 0) {
			const inputStr = typeof inputs[0] === 'string' ? inputs[0] : JSON.stringify(inputs[0]);
			query = query.replace(/\{\{\s*input\s*\}\}/g, inputStr);
		}

		// Replace {{node_id.output}} patterns with node results
		query = query.replace(/\{\{\s*([a-zA-Z0-9_-]+)\.output\s*\}\}/g, (match: string, nodeId: string) => {
			const result = this.getNodeResult(nodeId);
			if (result !== undefined) {
				return typeof result === 'string' ? result : JSON.stringify(result);
			}
			return match; // Keep original if node not found
		});

		console.log('Interpolated query:', query);

		try {
			// Get auth token
			const token = localStorage.getItem('token') || '';
			
			// Get knowledge base details to find collection name
			const knowledgeBase = await getKnowledgeById(token, data.knowledgeBaseId);
			console.log('Knowledge base object:', knowledgeBase);
			
			if (!knowledgeBase) {
				throw new Error('Knowledge base not found');
			}

			// The collection name is typically just the knowledge base ID
			let collectionName = knowledgeBase.data?.collection_name 
				|| knowledgeBase.collection_name 
				|| data.knowledgeBaseId; // Use the ID directly as collection name
			
			console.log('Using collection name:', collectionName);

			// Query the knowledge base using the retrieval API
			const topK = data.topK || 4;
			const result = await queryDoc(token, collectionName, query, topK);
			
			console.log('Knowledge query result:', result);

			// Format the results
			if (result && result.documents && result.documents.length > 0) {
				// Extract relevant chunks with metadata
				const chunks = result.documents.map((doc: any, index: number) => {
					const metadata = result.metadatas?.[index] || {};
					const distance = result.distances?.[index];
					
					return {
						content: doc,
						metadata: data.includeMetadata ? metadata : undefined,
						relevanceScore: distance !== undefined ? (1 - distance) : undefined
					};
				});

				// Filter by confidence threshold if specified
				const filteredChunks = data.confidenceThreshold
					? chunks.filter((chunk: any) => 
						!chunk.relevanceScore || chunk.relevanceScore >= data.confidenceThreshold
					)
					: chunks;

				if (filteredChunks.length === 0) {
					return {
						chunks: [],
						message: 'No results met the confidence threshold'
					};
				}

				// Return formatted results
				return {
					chunks: filteredChunks,
					count: filteredChunks.length,
					query: query,
					knowledgeBase: knowledgeBase.name
				};
			} else {
				return {
					chunks: [],
					message: 'No relevant documents found'
				};
			}
		} catch (error) {
			console.error('Knowledge query error:', error);
			throw new Error(`Knowledge query failed: ${(error as Error).message}`);
		}
	}

	private async executeWebSearchNode(node: FlowNode, inputs: any[]): Promise<any> {
		const data = node.data as any;
		
		if (!data.query) {
			throw new Error('No search query provided');
		}

		console.log('=== Web Search Node Execution ===');
		console.log('Node data:', data);

		// Get query with variable interpolation
		let query = data.query || '';
		const maxResults = data.maxResults || 5;
		
		// Replace {{input}} with the first input
		if (inputs.length > 0) {
			const inputStr = typeof inputs[0] === 'string' ? inputs[0] : JSON.stringify(inputs[0]);
			query = query.replace(/\{\{\s*input\s*\}\}/g, inputStr);
		}

		// Replace {{node_id.output}} patterns with node results
		query = query.replace(/\{\{\s*([a-zA-Z0-9_-]+)\.output\s*\}\}/g, (match: string, nodeId: string) => {
			const result = this.getNodeResult(nodeId);
			if (result !== undefined) {
				return typeof result === 'string' ? result : JSON.stringify(result);
			}
			return match; // Keep original if node not found
		});

		console.log('Interpolated query:', query);

		try {
			// Get auth token
			const token = localStorage.getItem('token') || '';
			
			// Perform web search - Note: processWebSearch expects query and optional collection_name
			// We'll let it create a temporary collection automatically by passing undefined
			const searchResult = await processWebSearch(token, query, undefined);
			
			console.log('Web search result:', searchResult);

			if (!searchResult || !searchResult.status) {
				throw new Error('No search results returned');
			}

			// Try to query the collection to get the actual documents with metadata
			let results: any[] = [];
			
			try {
				const collectionResult = await queryCollection(
					token,
					searchResult.collection_name,
					query,
					maxResults || 5
				);

				console.log('Collection query result:', collectionResult);

				// Extract structured results with URLs
				if (collectionResult?.documents?.[0]) {
					results = collectionResult.documents[0].map((doc: any, index: number) => {
						const metadata = collectionResult?.metadatas?.[0]?.[index] || {};
						return {
							title: metadata.title || metadata.source || `Result ${index + 1}`,
							url: metadata.source || metadata.url || '',
							content: doc || '',
							snippet: doc ? doc.substring(0, 200) + '...' : '',
							metadata: metadata
						};
					});
				}
			} catch (collectionError) {
				console.warn('Collection query failed, using filenames only:', collectionError);
				// Fallback: use filenames from search result
				results = (searchResult.filenames || []).map((filename: string, index: number) => ({
					title: filename,
					url: filename,
					content: '',
					snippet: filename,
					metadata: { source: filename }
				}));
			}

			console.log('Structured results:', results);

			// Return both structured array and formatted text
			return {
				query: query,
				results: results, // Array for looping
				count: results.length,
				collection_name: searchResult.collection_name,
				// Formatted text for direct use
				text: results.length > 0
					? `Found ${results.length} results:\n\n` + 
					  results.map((r: any, i: number) => 
						`${i + 1}. ${r.title}\n   URL: ${r.url}\n   ${r.snippet}`
					  ).join('\n\n')
					: `No results found for "${query}"`
			};
		} catch (error) {
			console.error('Web search error:', error);
			// Try to extract the actual error message
			let errorMessage = 'Unknown error';
			if (Array.isArray(error)) {
				errorMessage = error.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
			} else if (error instanceof Error) {
				errorMessage = error.message;
			} else if (typeof error === 'string') {
				errorMessage = error;
			}
			throw new Error(`Web search failed: ${errorMessage}`);
		}
	}

	private async executeConditionalNode(node: FlowNode, inputs: any[]): Promise<any> {
		const data = node.data as any;
		
		console.log('=== Conditional Node Execution ===');
		console.log('Condition:', data.condition);
		console.log('Operator:', data.operator);
		console.log('Compare value:', data.compareValue);

		// Get condition value (with variable interpolation)
		let conditionValue = data.condition || '';
		
		// Replace {{input}} with first input
		if (inputs.length > 0) {
			const inputStr = typeof inputs[0] === 'string' ? inputs[0] : JSON.stringify(inputs[0]);
			conditionValue = conditionValue.replace(/\{\{\s*input\s*\}\}/g, inputStr);
		}

		// Replace {{node_id.output}} patterns
		conditionValue = conditionValue.replace(/\{\{\s*([a-zA-Z0-9_-]+)\.output\s*\}\}/g, (match: string, nodeId: string) => {
			const result = this.getNodeResult(nodeId);
			if (result !== undefined) {
				return typeof result === 'string' ? result : JSON.stringify(result);
			}
			return match;
		});

		const compareValue = data.compareValue || '';
		const operator = data.operator || 'equals';

		console.log('Evaluated condition value:', conditionValue);
		console.log('Comparing against:', compareValue);

		// Evaluate condition
		let result = false;
		try {
			switch (operator) {
				case 'equals':
					result = conditionValue === compareValue;
					break;
				case 'not_equals':
					result = conditionValue !== compareValue;
					break;
				case 'contains':
					result = conditionValue.includes(compareValue);
					break;
				case 'greater':
					result = parseFloat(conditionValue) > parseFloat(compareValue);
					break;
				case 'less':
					result = parseFloat(conditionValue) < parseFloat(compareValue);
					break;
				case 'regex':
					const regex = new RegExp(compareValue);
					result = regex.test(conditionValue);
					break;
				default:
					result = false;
			}
		} catch (error) {
			console.error('Condition evaluation error:', error);
			throw new Error(`Failed to evaluate condition: ${(error as Error).message}`);
		}

		console.log('Condition result:', result);

		return {
			condition: conditionValue,
			result: result,
			branch: result ? 'true' : 'false'
		};
	}

	private async executeLoopNode(node: FlowNode, inputs: any[]): Promise<any> {
		const data = node.data as any;
		
		console.log('=== Loop Node Execution ===');
		console.log('Loop type:', data.loopType);
		console.log('Max iterations:', data.maxIterations);

		const loopType = data.loopType || 'count';
		const maxIterations = data.maxIterations || 5;
		const results: any[] = [];

		try {
			if (loopType === 'count') {
				// Simple count loop
				for (let i = 0; i < maxIterations; i++) {
					console.log(`Loop iteration ${i + 1}/${maxIterations}`);
					results.push({
						iteration: i,
						value: inputs[0] // Pass through input
					});
				}
			} else if (loopType === 'array') {
				// Loop over array
				let arrayPath = data.arrayPath || '{{input}}';
				
				console.log('Original array path:', arrayPath);
				
				// Interpolate array path
				let array: any;
				
				if (arrayPath === '{{input}}' && inputs.length > 0) {
					array = inputs[0];
				} else if (arrayPath.includes('{{')) {
					// Handle template syntax: {{node_id.output.path.to.array}}
					const templateMatch = arrayPath.match(/\{\{\s*([a-zA-Z0-9_-]+)\.output(\.[\w.]+)?\s*\}\}/);
					
					if (templateMatch) {
						const nodeId = templateMatch[1];
						const path = templateMatch[2];
						
						console.log(`Interpolating: nodeId=${nodeId}, path=${path || ''}`);
						
						const result = this.getNodeResult(nodeId);
						
						if (result === undefined) {
							throw new Error(`Node ${nodeId} not found in results. Available nodes: ${Array.from(this.nodeResults.keys()).join(', ')}`);
						}
						
						console.log('Node result:', result);
						
						// If there's a path after .output, navigate to it
						if (path) {
							const keys = path.substring(1).split('.'); // Remove leading dot and split
							let value = result;
							for (const key of keys) {
								if (value && typeof value === 'object' && key in value) {
									value = value[key];
								} else {
									throw new Error(`Path ${key} not found in result at ${keys.slice(0, keys.indexOf(key) + 1).join('.')}`);
								}
							}
							array = value;
						} else {
							array = result;
						}
						
						console.log('Extracted value:', array);
					} else {
						throw new Error(`Invalid array path template: ${arrayPath}`);
					}
				} else {
					// Try to parse as JSON or split
					try {
						array = JSON.parse(arrayPath);
					} catch {
						array = arrayPath.split(/[\n,]/).map((s: string) => s.trim()).filter(Boolean);
					}
				}

				console.log('Resolved array:', array);

				if (!Array.isArray(array)) {
					throw new Error(`Loop array must be an array. Got: ${typeof array}. Value: ${JSON.stringify(array)}`);
				}

				console.log(`Looping over array with ${array.length} items`);
				for (let i = 0; i < Math.min(array.length, maxIterations); i++) {
					results.push({
						iteration: i,
						value: array[i]
					});
				}
			} else if (loopType === 'until') {
				// Loop until condition (simplified - just use max iterations for now)
				for (let i = 0; i < maxIterations; i++) {
					results.push({
						iteration: i,
						value: inputs[0]
					});
					// TODO: Implement break condition evaluation
				}
			}

			console.log(`Loop completed with ${results.length} iterations`);

			return {
				iterations: results.length,
				results: results
			};
		} catch (error) {
			console.error('Loop execution error:', error);
			throw new Error(`Loop failed: ${(error as Error).message}`);
		}
	}

	private async executeMergeNode(node: FlowNode, inputs: any[]): Promise<any> {
		const data = node.data as any;
		
		console.log('=== Merge Node Execution ===');
		console.log('Strategy:', data.strategy);
		console.log('Inputs:', inputs);

		const strategy = data.strategy || 'concat';
		const separator = data.separator || '\n';

		try {
			let result: any;

			switch (strategy) {
				case 'concat':
					// Concatenate all inputs as strings
					result = inputs
						.map(input => typeof input === 'string' ? input : JSON.stringify(input))
						.join(separator.replace(/\\n/g, '\n'));
					break;
				
				case 'array':
					// Combine as array
					result = inputs;
					break;
				
				case 'first':
					// Take first input
					result = inputs[0];
					break;
				
				case 'last':
					// Take last input
					result = inputs[inputs.length - 1];
					break;
				
				default:
					result = inputs[0];
			}

			console.log('Merge result:', result);

			return result;
		} catch (error) {
			console.error('Merge execution error:', error);
			throw new Error(`Merge failed: ${(error as Error).message}`);
		}
	}
}
