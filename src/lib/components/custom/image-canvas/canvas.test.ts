import { afterEach, describe, expect, it, vi } from 'vitest';
import { imageEdits, imageGenerations, updateConfig } from '$lib/apis/images';
import { placeImage, CANVAS_SIZE } from './document';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('image canvas backend contract', () => {
	it('trims pasted model IDs when saving settings, without changing prompts or credentials', async () => {
		const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
		vi.stubGlobal('fetch', fetchMock);
		await updateConfig('test-token', {
			IMAGE_GENERATION_MODEL: ' gpt-image-2.5-flare ',
			IMAGE_EDIT_MODEL: '\tgpt-image-2.5-sunburst\n',
			IMAGES_OPENAI_API_KEY: ' unchanged '
		});
		expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
			IMAGE_GENERATION_MODEL: 'gpt-image-2.5-flare',
			IMAGE_EDIT_MODEL: 'gpt-image-2.5-sunburst',
			IMAGES_OPENAI_API_KEY: ' unchanged '
		});
	});
	it('sends a composed PNG directly in the edit schema, without a form_data wrapper', async () => {
		const fetchMock = vi
			.fn()
			.mockResolvedValue({ ok: true, json: async () => [{ url: '/api/v1/files/result/content' }] });
		vi.stubGlobal('fetch', fetchMock);
		await imageEdits('test-token', 'data:image/png;base64,composed', 'Combine this scene');
		const [url, options] = fetchMock.mock.calls[0];
		expect(url).toContain('/images/edit');
		expect(options.headers.authorization).toBe('Bearer test-token');
		expect(JSON.parse(options.body)).toEqual({
			image: 'data:image/png;base64,composed',
			prompt: 'Combine this scene'
		});
	});
	it('keeps text generation independent of canvas inputs', async () => {
		const fetchMock = vi
			.fn()
			.mockResolvedValue({ ok: true, json: async () => [{ url: '/api/v1/files/result/content' }] });
		vi.stubGlobal('fetch', fetchMock);
		await imageGenerations('test-token', 'A landscape');
		expect(fetchMock.mock.calls[0][0]).toContain('/images/generations');
		expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ prompt: 'A landscape' });
	});
	it('preserves existing multi-reference API calls', async () => {
		const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
		vi.stubGlobal('fetch', fetchMock);
		await imageEdits('test-token', ['first', 'second'], 'Combine', 'model', '1024x1024', 2);
		expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
			image: ['first', 'second'],
			prompt: 'Combine',
			model: 'model',
			size: '1024x1024',
			n: 2
		});
	});
	it('fits landscape and portrait images without changing their aspect ratio', () => {
		for (const [width, height] of [
			[2000, 1000],
			[1000, 2000]
		]) {
			const item = placeImage('data:image/png;base64,test', 'Test', width, height, 0);
			expect(item.width / item.height).toBe(width / height);
			expect(Math.max(item.width, item.height)).toBe(CANVAS_SIZE);
			expect(item.x).toBeGreaterThanOrEqual(0);
			expect(item.y).toBeGreaterThanOrEqual(0);
		}
	});
});
