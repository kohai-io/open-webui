import { WEBUI_API_BASE_URL } from '$lib/constants';

export type MediaKind = 'image' | 'video' | 'audio';

export interface MediaFile {
	id: string;
	filename: string;
	meta?: { name?: string; content_type?: string | null; size?: number } | null;
}

export interface FilePage {
	items: MediaFile[];
	total: number;
}

// Keep the upstream Files contract here; the gallery does not own file records.
// getFiles currently has no page argument, so this adapter calls that same endpoint.
export async function getFilePage(
	token: string,
	page: number,
	signal?: AbortSignal
): Promise<FilePage> {
	const query = new URLSearchParams({ page: String(page), content: 'false' });
	const response = await fetch(`${WEBUI_API_BASE_URL}/files/?${query}`, {
		headers: { Accept: 'application/json', authorization: `Bearer ${token}` },
		signal
	});
	if (!response.ok) throw new Error(`Files request failed (${response.status})`);
	const data = await response.json();
	if (!Array.isArray(data?.items) || !Number.isInteger(data.total) || data.total < 0) {
		throw new Error('Unexpected Files response');
	}
	return data;
}

export function mediaKind(file: MediaFile): MediaKind | null {
	const mime =
		typeof file.meta?.content_type === 'string' ? file.meta.content_type.toLowerCase() : '';
	for (const kind of ['image', 'video', 'audio'] as const) {
		if (mime.startsWith(`${kind}/`)) return kind;
	}
	if (mime && mime !== 'application/octet-stream') return null;
	const extension = (file.meta?.name || file.filename).split('.').pop()?.toLowerCase() ?? '';
	if (['png', 'jpg', 'jpeg', 'webp', 'gif', 'avif', 'bmp', 'svg'].includes(extension))
		return 'image';
	if (['mp4', 'webm', 'mov', 'm4v', 'mkv'].includes(extension)) return 'video';
	if (['mp3', 'wav', 'ogg', 'm4a', 'flac', 'aac', 'opus'].includes(extension)) return 'audio';
	return null;
}

export const fileName = (file: MediaFile) => file.meta?.name || file.filename;
export const contentUrl = (file: MediaFile) =>
	`${WEBUI_API_BASE_URL}/files/${encodeURIComponent(file.id)}/content`;
