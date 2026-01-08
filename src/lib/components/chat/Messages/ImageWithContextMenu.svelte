<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	import { fade } from 'svelte/transition';
	
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let src: string;
	export let alt: string = '';
	export let messageId: string;
	export let model: any = null;
	export let disabled: boolean = false;

	let imageElement: HTMLImageElement;
	let imageWrapper: HTMLDivElement;
	let showContextMenu = false;
	let showInput = false;
	let clickX = 0;
	let clickY = 0;
	let normalizedX = 0;
	let normalizedY = 0;
	let menuX = 0;
	let menuY = 0;
	let brushRadius = 25;
	let currentAction: string | null = null;
	let inputValue = '';
	let inputElement: HTMLInputElement;

	const IMAGE_ACTIONS = [
		{
			id: 'add',
			label: $i18n.t('Add New Element'),
			icon: 'plus',
			needsInput: true,
			inputPlaceholder: 'Add what...',
			prompt: (coords: any, input: string) =>
				`Add ${input} at position (${coords.normalizedX}, ${coords.normalizedY}). Make it fit naturally with the lighting, perspective, and style of the image.`
		},
		{
			id: 'remove',
			label: $i18n.t('Remove This'),
			icon: 'trash',
			needsInput: false,
			prompt: (coords: any, input: string) =>
				`Edit this image: Remove the object at position (${coords.normalizedX}, ${coords.normalizedY}). Fill in that area naturally to blend with the surroundings. Keep everything else unchanged.`
		},
		{
			id: 'replace',
			label: $i18n.t('Replace This'),
			icon: 'replace',
			needsInput: true,
			inputPlaceholder: 'Replace with...',
			prompt: (coords: any, input: string) =>
				`Edit this image: At position (${coords.normalizedX}, ${coords.normalizedY}), replace the object there with ${input}. Match the lighting and perspective. Keep everything else the same.`
		},
		{
			id: 'change_color',
			label: $i18n.t('Change Color'),
			icon: 'palette',
			needsInput: true,
			inputPlaceholder: 'Change color to...',
			prompt: (coords: any, input: string) =>
				`Edit this image: Change the color of the object at position (${coords.normalizedX}, ${coords.normalizedY}) to ${input}. Only change the color, keep all other details, texture, and lighting the same.`
		},
		{
			id: 'describe',
			label: $i18n.t('Describe This Area'),
			icon: 'eye',
			needsInput: false,
			prompt: (coords: any, input: string) =>
				`What do you see at position (${coords.normalizedX}, ${coords.normalizedY}) in this image? Describe the object, its color, texture, and surrounding context.`
		},
		{
			id: 'enhance',
			label: $i18n.t('Enhance Quality'),
			icon: 'zoom',
			needsInput: false,
			prompt: (coords: any, input: string) =>
				`Edit this image: Enhance the quality and detail of the entire image. Improve sharpness and clarity while preserving the composition and content.`
		},
		{
			id: 'fullscreen',
			label: $i18n.t('View Full Screen'),
			icon: 'fullscreen',
			needsInput: false,
			isViewAction: true
		}
	];

	const handleImageClick = (e: MouseEvent) => {
		if (disabled) return;

		e.preventDefault();
		e.stopPropagation();

		const rect = imageElement.getBoundingClientRect();
		
		// Get the click position relative to the displayed image
		clickX = e.clientX - rect.left;
		clickY = e.clientY - rect.top;
		
		// Calculate normalized coordinates (0-1) based on displayed size
		// These should work correctly with the image generation model
		normalizedX = parseFloat((clickX / rect.width).toFixed(4));
		normalizedY = parseFloat((clickY / rect.height).toFixed(4));
		
		// Clamp values to 0-1 range in case of edge cases
		normalizedX = Math.max(0, Math.min(1, normalizedX));
		normalizedY = Math.max(0, Math.min(1, normalizedY));

		// Position menu
		menuX = e.clientX - rect.left + 10;
		menuY = e.clientY - rect.top;

		showContextMenu = true;
		showInput = false;
	};

	const handleActionClick = (action: any) => {
		currentAction = action;
		showContextMenu = false;

		if (action.id === 'fullscreen') {
			openFullscreen();
		} else if (action.needsInput) {
			showInput = true;
			setTimeout(() => inputElement?.focus(), 100);
		} else {
			executeAction(action);
		}
	};

	const openFullscreen = () => {
		const overlay = document.createElement('div');
		overlay.className = 'fixed inset-0 z-[9999] bg-black/90 flex items-center justify-center p-4';
		overlay.style.backdropFilter = 'blur(4px)';
		
		const img = document.createElement('img');
		img.src = src;
		img.alt = alt;
		img.className = 'max-w-full max-h-full object-contain';
		
		const closeButton = document.createElement('button');
		closeButton.innerHTML = `
			<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
			</svg>
		`;
		closeButton.className = 'absolute top-4 right-4 w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 text-white flex items-center justify-center transition';
		
		const closeOverlay = () => {
			overlay.remove();
			document.body.style.overflow = '';
		};
		
		closeButton.addEventListener('click', closeOverlay);
		overlay.addEventListener('click', (e) => {
			if (e.target === overlay) closeOverlay();
		});
		document.addEventListener('keydown', function escHandler(e) {
			if (e.key === 'Escape') {
				closeOverlay();
				document.removeEventListener('keydown', escHandler);
			}
		});
		
		overlay.appendChild(img);
		overlay.appendChild(closeButton);
		document.body.appendChild(overlay);
		document.body.style.overflow = 'hidden';
	};

	const executeAction = async (action: any) => {
		const coords = { normalizedX, normalizedY };
		const prompt = action.prompt(coords, inputValue);

		// Dispatch event to parent with the edit request
		dispatch('edit', {
			action: action.id,
			coords,
			prompt,
			imageUrl: src,
			brushRadius
		});

		// Reset state
		inputValue = '';
		showInput = false;
		showContextMenu = false;
	};

	const handleInputSubmit = () => {
		if (currentAction && inputValue.trim()) {
			executeAction(currentAction);
		}
	};

	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Enter') {
			handleInputSubmit();
		} else if (e.key === 'Escape') {
			showInput = false;
			showContextMenu = false;
			inputValue = '';
		}
	};

	const handleOutsideClick = (e: MouseEvent) => {
		if (imageWrapper && !imageWrapper.contains(e.target as Node)) {
			showContextMenu = false;
			showInput = false;
		}
	};

	// Icon helper
	const getIcon = (iconName: string) => {
		const icons: Record<string, string> = {
			plus: 'M12 4v16m8-8H4',
			trash: 'M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16',
			replace: 'M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4',
			palette: 'M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01',
			eye: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z',
			zoom: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7',
			fullscreen: 'M4 8V4m0 0h4M4 4l5 5m11-5v4m0-4h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4'
		};
		return icons[iconName] || icons.eye;
	};
</script>

<svelte:window on:click={handleOutsideClick} />

<div bind:this={imageWrapper} class="relative inline-block">
	<img
		bind:this={imageElement}
		{src}
		{alt}
		class="rounded-lg cursor-crosshair max-h-96"
		on:click={handleImageClick}
		on:contextmenu|preventDefault={handleImageClick}
	/>

	<!-- Click marker -->
	{#if showContextMenu || showInput}
		<div
			class="absolute w-5 h-5 border-2 border-red-500 rounded-full pointer-events-none animate-pulse"
			style="left: {clickX}px; top: {clickY}px; transform: translate(-50%, -50%);"
			transition:fade={{ duration: 150 }}
		/>

		<!-- Selection circle -->
		<div
			class="absolute border-2 border-dashed border-blue-500 rounded-full pointer-events-none bg-blue-500/10"
			style="left: {clickX - brushRadius}px; top: {clickY - brushRadius}px; width: {brushRadius *
				2}px; height: {brushRadius * 2}px;"
			transition:fade={{ duration: 150 }}
		/>
	{/if}

	<!-- Context Menu -->
	{#if showContextMenu}
		<div
			class="absolute bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 p-2 min-w-[200px] z-50"
			style="left: {menuX}px; top: {menuY}px;"
			transition:fade={{ duration: 150 }}
		>
			{#each IMAGE_ACTIONS as action, idx}
				<button
					type="button"
					class="flex items-center gap-3 w-full px-3 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
					on:click={() => handleActionClick(action)}
				>
					<svg
						class="w-5 h-5 flex-shrink-0"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getIcon(action.icon)} />
					</svg>
					<span>{action.label}</span>
				</button>
				{#if idx === 3 || idx === 5}
					<div class="h-px bg-gray-200 dark:bg-gray-700 my-1" />
				{/if}
			{/each}
		</div>
	{/if}

	<!-- Input Overlay -->
	{#if showInput && currentAction}
		<div
			class="absolute bg-white dark:bg-gray-800 rounded-full shadow-xl border border-gray-200 dark:border-gray-700 px-4 py-2 flex items-center gap-2 min-w-[300px] z-50"
			style="left: {menuX}px; top: {menuY + 40}px;"
			transition:fade={{ duration: 150 }}
		>
			<input
				bind:this={inputElement}
				bind:value={inputValue}
				type="text"
				placeholder={currentAction.inputPlaceholder || 'Enter value...'}
				class="flex-1 bg-transparent border-none outline-none text-sm dark:text-gray-100"
				on:keydown={handleKeydown}
			/>
			<button
				type="button"
				class="w-8 h-8 rounded-full bg-blue-500 hover:bg-blue-600 text-white flex items-center justify-center transition"
				on:click={handleInputSubmit}
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 16 16">
					<path
						d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
					/>
				</svg>
			</button>
		</div>
	{/if}
</div>

<style>
	@keyframes pulse {
		0%,
		100% {
			opacity: 1;
			transform: translate(-50%, -50%) scale(1);
		}
		50% {
			opacity: 0.5;
			transform: translate(-50%, -50%) scale(1.2);
		}
	}

	.animate-pulse {
		animation: pulse 1.5s ease-in-out infinite;
	}
</style>
