<script lang="ts">
	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { config, settings, user, showSidebar, mobile, showArchivedChats } from '$lib/stores';
	import { getModels } from '$lib/apis';
	import { getModels as getWorkspaceModels } from '$lib/apis/models';
	import { getFunctions } from '$lib/apis/functions';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import Clip from '$lib/components/icons/Clip.svelte';
	import Camera from '$lib/components/icons/Camera.svelte';
	import Voice from '$lib/components/icons/Voice.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	let agents: any[] = [];
	let loading = false;
	let files: any[] = [];
	let filesInputElement: HTMLInputElement;
	let cameraInputElement: HTMLInputElement;
	let webSearchEnabled = false;

	const detectMobile = () => {
		const userAgent = navigator.userAgent || navigator.vendor || (window as any).opera;
		return /android|iphone|ipad|ipod|windows phone/i.test(userAgent);
	};

	onMount(async () => {
		loading = true;
		try {
			const connections = $config?.features?.enable_direct_connections ? ($settings?.directConnections ?? null) : null;
			const [allModelsData, workspaceModelsData, functionsData] = await Promise.all([
				getModels(localStorage.token, connections),
				getWorkspaceModels(localStorage.token),
				getFunctions(localStorage.token)
			]);

			// Merge workspace metadata
			const mergedModels = (allModelsData || []).map((m: any) => {
				const workspaceModel = (workspaceModelsData || []).find((wm: any) => wm.id === m.id);
				return workspaceModel ? { ...m, ...workspaceModel } : m;
			});

			// Get agent IDs (assistants + functions)
			const functionIds = new Set((functionsData || []).map((a: any) => a.id));
			const assistantIds = new Set((workspaceModelsData || []).filter((m: any) => m.base_model_id).map((m: any) => m.id));
			const agentIds = new Set([...functionIds, ...assistantIds]);

			// Filter agents
			agents = mergedModels.filter((m: any) => 
				m.is_active !== false && 
				agentIds.has(m.id)
			);
		} catch (error) {
			console.error('Error loading agents:', error);
		} finally {
			loading = false;
		}
	});

	const selectAgent = (agentId: string) => {
		// Store files in sessionStorage if any are attached
		if (files.length > 0) {
			try {
				sessionStorage.setItem('welcome-files', JSON.stringify(files));
			} catch (error) {
				console.error('Failed to store files in sessionStorage:', error);
				toast.error($i18n.t('Files are too large to transfer'));
			}
		}
		goto(`/?models=${encodeURIComponent(agentId)}`);
	};

	const handleSearch = (e: Event) => {
		const formData = new FormData(e.target as HTMLFormElement);
		const message = formData.get('message') as string;
		if (message && message.trim()) {
			// Store files in sessionStorage for Chat component to pick up
			if (files.length > 0) {
				try {
					sessionStorage.setItem('welcome-files', JSON.stringify(files));
				} catch (error) {
					console.error('Failed to store files in sessionStorage:', error);
					toast.error($i18n.t('Files are too large to transfer'));
				}
			}
			
			const params = new URLSearchParams({ q: message.trim() });
			if (webSearchEnabled) {
				params.set('web-search', 'true');
			}
			goto(`/?${params.toString()}`);
		}
	};

	const handleFileUpload = () => {
		filesInputElement?.click();
	};

	const handleCameraCapture = async () => {
		if (!detectMobile()) {
			// Desktop: Use screen capture
			try {
				const stream = await navigator.mediaDevices.getDisplayMedia({
					video: { displaySurface: 'monitor' } as any
				});
				const video = document.createElement('video');
				video.srcObject = stream;
				video.play();

				await new Promise((resolve) => {
					video.onloadedmetadata = resolve;
				});

				const canvas = document.createElement('canvas');
				canvas.width = video.videoWidth;
				canvas.height = video.videoHeight;
				const context = canvas.getContext('2d');
				context?.drawImage(video, 0, 0);

				stream.getTracks().forEach((track) => track.stop());

				const imageUrl = canvas.toDataURL('image/png');
				files = [...files, { type: 'image', url: imageUrl }];
				video.srcObject = null;
			} catch (error) {
				console.error('Screen capture error:', error);
				toast.error($i18n.t('Screen capture failed'));
			}
		} else {
			// Mobile: Use camera input
			cameraInputElement?.click();
		}
	};

	const handleFileInputChange = async (event: Event) => {
		const input = event.target as HTMLInputElement;
		const selectedFiles = Array.from(input.files || []);
		
		for (const file of selectedFiles) {
			if (file.type.startsWith('image/')) {
				const reader = new FileReader();
				reader.onload = (e) => {
					files = [...files, { type: 'image', url: e.target?.result as string, name: file.name }];
				};
				reader.readAsDataURL(file);
			} else {
				// For non-image files, store file object
				files = [...files, { type: 'file', file: file, name: file.name }];
			}
		}
		
		input.value = '';
	};

	const removeFile = (index: number) => {
		files = files.filter((_, i) => i !== index);
	};

	const handleVoiceMode = () => {
		// Store files in sessionStorage if any are attached
		if (files.length > 0) {
			try {
				sessionStorage.setItem('welcome-files', JSON.stringify(files));
			} catch (error) {
				console.error('Failed to store files in sessionStorage:', error);
				toast.error($i18n.t('Files are too large to transfer'));
			}
		}
		goto('/?call=true');
	};
</script>

<div class="h-screen max-h-[100dvh] w-full max-w-full flex flex-col overflow-y-auto {$showSidebar
	? 'md:max-w-[calc(100%-260px)]'
	: ''}"
>
	<!-- Top Navigation Bar -->
	<nav class="sticky top-0 z-30 w-full py-1 pl-1.5 pr-1">
		<div class="w-full flex items-center justify-between">
			<!-- Left: Sidebar button (mobile only) -->
			<div class="flex items-center">
				{#if $mobile && !$showSidebar}
					<Tooltip content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}>
						<button
							class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
							on:click={() => {
								showSidebar.set(!$showSidebar);
							}}
						>
							<div class="self-center p-1.5">
								<Sidebar />
							</div>
						</button>
					</Tooltip>
				{/if}
			</div>

			<!-- Right: User Menu -->
			<div class="flex items-center ml-auto">
				{#if $user !== undefined && $user !== null}
					<UserMenu
						className="max-w-[240px]"
						role={$user?.role}
						help={true}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<div
							class="select-none flex rounded-xl p-1.5 w-full hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						>
							<div class="self-center">
								<span class="sr-only">{$i18n.t('User menu')}</span>
								<img
									src={$user?.profile_image_url}
									class="size-6 object-cover rounded-full"
									alt=""
									draggable="false"
								/>
							</div>
						</div>
					</UserMenu>
				{/if}
			</div>
		</div>
	</nav>

	<div class="px-6 py-8 md:px-12 lg:px-20">
		<div class="max-w-6xl mx-auto w-full">
			<!-- Greeting -->
			<div class="mb-8 mt-6">
				<h1 style="font-size: clamp(1.5rem, 4.5vw, 5.5rem); line-height: 1.1; font-family: 'Public Sans', sans-serif;" class="font-semibold mb-1 text-gray-900 dark:text-white">
					<span class="text-blue-600 dark:text-blue-400">{$i18n.t('Hello, {{name}}.', { name: $user?.name || $i18n.t('there') })}</span>
				</h1>
				<p style="font-size: clamp(1.5rem, 4.5vw, 5.5rem); line-height: 1.1; font-family: 'Public Sans', sans-serif;" class="font-semibold text-gray-600 dark:text-gray-400">{$i18n.t('how can I help?')}</p>
			</div>

			<!-- Chat Input -->
			<div class="mb-12 w-full">
				<!-- Hidden file inputs -->
				<input
					bind:this={filesInputElement}
					type="file"
					multiple
					accept="*/*"
					on:change={handleFileInputChange}
					style="display: none;"
				/>
				<input
					bind:this={cameraInputElement}
					type="file"
					accept="image/*"
					capture="environment"
					on:change={handleFileInputChange}
					style="display: none;"
				/>

				<!-- File previews -->
				{#if files.length > 0}
					<div class="flex flex-wrap gap-2 mb-3">
						{#each files as file, index}
							<div class="relative group">
								{#if file.type === 'image'}
									<img
										src={file.url}
										alt={file.name || 'Uploaded image'}
										class="w-20 h-20 object-cover rounded-lg border-2 border-gray-200 dark:border-gray-700"
									/>
								{:else}
									<div class="w-20 h-20 flex items-center justify-center rounded-lg border-2 border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
										<div class="text-center px-1">
											<svg class="w-6 h-6 mx-auto text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
											</svg>
											<span class="text-xs text-gray-600 dark:text-gray-400 block truncate w-full">{file.name}</span>
										</div>
									</div>
								{/if}
								<button
									type="button"
									on:click={() => removeFile(index)}
									class="absolute -top-2 -right-2 bg-red-500 hover:bg-red-600 text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
								>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
									</svg>
								</button>
							</div>
						{/each}
					</div>
				{/if}

				<form on:submit|preventDefault={handleSearch}>
					<div class="relative">
						<div class="absolute left-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
							<button
								type="button"
								on:click={handleFileUpload}
								class="p-2 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
								title={$i18n.t('Upload Files')}
							>
								<Clip className="w-5 h-5" />
							</button>
							<button
								type="button"
								on:click={handleCameraCapture}
								class="p-2 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
								title={$i18n.t('Capture')}
							>
								<Camera className="w-5 h-5" />
							</button>
							<button
								type="button"
								on:click={() => webSearchEnabled = !webSearchEnabled}
								class="p-2 rounded-lg transition {webSearchEnabled 
									? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30' 
									: 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'}"
								title={$i18n.t('Web search')}
							>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
								</svg>
							</button>
						</div>
						<input
							type="text"
							name="message"
							placeholder={$i18n.t('Ask me anything...')}
							class="w-full px-6 py-4 pl-36 pr-24 text-lg rounded-2xl bg-white dark:bg-gray-850 border border-gray-200 dark:border-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 text-gray-900 dark:text-white placeholder-gray-400"
						/>
						<div class="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
							{#if $user?.role === 'admin' || ($user?.permissions?.chat?.call ?? true)}
								<Tooltip content={$i18n.t('Voice mode')}>
									<button
										type="button"
										on:click={handleVoiceMode}
										class="p-2 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 transition"
										title={$i18n.t('Voice mode')}
									>
										<Voice className="w-5 h-5" strokeWidth="2.5" />
									</button>
								</Tooltip>
							{/if}
							<button
								type="submit"
								class="p-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition"
							>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
								</svg>
							</button>
						</div>
					</div>
			</form>
		</div>

			<!-- Agents Section -->
			<div class="w-full">
			<div class="flex items-center justify-between mb-6">
			<h2 class="text-2xl font-semibold text-gray-800 dark:text-gray-200">{$i18n.t('Agents')}</h2>
			<a
				href="/workspace/agents"
				class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
			>
				{$i18n.t('View all')}
			</a>
		</div>

			{#if loading}
				<div class="flex justify-center py-16">
					<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
				</div>
			{:else if agents.length === 0}
				<div class="text-center py-16">
					<p class="text-gray-500 dark:text-gray-400 mb-4">{$i18n.t('No agents available yet.')}</p>
					<a
						href="/workspace/agents"
						class="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
					>
						{$i18n.t('Browse Agents')}
					</a>
				</div>
			{:else}
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
					{#each agents.slice(0, 11) as agent}
						<button
							on:click={() => selectAgent(agent.id)}
							class="flex flex-col p-5 bg-white dark:bg-gray-850 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:shadow-md transition text-left relative group"
						>
							<h3 class="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">
								{agent.name}
							</h3>
							<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-3 mb-3 flex-1">
								{agent?.meta?.description ?? agent?.info?.meta?.description ?? ''}
							</p>
							<div class="flex justify-end">
								<img
									src={agent?.meta?.profile_image_url ?? agent?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
									alt={agent.name}
									class="w-10 h-10 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-700"
								/>
							</div>
						</button>
					{/each}

					<!-- Create Agent Card -->
					<a
						href="/workspace/models/create"
						class="flex flex-col items-center justify-center gap-3 p-5 bg-gray-50 dark:bg-gray-800/50 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 transition"
					>
						<div class="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center">
							<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
							</svg>
						</div>
						<div class="text-sm font-medium text-blue-600 dark:text-blue-400">{$i18n.t('Create Agent')}</div>
					</a>
				</div>
			{/if}
	</div>

		<!-- Quick Actions (optional) -->
		<div class="mt-16 w-full">
			<h2 class="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4">{$i18n.t('Quick Actions')}</h2>
			<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
				<a
					href="/?new=true"
					class="flex items-center gap-3 p-4 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				>
					<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
					</svg>
					<div>
						<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('New Chat')}</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Start a conversation')}</div>
					</div>
				</a>

				<a
					href="/workspace/agents"
					class="flex items-center gap-3 p-4 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				>
					<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
					</svg>
					<div>
						<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Browse Agents')}</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Explore all agents')}</div>
					</div>
				</a>

				<a
					href="/workspace"
					class="flex items-center gap-3 p-4 bg-white dark:bg-gray-850 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition"
				>
					<svg class="w-5 h-5 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
					<div>
						<div class="font-medium text-gray-900 dark:text-gray-100">{$i18n.t('Workspace')}</div>
						<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Manage your settings')}</div>
					</div>
				</a>
			</div>
		</div>
		</div>
	</div>
</div>
