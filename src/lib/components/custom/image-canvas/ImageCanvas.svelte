<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { user } from '$lib/stores';
	import { getConfig, imageGenerations, imageEdits } from '$lib/apis/images';
	import Surface from './Surface.svelte';
	import {
		CANVAS_SIZE,
		emptyDocument,
		historyPush,
		placeImage,
		type CanvasItem,
		type CanvasResult
	} from './document';
	import { decodeImage, loadResult, readImage, resultUrl } from './assets';
	import { loadDraft, saveDraft } from './storage';

	const i18n: Writable<I18n> = getContext('i18n');
	// The playground wrapper mounts this component only for an authenticated admin.
	const owner = $user!.id;
	let items: CanvasItem[] = [];
	let results: CanvasResult[] = [];
	let prompt = '';
	let images = new Map<string, HTMLImageElement>();
	let selected = '';
	let tool: 'select' | 'draw' = 'select';
	let color = '#171717';
	let brushSize = 8;
	let past: CanvasItem[][] = [];
	let future: CanvasItem[][] = [];
	let ready = false;
	let busy = false;
	let running = false;
	let canGenerate = false;
	let canEdit = false;
	let configurationError = false;
	let error = '';
	let saveError = false;
	let surface: Surface;
	let fileInput: HTMLInputElement;
	let saveQueue = Promise.resolve();
	$: locked = !ready || busy || running;
	$: selection = items.find((item) => item.id === selected);
	$: if (ready) persist(items, results, prompt);

	function persist(
		currentItems: CanvasItem[],
		currentResults: CanvasResult[],
		currentPrompt: string
	) {
		const draft = {
			...emptyDocument(),
			items: currentItems,
			results: currentResults,
			prompt: currentPrompt
		};
		// Serialize writes so an earlier draft cannot overwrite a newer composition.
		saveQueue = saveQueue
			.then(() => saveDraft(owner, draft))
			.then(() => {
				saveError = false;
			})
			.catch(() => {
				saveError = true;
			});
	}
	function change(next: CanvasItem[]) {
		past = historyPush(past, items);
		future = [];
		items = next;
		if (!items.some((item) => item.id === selected)) selected = '';
	}
	function undo() {
		if (locked || !past.length) return;
		future = [...future, items];
		items = past[past.length - 1];
		past = past.slice(0, -1);
		selected = '';
	}
	function redo() {
		if (locked || !future.length) return;
		past = historyPush(past, items);
		items = future[future.length - 1];
		future = future.slice(0, -1);
		selected = '';
	}
	function remove() {
		if (!locked && selected) change(items.filter((item) => item.id !== selected));
	}
	function reorder(direction: number) {
		const index = items.findIndex((item) => item.id === selected);
		const next = [...items];
		if (index < 0 || index + direction < 0 || index + direction >= items.length) return;
		[next[index], next[index + direction]] = [next[index + direction], next[index]];
		change(next);
	}
	function resizeSelected(value: number) {
		if (!selection || !Number.isFinite(value) || value < 10 || value > 300) return;
		change(
			items.map((item) =>
				item.id === selected ? { ...item, scaleX: value / 100, scaleY: value / 100 } : item
			)
		);
	}
	async function cache(src: string) {
		const image = images.get(src) ?? (await decodeImage(src));
		images = new Map(images).set(src, image);
		return image;
	}
	async function upload(files: File[]) {
		if (locked || !files.length) return;
		busy = true;
		error = '';
		try {
			const additions: CanvasItem[] = [];
			for (const file of files) {
				const src = await readImage(file);
				const image = await cache(src);
				additions.push(
					placeImage(
						src,
						file.name,
						image.naturalWidth,
						image.naturalHeight,
						items.length + additions.length
					)
				);
			}
			change([...items, ...additions]);
			selected = additions[additions.length - 1].id;
			tool = 'select';
		} catch (cause) {
			error = String(cause instanceof Error ? cause.message : cause);
		} finally {
			busy = false;
			fileInput.value = '';
		}
	}
	async function addResult(result: CanvasResult, replace = false) {
		const src = await loadResult(result.url, localStorage.token);
		const image = await cache(src);
		const item = placeImage(
			src,
			result.prompt,
			image.naturalWidth,
			image.naturalHeight,
			replace ? 0 : items.length
		);
		change(replace ? [item] : [...items, item]);
		selected = item.id;
		tool = 'select';
	}
	async function reuseResult(result: CanvasResult) {
		if (locked) return;
		busy = true;
		error = '';
		try {
			await addResult(result);
		} catch (cause) {
			error = String(cause instanceof Error ? cause.message : cause);
		} finally {
			busy = false;
		}
	}
	async function generate(mode: 'text' | 'canvas') {
		if (locked || !prompt.trim() || (mode === 'canvas' ? !canEdit || !items.length : !canGenerate))
			return;
		const requestPrompt = prompt.trim();
		running = true;
		error = '';
		try {
			const response: { url: string }[] =
				mode === 'canvas'
					? await imageEdits(localStorage.token, surface.exportPng(), requestPrompt)
					: await imageGenerations(localStorage.token, requestPrompt);
			if (
				!Array.isArray(response) ||
				!response.length ||
				response.some((image) => typeof image?.url !== 'string')
			)
				throw new Error('The image backend returned no images.');
			const generated = response.map((image) => ({
				id: crypto.randomUUID(),
				url: resultUrl(image.url),
				prompt: requestPrompt,
				mode
			}));
			results = [...generated, ...results];
			await addResult(generated[0], true);
		} catch (cause) {
			error = String(cause instanceof Error ? cause.message : cause);
		} finally {
			running = false;
		}
	}
	function download() {
		try {
			const link = document.createElement('a');
			link.href = surface.exportPng();
			link.download = 'image-canvas.png';
			link.click();
		} catch {
			error = 'Unable to export the canvas.';
		}
	}
	function shortcuts(event: KeyboardEvent) {
		const target = event.target as HTMLElement;
		if (
			['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) ||
			target.isContentEditable ||
			locked
		)
			return;
		if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z') {
			event.preventDefault();
			if (event.shiftKey) redo();
			else undo();
		} else if (event.key === 'Delete' || event.key === 'Backspace') {
			event.preventDefault();
			remove();
		}
	}
	async function configure() {
		configurationError = false;
		try {
			const config = await getConfig(localStorage.token);
			canGenerate = !!config.ENABLE_IMAGE_GENERATION;
			canEdit = !!config.ENABLE_IMAGE_EDIT;
		} catch {
			configurationError = true;
		}
	}
	onMount(() => {
		void configure();
		void (async () => {
			try {
				const draft = await loadDraft(owner);
				if (draft) {
					await Promise.all(
						draft.items.filter((item) => item.kind === 'image').map((item) => cache(item.src))
					);
					items = draft.items;
					results = draft.results;
					prompt = draft.prompt;
				}
			} catch {
				error = 'Unable to restore the canvas draft.';
			} finally {
				ready = true;
			}
		})();
	});
</script>

<svelte:window on:keydown={shortcuts} />

<div class="canvas-workspace">
	<div class="flex flex-wrap items-center gap-2">
		<div class="mr-auto">
			<h1 class="text-lg font-semibold">{$i18n.t('Image canvas')}</h1>
			<p class="text-xs text-gray-500">{$i18n.t('Compose images, draw an idea, then generate.')}</p>
		</div>
		<span class="text-xs text-gray-500" aria-live="polite"
			>{ready ? $i18n.t('Draft stored in this browser') : $i18n.t('Loading...')}</span
		>
		<button class="control" disabled={locked || !items.length} on:click={download}
			>{$i18n.t('Download PNG')}</button
		>
	</div>
	{#if saveError}<p role="alert" class="text-sm text-amber-600">
			{$i18n.t('Draft could not be saved. Download your canvas before leaving.')}
		</p>{/if}
	{#if error}<p role="alert" class="text-sm text-red-600">{$i18n.t(error)}</p>{/if}
	<div
		class="toolbar flex flex-wrap items-center gap-2"
		role="group"
		aria-label={$i18n.t('Canvas tools')}
	>
		<input
			type="file"
			accept="image/png,image/jpeg,image/webp,image/gif,image/avif"
			multiple
			class="hidden"
			bind:this={fileInput}
			on:change={() => upload(Array.from(fileInput.files ?? []))}
		/>
		<button class="control" disabled={locked} on:click={() => fileInput.click()}
			>{$i18n.t('Add images')}</button
		>
		<button
			class="control"
			aria-pressed={tool === 'select'}
			disabled={locked}
			on:click={() => (tool = 'select')}>{$i18n.t('Select')}</button
		>
		<button
			class="control"
			aria-pressed={tool === 'draw'}
			disabled={locked}
			on:click={() => {
				tool = 'draw';
				selected = '';
			}}>{$i18n.t('Draw')}</button
		>
		<label class="flex items-center gap-1 text-xs"
			>{$i18n.t('Colour')}<input
				aria-label={$i18n.t('Brush colour')}
				type="color"
				bind:value={color}
				disabled={locked}
			/></label
		>
		<label class="flex items-center gap-1 text-xs"
			>{$i18n.t('Brush')}<input
				class="w-20"
				aria-label={$i18n.t('Brush size')}
				type="range"
				min="1"
				max="60"
				bind:value={brushSize}
				disabled={locked}
			/></label
		>
		<button class="control" disabled={locked || !past.length} on:click={undo}
			>{$i18n.t('Undo')}</button
		>
		<button class="control" disabled={locked || !future.length} on:click={redo}
			>{$i18n.t('Redo')}</button
		>
		<button class="control" disabled={locked || !items.length} on:click={() => change([])}
			>{$i18n.t('Clear canvas')}</button
		>
	</div>
	<div class="editor-grid">
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="canvas-area"
			on:dragover|preventDefault
			on:drop|preventDefault={(event) => upload(Array.from(event.dataTransfer?.files ?? []))}
		>
			<Surface
				bind:this={surface}
				{items}
				{images}
				bind:selected
				{tool}
				{color}
				{brushSize}
				disabled={locked}
				onchange={change}
			/>
		</div>
		<aside class="layers" aria-label={$i18n.t('Canvas layers')}>
			<h2 class="mb-2 text-sm font-semibold">
				{$i18n.t('Layers')} <span class="text-gray-500">({items.length})</span>
			</h2>
			{#if !items.length}<p class="text-xs text-gray-500">
					{$i18n.t(
						'Add images or draw on the white canvas. You can also start with a text prompt.'
					)}
				</p>{/if}
			<div class="layer-list">
				{#each [...items].reverse() as item (item.id)}
					<button
						class="control block w-full truncate text-left"
						aria-pressed={selected === item.id}
						disabled={locked}
						on:click={() => {
							selected = item.id;
							tool = 'select';
						}}
						title={item.kind === 'image' ? item.name : $i18n.t('Drawing')}
					>
						{item.kind === 'image' ? item.name : $i18n.t('Drawing')}
					</button>
				{/each}
			</div>
			{#if selection}
				<div class="mt-3 flex flex-wrap gap-1">
					<button
						class="control"
						disabled={locked || items[items.length - 1].id === selected}
						on:click={() => reorder(1)}>{$i18n.t('Forward')}</button
					>
					<button
						class="control"
						disabled={locked || items[0].id === selected}
						on:click={() => reorder(-1)}>{$i18n.t('Backward')}</button
					>
					<button class="control" disabled={locked} on:click={remove}>{$i18n.t('Remove')}</button>
				</div>
				<label class="mt-3 flex items-center gap-2 text-xs"
					>{$i18n.t('Scale (%)')}<input
						class="w-16 rounded border bg-transparent p-1"
						type="number"
						min="10"
						max="300"
						value={Math.round(selection.scaleX * 100)}
						disabled={locked}
						on:change={(event) => resizeSelected(Number(event.currentTarget.value))}
					/></label
				>
			{/if}
			<p class="mt-3 text-xs text-gray-500">
				{$i18n.t(
					'Drag to move. Use corner handles to resize. Only content inside the white square is sent.'
				)}
			</p>
			<p class="mt-2 text-xs text-gray-500">{CANVAS_SIZE} × {CANVAS_SIZE} PNG</p>
		</aside>
	</div>
	<div class="rounded-xl border border-gray-200 p-3 dark:border-gray-800">
		<label for="canvas-prompt" class="text-sm font-medium">{$i18n.t('Prompt')}</label>
		<textarea
			id="canvas-prompt"
			class="mt-1 w-full resize-y bg-transparent text-sm outline-hidden"
			rows="2"
			bind:value={prompt}
			placeholder={$i18n.t('Describe the image or how to transform your canvas...')}
			disabled={locked}
		></textarea>
		<div class="flex flex-wrap items-center gap-2">
			<p class="mr-auto max-w-xl text-xs text-gray-500">
				{$i18n.t(
					'Canvas generation combines all images and drawing into one image. Results open on the canvas; Undo restores your composition.'
				)}
			</p>
			<button
				class="control"
				disabled={locked || !canGenerate || !prompt.trim()}
				on:click={() => generate('text')}>{$i18n.t('Generate from text')}</button
			>
			<button
				class="control primary"
				disabled={locked || !canEdit || !items.length || !prompt.trim()}
				on:click={() => generate('canvas')}>{$i18n.t('Generate from canvas')}</button
			>
		</div>
		{#if running}<p class="mt-2 text-sm" role="status">{$i18n.t('Generating image...')}</p>{/if}
		{#if configurationError}<p class="mt-2 text-xs text-red-600">
				{$i18n.t('Unable to load image settings.')}
				<button class="underline" on:click={configure}>{$i18n.t('Retry')}</button>
			</p>
		{:else if !canGenerate || !canEdit}<p class="mt-2 text-xs text-gray-500">
				{$i18n.t(
					'Enable image generation and image editing in Admin Settings → Images to use both generation modes.'
				)}
			</p>{/if}
	</div>
	{#if results.length}
		<section aria-label={$i18n.t('Generated images')}>
			<h2 class="mb-2 text-sm font-semibold">{$i18n.t('Results')}</h2>
			<div class="flex gap-3 overflow-x-auto pb-2">
				{#each results as result (result.id)}
					<article class="w-36 shrink-0 rounded-xl border border-gray-200 p-2 dark:border-gray-800">
						<img
							src={result.url}
							alt={result.prompt}
							class="aspect-square w-full rounded-lg object-contain"
							loading="lazy"
						/>
						<p class="my-1 truncate text-xs" title={result.prompt}>{result.prompt}</p>
						<button class="control w-full" disabled={locked} on:click={() => reuseResult(result)}
							>{$i18n.t('Add to canvas')}</button
						>
						<a
							class="mt-1 block text-center text-xs underline"
							href={`${result.url}?attachment=true`}
							download
							target="_blank"
							rel="noopener noreferrer">{$i18n.t('Download')}</a
						>
					</article>
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	.canvas-workspace {
		padding: 12px 16px 24px;
		display: flex;
		flex-direction: column;
		gap: 12px;
		min-height: 100%;
	}
	.editor-grid {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 190px;
		gap: 12px;
	}
	.canvas-area {
		height: clamp(320px, 56vh, 720px);
		min-width: 0;
	}
	.layers {
		padding: 12px;
		border: 1px solid #8883;
		border-radius: 12px;
		min-width: 0;
	}
	.layer-list {
		display: flex;
		flex-direction: column;
		gap: 4px;
		max-height: 240px;
		overflow-y: auto;
	}
	.control {
		border: 1px solid #8884;
		border-radius: 8px;
		padding: 6px 10px;
		font-size: 12px;
		transition: background 0.15s;
	}
	.control:hover:not(:disabled) {
		background: #8882;
	}
	.control[aria-pressed='true'] {
		border-color: #6366f1;
		background: #6366f122;
	}
	.control:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.primary {
		background: #4f46e5;
		border-color: #4f46e5;
		color: white;
	}
	.primary:hover:not(:disabled) {
		background: #4338ca;
	}
	@media (max-width: 700px) {
		.editor-grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.canvas-area {
			height: 380px;
		}
		.layer-list {
			max-height: 100px;
		}
	}
</style>
