<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { user, models, showSidebar, mobile } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getModelItems as getWorkspaceModels } from '$lib/apis/models';
	import { getFunctions } from '$lib/apis/functions';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import QuickActions from './QuickActions.svelte';
	import {
		classifyWelcomeCatalogue,
		hasPendingWelcomeFileOperations,
		orderWelcomeAgents
	} from './catalogue';

	const i18n: Writable<i18nType> = getContext('i18n');

	let agents: any[] = [];
	let orderedAgents: any[] = [];
	let loading = false;
	let draggedIndex: number | null = null;
	let dragOverIndex: number | null = null;
	let longPressTimer: ReturnType<typeof setTimeout> | null = null;
	let isDragging = false;
	let scrollContainer: HTMLDivElement;
	export let files: any[] = [];

	const storeFilesForTransfer = (): boolean => {
		if (hasPendingWelcomeFileOperations(files)) {
			toast.error($i18n.t('Please wait until all files are uploaded.'));
			return false;
		}

		if (files.length > 0) {
			try {
				sessionStorage.setItem('welcome-files', JSON.stringify(files));
			} catch (error) {
				console.error('Failed to store files in sessionStorage:', error);
				toast.error($i18n.t('Files are too large to transfer'));
				return false;
			}
		}
		return true;
	};

	const AGENT_ORDER_KEY = 'welcome-agent-order';

	const loadWorkspaceModels = async (): Promise<any[]> => {
		const items: any[] = [];
		for (let page = 1; ; page += 1) {
			const response = await getWorkspaceModels(localStorage.token, '', '', '', '', '', page);
			const pageItems = response?.items ?? [];
			items.push(...pageItems);
			if (items.length >= (response?.total ?? 0) || pageItems.length === 0) return items;
		}
	};

	const applyStoredOrder = (agentList: any[]): any[] => {
		try {
			const storedOrder = localStorage.getItem(AGENT_ORDER_KEY);
			if (storedOrder) {
				const orderIds: string[] = JSON.parse(storedOrder);
				return orderWelcomeAgents(agentList, orderIds);
			}
		} catch (error) {
			console.error('Failed to load agent order:', error);
		}
		return agentList;
	};

	const saveAgentOrder = () => {
		try {
			const orderIds = orderedAgents.map((a) => a.id);
			localStorage.setItem(AGENT_ORDER_KEY, JSON.stringify(orderIds));
		} catch (error) {
			console.error('Failed to save agent order:', error);
		}
	};

	const handleDragStart = (index: number) => {
		draggedIndex = index;
		isDragging = true;
	};

	const handleDragOver = (index: number) => {
		if (draggedIndex !== null && draggedIndex !== index) {
			// Dynamically reorder the list as user drags
			const newOrder = [...orderedAgents];
			const [removed] = newOrder.splice(draggedIndex, 1);
			newOrder.splice(index, 0, removed);
			orderedAgents = newOrder;
			draggedIndex = index; // Update dragged index to new position
			dragOverIndex = null;
		}
	};

	const handleDragEnd = () => {
		if (isDragging) {
			// Save the new order (reordering already happened dynamically)
			saveAgentOrder();
		}
		draggedIndex = null;
		dragOverIndex = null;
		isDragging = false;
	};

	const handleTouchStart = (index: number, event: TouchEvent) => {
		longPressTimer = setTimeout(() => {
			handleDragStart(index);
			// Vibrate for haptic feedback if supported
			if (navigator.vibrate) {
				navigator.vibrate(50);
			}
		}, 500); // 500ms long press
	};

	const handleTouchMove = (event: TouchEvent) => {
		if (!isDragging) {
			// Cancel long press if user moves before drag starts
			if (longPressTimer) {
				clearTimeout(longPressTimer);
				longPressTimer = null;
			}
			return;
		}

		event.preventDefault();
		const touch = event.touches[0];

		// Auto-scroll when near edges of scroll container
		if (scrollContainer) {
			const rect = scrollContainer.getBoundingClientRect();
			const scrollThreshold = 50; // pixels from edge to trigger scroll
			const scrollSpeed = 8; // pixels per frame

			if (touch.clientY < rect.top + scrollThreshold) {
				// Near top - scroll up
				scrollContainer.scrollTop -= scrollSpeed;
			} else if (touch.clientY > rect.bottom - scrollThreshold) {
				// Near bottom - scroll down
				scrollContainer.scrollTop += scrollSpeed;
			}
		}

		const elements = document.elementsFromPoint(touch.clientX, touch.clientY);
		const agentButton = elements.find((el) => el.hasAttribute('data-agent-index'));
		if (agentButton) {
			const index = parseInt(agentButton.getAttribute('data-agent-index') || '-1');
			if (index >= 0) {
				handleDragOver(index);
			}
		}
	};

	const handleTouchEnd = () => {
		if (longPressTimer) {
			clearTimeout(longPressTimer);
			longPressTimer = null;
		}
		if (isDragging) {
			handleDragEnd();
		}
	};

	onMount(async () => {
		loading = true;
		try {
			const [workspaceModelsData, functionsData] = await Promise.all([
				loadWorkspaceModels(),
				getFunctions(localStorage.token)
			]);

			agents = classifyWelcomeCatalogue(
				$models,
				workspaceModelsData || [],
				functionsData || []
			).agents;

			// Apply stored order from localStorage
			orderedAgents = applyStoredOrder(agents);
		} catch (error) {
			console.error('Error loading agents:', error);
		} finally {
			loading = false;
		}
	});

	const selectAgent = (agentId: string) => {
		if (!storeFilesForTransfer()) return;
		goto(`/?models=${encodeURIComponent(agentId)}`);
	};
</script>

<div class="h-full min-h-0 w-full flex flex-col">
	<!-- Top Navigation Bar -->
	<nav class="sticky top-0 z-30 w-full shrink-0 py-1 pl-1.5 pr-1">
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
					<UserMenu className="max-w-[240px]" role={$user?.role} help={true}>
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

	<!-- Mobile content scrolls above the composer; desktop keeps the composer below the greeting. -->
	<div class="flex-1 min-h-0 overflow-hidden md:overflow-y-auto md:px-12 lg:px-20 md:pb-8">
		<div class="max-w-6xl mx-auto w-full h-full md:h-auto flex flex-col">
			<div
				data-testid="welcome-content"
				class="min-h-0 flex-1 overflow-y-auto px-4 pt-8 pb-4 md:contents"
			>
				<!-- Greeting -->
				<!-- Keep the desktop composer near the New Chat starting position as the viewport grows. -->
				<div
					class="mb-6 md:mb-8 mt-2 md:mt-0 md:order-1 md:flex md:min-h-[calc(50dvh-10rem)] md:items-end"
				>
					<h1
						style="font-size: clamp(2rem, 6vw, 5.5rem); line-height: 1.1; font-family: 'Public Sans', sans-serif;"
						class="font-semibold mb-1 text-gray-900 dark:text-white"
					>
						<span class="text-blue-600 dark:text-blue-400"
							>{$i18n.t('Hello, {{name}}', { name: $user?.name || $i18n.t('User') })}</span
						>
					</h1>
				</div>

				<QuickActions />

				<!-- Agents Section -->
				<div class="w-full md:order-4">
					<div class="flex items-center justify-between mb-6">
						<h2 class="text-2xl font-semibold text-gray-800 dark:text-gray-200">
							{$i18n.t('Agents')}
						</h2>
						<a
							href="/workspace/models"
							class="hidden md:block text-sm text-blue-600 dark:text-blue-400 hover:underline"
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
							<p class="text-gray-500 dark:text-gray-400 mb-4">
								{$i18n.t('No agents available yet.')}
							</p>
							<a
								href="/workspace/models"
								class="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
							>
								{$i18n.t('Browse Agents')}
							</a>
						</div>
					{:else}
						<!-- Mobile: Constrained vertical scroll area with drag reorder -->
						<div class="md:hidden flex flex-col">
							<div
								bind:this={scrollContainer}
								class="overflow-y-auto max-h-[240px] space-y-2 scrollbar-none"
								on:touchmove={handleTouchMove}
								on:touchend={handleTouchEnd}
							>
								{#each orderedAgents as agent, index (agent.id)}
									<button
										data-agent-index={index}
										on:click={() => !isDragging && selectAgent(agent.id)}
										on:touchstart={(e) => handleTouchStart(index, e)}
										class="w-full flex items-center gap-2.5 p-2.5 rounded-xl border transition-all duration-150 text-left touch-manipulation
									{draggedIndex === index
											? 'bg-blue-100 dark:bg-blue-900/30 border-blue-500 border-2 shadow-lg scale-[1.02]'
											: 'bg-white dark:bg-gray-850 border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'}
									{!isDragging ? 'active:scale-[0.98]' : ''}"
									>
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(agent.id)}&lang=${$i18n.language}`}
											alt={agent.name}
											on:error={(e) => {
												if (e.currentTarget.getAttribute('src') !== '/favicon.png') {
													e.currentTarget.src = '/favicon.png';
												}
											}}
											class="w-10 h-10 rounded-full object-cover ring-2 ring-gray-100 dark:ring-gray-700 flex-shrink-0 pointer-events-none"
										/>
										<div class="min-w-0 flex-1 pointer-events-none">
											<h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
												{agent.name}
											</h3>
											<p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
												{agent?.meta?.description ?? agent?.info?.meta?.description ?? ''}
											</p>
										</div>
										<svg
											class="w-4 h-4 text-gray-400 flex-shrink-0 pointer-events-none"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M9 5l7 7-7 7"
											/>
										</svg>
									</button>
								{/each}
								<!-- Create Agent Card - Mobile -->
								<a
									href="/workspace/models/create"
									class="w-full flex items-center justify-center gap-2 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-600 hover:border-blue-400 dark:hover:border-blue-500 active:scale-[0.98] transition"
								>
									<div class="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
										<svg
											class="w-4 h-4 text-white"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 4v16m8-8H4"
											/>
										</svg>
									</div>
									<span class="text-sm font-medium text-blue-600 dark:text-blue-400"
										>{$i18n.t('Create Agent')}</span
									>
								</a>
							</div>
						</div>

						<!-- Desktop/Tablet: Grid layout with scroll -->
						<div
							class="hidden md:block overflow-y-auto scrollbar-none"
							style="max-height: calc(3 * 72px + 2 * 12px);"
						>
							<div class="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 auto-rows-min">
								{#each orderedAgents as agent, index (agent.id)}
									<button
										data-agent-index={index}
										draggable="true"
										on:click={() => !isDragging && selectAgent(agent.id)}
										on:dragstart={(e) => {
											handleDragStart(index);
											e.dataTransfer?.setData('text/plain', index.toString());
										}}
										on:dragover={(e) => {
											e.preventDefault();
											handleDragOver(index);
										}}
										on:dragend={handleDragEnd}
										class="flex items-center gap-3 p-3 h-[72px] bg-white dark:bg-gray-850 rounded-lg border transition-all duration-150 text-left group cursor-grab active:cursor-grabbing
								{draggedIndex === index
											? 'opacity-50 scale-95 border-blue-500 border-2'
											: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-600 hover:shadow-sm'}"
									>
										<img
											src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(agent.id)}&lang=${$i18n.language}`}
											alt={agent.name}
											on:error={(e) => {
												if (e.currentTarget.getAttribute('src') !== '/favicon.png') {
													e.currentTarget.src = '/favicon.png';
												}
											}}
											class="w-9 h-9 rounded-full object-cover ring-1 ring-gray-200 dark:ring-gray-700 flex-shrink-0"
										/>
										<div class="min-w-0 flex-1">
											<h3
												class="text-sm font-semibold text-gray-900 dark:text-gray-100 line-clamp-1"
											>
												{agent.name}
											</h3>
											<p
												class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 leading-relaxed"
											>
												{agent?.meta?.description ?? agent?.info?.meta?.description ?? ''}
											</p>
										</div>
									</button>
								{/each}

								<!-- Create Agent Card - Desktop -->
								<a
									href="/workspace/models/create"
									class="flex items-center gap-3 p-3 h-[72px] bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-dashed border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-800 hover:border-blue-400 dark:hover:border-blue-500 transition-all duration-150"
								>
									<div
										class="w-9 h-9 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0"
									>
										<svg
											class="w-4 h-4 text-white"
											fill="none"
											stroke="currentColor"
											viewBox="0 0 24 24"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												stroke-width="2"
												d="M12 4v16m8-8H4"
											/>
										</svg>
									</div>
									<div class="min-w-0 flex-1">
										<div class="text-sm font-semibold text-blue-600 dark:text-blue-400">
											{$i18n.t('Create Agent')}
										</div>
										<p class="text-xs text-gray-500 dark:text-gray-400">Add a new agent</p>
									</div>
								</a>
							</div>
						</div>
					{/if}
				</div>
			</div>
			<!-- Keep one native composer mounted across breakpoints, including its draft and uploads. -->
			<div
				data-testid="welcome-composer"
				class="w-full shrink-0 px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:order-2 md:mb-8 md:px-0 md:py-0"
			>
				<slot />
			</div>
		</div>
	</div>
</div>
