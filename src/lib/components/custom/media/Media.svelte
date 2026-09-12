<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as I18n } from 'i18next';
	import { toast } from 'svelte-sonner';
	import { WEBUI_NAME, mobile, showSidebar } from '$lib/stores';
	import { deleteFileById } from '$lib/apis/files';
	import Modal from '$lib/components/common/Modal.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Sidebar from '$lib/components/icons/Sidebar.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import {
		getFilePage,
		mediaKind,
		fileName,
		contentUrl,
		type MediaFile,
		type MediaKind
	} from './api';

	const i18n: Writable<I18n> = getContext('i18n');
	const controller = new AbortController();
	let files: MediaFile[] = [];
	let nextPage = 1;
	let scanned = 0;
	let total = 0;
	let exhausted = false;
	let loading = false;
	let error = false;
	let query = '';
	let kind: MediaKind | 'all' = 'all';
	let preview: MediaFile | null = null;
	let previewOpen = false;
	let pendingDelete: MediaFile | null = null;
	let confirmDelete = false;
	let deleting = false;

	$: visible = files.filter(
		(file) =>
			(kind === 'all' || mediaKind(file) === kind) &&
			fileName(file).toLowerCase().includes(query.trim().toLowerCase())
	);
	$: hasMore = !exhausted && (nextPage === 1 || scanned < total);

	async function loadMore(reset = false) {
		if (loading) return;
		loading = true;
		error = false;
		if (reset) {
			files = [];
			nextPage = 1;
			scanned = 0;
			total = 0;
			exhausted = false;
		}
		try {
			const result = await getFilePage(localStorage.token, nextPage, controller.signal);
			if (controller.signal.aborted) return;
			total = result.total;
			scanned += result.items.length;
			exhausted = result.items.length === 0;
			const merged = new Map(files.map((file) => [file.id, file]));
			for (const file of result.items) if (mediaKind(file)) merged.set(file.id, file);
			files = [...merged.values()];
			nextPage += 1;
		} catch {
			if (!controller.signal.aborted) error = true;
		} finally {
			loading = false;
		}
	}

	async function removeFile() {
		if (!pendingDelete || deleting) return;
		deleting = true;
		try {
			const result = await deleteFileById(localStorage.token, pendingDelete.id);
			if (!result) throw new Error('File deletion failed');
			previewOpen = false;
			// Deletion shifts the upstream page offsets. Restart instead of skipping a file.
			await loadMore(true);
		} catch {
			toast.error($i18n.t('Error deleting file'));
		} finally {
			deleting = false;
			pendingDelete = null;
		}
	}

	onMount(() => {
		void loadMore();
	});
	onDestroy(() => controller.abort());
</script>

<svelte:head><title>{$i18n.t('Media')} • {$WEBUI_NAME}</title></svelte:head>

<div
	class="flex h-screen max-h-[100dvh] w-full min-w-0 flex-col {$showSidebar
		? 'md:max-w-[calc(100%-var(--sidebar-width))]'
		: ''}"
>
	<header class="flex items-center gap-2 px-4 py-3">
		{#if $mobile && !$showSidebar}
			<button
				class="rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-850"
				aria-label={$i18n.t('Open Sidebar')}
				on:click={() => showSidebar.set(true)}><Sidebar /></button
			>
		{/if}
		<h1 class="text-xl font-semibold">{$i18n.t('Media')}</h1>
		<button
			class="ml-auto rounded-lg px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-850 disabled:opacity-50"
			disabled={loading || deleting}
			on:click={() => loadMore(true)}>{$i18n.t('Refresh')}</button
		>
	</header>
	<div class="flex-1 overflow-y-auto px-4 pb-8 md:px-8">
		<div class="mx-auto max-w-6xl">
			<div class="my-4 flex flex-wrap gap-3">
				<input
					class="min-w-0 flex-1 rounded-xl bg-gray-100 px-4 py-2 dark:bg-gray-850"
					type="search"
					bind:value={query}
					aria-label={$i18n.t('Search')}
					placeholder={$i18n.t('Search')}
				/>
				<select
					class="rounded-xl bg-gray-100 px-3 py-2 dark:bg-gray-850"
					bind:value={kind}
					aria-label={$i18n.t('Type')}
				>
					<option value="all">{$i18n.t('All')}</option>
					<option value="image">{$i18n.t('Images')}</option>
					<option value="video">{$i18n.t('Video')}</option>
					<option value="audio">{$i18n.t('Audio')}</option>
				</select>
			</div>
			<p class="mb-5 text-sm text-gray-500" aria-live="polite">
				{$i18n.t('{{count}} media files loaded', { count: files.length })}
				{#if hasMore}{$i18n.t(
						'Search and filters apply to loaded files. Load more to browse further.'
					)}{/if}
			</p>
			<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
				{#each visible as file (file.id)}
					<article class="overflow-hidden rounded-2xl border border-gray-200 dark:border-gray-800">
						<button
							class="block w-full bg-gray-50 dark:bg-gray-900"
							aria-label={`${$i18n.t('Preview')}: ${fileName(file)}`}
							on:click={() => {
								preview = file;
								previewOpen = true;
							}}
						>
							{#if mediaKind(file) === 'image'}
								<img
									src={contentUrl(file)}
									alt={fileName(file)}
									loading="lazy"
									decoding="async"
									class="aspect-video w-full object-contain"
								/>
							{:else}
								<div class="flex aspect-video items-center justify-center gap-2 text-gray-500">
									<Photo className="size-6" />{mediaKind(file) === 'video'
										? $i18n.t('Video')
										: $i18n.t('Audio')}
								</div>
							{/if}
						</button>
						<div class="p-3">
							<p class="truncate text-sm font-medium" title={fileName(file)}>{fileName(file)}</p>
							<div class="mt-3 flex items-center justify-between text-sm">
								<a
									class="rounded-lg px-2 py-1 hover:bg-gray-100 dark:hover:bg-gray-850"
									href={`${contentUrl(file)}?attachment=true`}
									download={fileName(file)}
									target="_blank"
									rel="noopener noreferrer">{$i18n.t('Download')}</a
								>
								<button
									class="rounded-lg px-2 py-1 text-red-600 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-gray-850"
									disabled={loading || deleting}
									on:click={() => {
										pendingDelete = file;
										confirmDelete = true;
									}}>{$i18n.t('Delete')}</button
								>
							</div>
						</div>
					</article>
				{/each}
			</div>
			{#if !loading && !error && visible.length === 0}
				<p class="py-12 text-center text-gray-500">
					{hasMore
						? $i18n.t('No matching media in the files loaded so far.')
						: $i18n.t('No results found')}
				</p>
			{/if}
			{#if error}<p role="alert" class="mt-6 text-center text-red-600">
					{$i18n.t('Unable to load files. Please try again.')}
				</p>{/if}
			{#if hasMore || loading || error}
				<div class="mt-6 text-center">
					<button
						class="rounded-xl bg-gray-100 px-5 py-2 text-sm disabled:opacity-50 dark:bg-gray-850"
						disabled={loading || deleting}
						on:click={() => loadMore()}
						>{loading
							? $i18n.t('Loading...')
							: error
								? $i18n.t('Retry')
								: $i18n.t('Load more')}</button
					>
				</div>
			{/if}
		</div>
	</div>
</div>

<Modal bind:show={previewOpen} size="lg">
	{#if preview && previewOpen}
		<div class="p-5">
			<div class="mb-4 flex items-center gap-3">
				<h2 class="min-w-0 flex-1 truncate font-medium">{fileName(preview)}</h2>
				<button
					class="rounded-lg px-3 py-2 hover:bg-gray-100 dark:hover:bg-gray-850"
					on:click={() => (previewOpen = false)}>{$i18n.t('Close')}</button
				>
			</div>
			{#if mediaKind(preview) === 'image'}
				<img
					src={contentUrl(preview)}
					alt={fileName(preview)}
					class="mx-auto max-h-[70dvh] max-w-full object-contain"
				/>
			{:else if mediaKind(preview) === 'video'}
				<!-- svelte-ignore a11y-media-has-caption -->
				<video src={contentUrl(preview)} controls preload="metadata" class="max-h-[70dvh] w-full"
				></video>
			{:else}
				<audio src={contentUrl(preview)} controls preload="metadata" class="w-full"></audio>
			{/if}
		</div>
	{/if}
</Modal>

<ConfirmDialog
	bind:show={confirmDelete}
	title={$i18n.t('Delete file?')}
	message={$i18n.t('This permanently deletes the file, including access from chats that use it.')}
	confirmLabel={$i18n.t('Delete')}
	onConfirm={removeFile}
/>
