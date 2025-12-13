<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import FileItem from '$lib/components/common/FileItem.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let selectedFileId: string | null = null;
	export let files: any[] = [];

	export let small = false;

	const isDriveFile = (file: any): boolean => {
		return file?.meta?.data?.source === 'google_drive';
	};

	const getLastSyncedText = (file: any): string => {
		const lastSynced = file?.meta?.data?.google_drive?.last_synced_at;
		if (!lastSynced) return 'Never synced';
		
		const date = new Date(lastSynced * 1000);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		
		if (diffMins < 1) return 'Just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		
		const diffHours = Math.floor(diffMins / 60);
		if (diffHours < 24) return `${diffHours}h ago`;
		
		const diffDays = Math.floor(diffHours / 24);
		return `${diffDays}d ago`;
	};

	const handleSyncFile = (fileId: string, event: Event) => {
		event.stopPropagation();
		dispatch('sync', fileId);
	};
</script>

<div class=" max-h-full flex flex-col w-full">
	{#each files as file}
		<div class="mt-1 px-2">
			<div class="flex items-center gap-2 w-full">
				<div class="flex-1 min-w-0">
					<FileItem
						className="w-full"
						colorClassName="{selectedFileId === file.id
							? ' bg-gray-50 dark:bg-gray-850'
							: 'bg-transparent'} hover:bg-gray-50 dark:hover:bg-gray-850 transition"
						{small}
						item={file}
						name={file?.name ?? file?.meta?.name}
						type="file"
						size={file?.size ?? file?.meta?.size ?? ''}
						loading={file.status === 'uploading'}
						dismissible
						on:click={() => {
							if (file.status === 'uploading') {
								return;
							}

							dispatch('click', file.id);
						}}
						on:dismiss={() => {
							if (file.status === 'uploading') {
								return;
							}

							dispatch('delete', file.id);
						}}
					/>
				</div>
				
				{#if isDriveFile(file)}
					<div class="flex items-center gap-1">
						<Tooltip content="From Google Drive - {getLastSyncedText(file)}">
							<div class="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 87.3 78" class="w-4 h-4">
									<path
										d="m6.6 66.85 3.85 6.65c.8 1.4 1.95 2.5 3.3 3.3l13.75-23.8h-27.5c0 1.55.4 3.1 1.2 4.5z"
										fill="#0066da"
									/>
									<path
										d="m43.65 25-13.75-23.8c-1.35.8-2.5 1.9-3.3 3.3l-25.4 44a9.06 9.06 0 0 0 -1.2 4.5h27.5z"
										fill="#00ac47"
									/>
									<path
										d="m73.55 76.8c1.35-.8 2.5-1.9 3.3-3.3l1.6-2.75 7.65-13.25c.8-1.4 1.2-2.95 1.2-4.5h-27.502l5.852 11.5z"
										fill="#ea4335"
									/>
									<path
										d="m43.65 25 13.75-23.8c-1.35-.8-2.9-1.2-4.5-1.2h-18.5c-1.6 0-3.15.45-4.5 1.2z"
										fill="#00832d"
									/>
									<path
										d="m59.8 53h-32.3l-13.75 23.8c1.35.8 2.9 1.2 4.5 1.2h50.8c1.6 0 3.15-.45 4.5-1.2z"
										fill="#2684fc"
									/>
									<path
										d="m73.4 26.5-12.7-22c-.8-1.4-1.95-2.5-3.3-3.3l-13.75 23.8 16.15 28h27.45c0-1.55-.4-3.1-1.2-4.5z"
										fill="#ffba00"
									/>
								</svg>
							</div>
						</Tooltip>
						
						<Tooltip content="Sync from Google Drive">
							<button
								class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition"
								on:click={(e) => handleSyncFile(file.id, e)}
								disabled={file.status === 'uploading'}
								aria-label="Sync from Google Drive"
							>
								<svg 
									xmlns="http://www.w3.org/2000/svg" 
									viewBox="0 0 16 16" 
									fill="currentColor" 
									class="w-4 h-4 text-gray-600 dark:text-gray-300"
								>
									<path fill-rule="evenodd" d="M13.836 2.477a.75.75 0 0 1 .75.75v3.182a.75.75 0 0 1-.75.75h-3.182a.75.75 0 0 1 0-1.5h1.37l-.84-.841a4.5 4.5 0 0 0-7.08.932.75.75 0 0 1-1.3-.75 6 6 0 0 1 9.44-1.242l.842.84V3.227a.75.75 0 0 1 .75-.75Zm-.911 7.5A.75.75 0 0 1 13.199 11a6 6 0 0 1-9.44 1.241l-.84-.84v1.371a.75.75 0 0 1-1.5 0V9.591a.75.75 0 0 1 .75-.75H5.35a.75.75 0 0 1 0 1.5H3.98l.841.841a4.5 4.5 0 0 0 7.08-.932.75.75 0 0 1 1.025-.273Z" clip-rule="evenodd" />
								</svg>
							</button>
						</Tooltip>
					</div>
				{/if}
			</div>
		</div>
	{/each}
</div>
