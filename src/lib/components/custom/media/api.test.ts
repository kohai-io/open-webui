import { afterEach, describe, expect, it, vi } from 'vitest';
import { getFilePage, mediaKind } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('Media Files API adapter', () => {
	it('requests a bounded upstream page without extracted content and preserves non-media pagination', async () => {
		const page = { items: [{ id: 'doc', filename: 'notes.pdf' }], total: 120 };
		const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => page });
		vi.stubGlobal('fetch', fetchMock);
		expect(await getFilePage('test-token', 2)).toEqual(page);
		const [url, options] = fetchMock.mock.calls[0];
		expect(url).toContain('/files/?page=2&content=false');
		expect(options.headers.authorization).toBe('Bearer test-token');
		expect(mediaKind(page.items[0])).toBeNull();
	});

	it('surfaces denied access instead of showing an empty gallery', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 403 }));
		await expect(getFilePage('test-token', 1)).rejects.toThrow('403');
	});

	it('detects an upstream response contract change', async () => {
		vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
		await expect(getFilePage('test-token', 1)).rejects.toThrow('Unexpected Files response');
	});
});

describe('media classification', () => {
	it('uses content type for generated files without extensions', () => {
		expect(mediaKind({ id: '1', filename: 'generated', meta: { content_type: 'image/png' } })).toBe(
			'image'
		);
	});

	it('falls back to filenames for legacy or generic file metadata', () => {
		expect(mediaKind({ id: '1', filename: 'CLIP.MP4', meta: null })).toBe('video');
		expect(
			mediaKind({
				id: '2',
				filename: 'speech.flac',
				meta: { content_type: 'application/octet-stream' }
			})
		).toBe('audio');
	});

	it('does not override an explicit non-media content type with an extension', () => {
		expect(
			mediaKind({ id: '1', filename: 'report.png', meta: { content_type: 'application/pdf' } })
		).toBeNull();
	});
});
