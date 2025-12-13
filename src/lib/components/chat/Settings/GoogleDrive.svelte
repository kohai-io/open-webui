<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { config } from '$lib/stores';

	const i18n = getContext('i18n');

	let loading = false;
	let syncingAll = false;
	let authStatus: { authorized: boolean; expires_at: string | null } | null = null;

	const checkAuthStatus = async () => {
		try {
			const res = await fetch('/api/v1/google-drive/oauth/status', {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});
			if (res.ok) {
				authStatus = await res.json();
			}
		} catch (error) {
			console.error('Failed to check Google Drive auth status:', error);
		}
	};

	const clearAuthToken = async () => {
		loading = true;
		try {
			const res = await fetch('/api/v1/google-drive/oauth/revoke', {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				toast.success($i18n.t('Google Drive authorization cleared'));
				authStatus = { authorized: false, expires_at: null };
			} else {
				const error = await res.json();
				toast.error(error.detail || $i18n.t('Failed to clear authorization'));
			}
		} catch (error) {
			toast.error($i18n.t('Failed to clear Google Drive authorization'));
			console.error(error);
		} finally {
			loading = false;
		}
	};

	const syncAllFiles = async () => {
		syncingAll = true;
		try {
			const res = await fetch('/api/v1/google-drive/oauth/sync-all', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const result = await res.json();
				toast.success(result.message || $i18n.t('Sync complete'));
			} else {
				const error = await res.json();
				toast.error(error.detail || $i18n.t('Failed to sync files'));
			}
		} catch (error) {
			toast.error($i18n.t('Failed to sync Google Drive files'));
			console.error(error);
		} finally {
			syncingAll = false;
		}
	};

	// Check auth status on mount
	checkAuthStatus();
</script>

<div class="flex flex-col h-full justify-between text-sm">
	<div class="pr-1.5 overflow-y-scroll max-h-[25rem] space-y-2">
		<div>
			<div class="mb-2 text-sm font-medium">{$i18n.t('Google Drive')}</div>

			{#if $config?.features?.enable_google_drive_integration}
				<!-- Authorization Status -->
				<div class="mb-4 p-3 bg-gray-50 dark:bg-gray-850 rounded-lg">
					<div class="flex items-center justify-between mb-2">
						<div class="text-xs text-gray-600 dark:text-gray-400">
							{$i18n.t('Authorization Status')}
						</div>
						<div
							class={`text-xs font-medium ${
								authStatus?.authorized
									? 'text-green-600 dark:text-green-400'
									: 'text-gray-500 dark:text-gray-500'
							}`}
						>
							{authStatus?.authorized ? $i18n.t('Authorized') : $i18n.t('Not Authorized')}
						</div>
					</div>
					{#if authStatus?.authorized && authStatus?.expires_at}
						<div class="text-xs text-gray-500 dark:text-gray-500">
							{$i18n.t('Token expires')}: {new Date(authStatus.expires_at).toLocaleString()}
						</div>
					{/if}
				</div>

				<!-- Clear Authorization -->
				<div class="mb-4">
					<div class="flex w-full justify-between">
						<div class="self-center text-xs font-medium">
							{$i18n.t('Clear Authorization')}
						</div>
					</div>

					<div class="mt-2">
						<button
							class="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
							on:click={clearAuthToken}
							disabled={loading || !authStatus?.authorized}
						>
							{loading ? $i18n.t('Clearing...') : $i18n.t('Clear Google Drive Token')}
						</button>
					</div>

					<div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
						{$i18n.t(
							'Remove stored Google Drive authorization. You will need to re-authorize next time you access Drive files.'
						)}
					</div>
				</div>

				<!-- Sync All Files -->
				<div>
					<div class="flex w-full justify-between">
						<div class="self-center text-xs font-medium">{$i18n.t('Sync All Files')}</div>
					</div>

					<div class="mt-2">
						<button
							class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-50"
							on:click={syncAllFiles}
							disabled={syncingAll || !authStatus?.authorized}
						>
							{syncingAll ? $i18n.t('Syncing...') : $i18n.t('Sync All Google Drive Files')}
						</button>
					</div>

					<div class="text-xs text-gray-500 dark:text-gray-400 mt-2">
						{$i18n.t(
							'Check all your Google Drive files for updates and sync the latest versions to your knowledge bases.'
						)}
					</div>
				</div>
			{:else}
				<div class="p-4 bg-gray-50 dark:bg-gray-850 rounded-lg">
					<div class="text-sm text-gray-600 dark:text-gray-400">
						{$i18n.t('Google Drive integration is not enabled.')}
					</div>
				</div>
			{/if}
		</div>
	</div>
</div>
