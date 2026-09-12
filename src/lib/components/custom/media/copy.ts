import type { i18n } from 'i18next';

// Feature-owned copy: keep custom keys out of the upstream translation catalogue.
// Deployments can provide translations in the customMedia namespace.
const copy = {
	title: 'Media',
	video: 'Video',
	loaded: 'Media files loaded: {{count}}',
	loadedOnly: 'Search and filters apply to loaded files. Load more to browse further.',
	emptyPage: 'No matching media in the files loaded so far.',
	loadError: 'Unable to load files. Please try again.',
	deleteError: 'Error deleting file',
	retry: 'Retry',
	loadMore: 'Load more',
	deleteTitle: 'Delete file?',
	deleteWarning: 'This permanently deletes the file, including access from chats that use it.'
};

export function mediaText(
	i18n: i18n,
	key: keyof typeof copy,
	values: Record<string, string | number> = {}
): string {
	return i18n.t(key, { ...values, ns: 'customMedia', defaultValue: copy[key] });
}
