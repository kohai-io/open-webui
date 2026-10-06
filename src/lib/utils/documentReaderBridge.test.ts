import { describe, expect, it } from 'vitest';
import { createDocumentReaderBridge } from './documentReaderBridge';

const snapshot = {
	version: 1,
	fingerprint: 'a'.repeat(64),
	resume_scope: 'b'.repeat(64),
	created_at: '2026-10-06',
	passages: [{ id: 'p1' }],
	sections: [{ id: 's1' }]
};
const html = `<script id="reader-data" type="application/json">${JSON.stringify(snapshot)}</script>`;
const key = `document-reader:position:${snapshot.resume_scope}:${snapshot.fingerprint}:${snapshot.created_at}`;
const position = {
	v: 1,
	fingerprint: snapshot.fingerprint,
	passage: 'p1',
	level: 'explanation',
	offset: 18,
	expanded: ['p1'],
	mapAnchor: { kind: 'map', id: 's1', offset: 24 }
};
function storage() {
	const values = new Map<string, string>();
	return {
		values,
		getItem: (key: string) => values.get(key) ?? null,
		setItem: (key: string, value: string) => values.set(key, value),
		removeItem: (key: string) => values.delete(key)
	} as unknown as Storage & { values: Map<string, string> };
}
describe('isolated Reader host bridge', () => {
	it('stores only validated location fields, scoped to the current account', () => {
		const local = storage(),
			a = createDocumentReaderBridge(html, 'user-a', local)!,
			b = createDocumentReaderBridge(html, 'user-b', local)!;
		a(
			{
				type: 'document-reader:save',
				key,
				value: { ...position, documentText: 'must never be stored', token: 'secret' }
			},
			900
		);
		const loaded = a({ type: 'document-reader:load', key }, 900) as any;
		expect(loaded.supported).toBe(true);
		expect(loaded.value.passage).toBe('p1');
		expect(loaded.value.expanded).toEqual(['p1']);
		expect(loaded.value).not.toHaveProperty('documentText');
		expect(JSON.stringify([...local.values.values()])).not.toContain('secret');
		expect((b({ type: 'document-reader:load', key }, 900) as any).value).toBeNull();
	});
	it('rejects other keys, unknown passages, mismatched documents and invalid offsets', () => {
		const local = storage(),
			bridge = createDocumentReaderBridge(html, 'user-a', local)!;
		expect(bridge({ type: 'document-reader:load', key: 'access_token' }, 900)).toBeNull();
		for (const bad of [
			{ passage: 'p999' },
			{ fingerprint: 'c'.repeat(64) },
			{ offset: Infinity },
			{ offset: '18' },
			{ level: 'javascript' }
		]) {
			bridge({ type: 'document-reader:save', key, value: { ...position, ...bad } }, 900);
		}
		expect(local.values.size).toBe(0);
	});
	it('bounds viewport height and tolerates corrupt or blocked browser storage', () => {
		const local = storage(),
			bridge = createDocumentReaderBridge(html, 'user', local)!;
		expect((bridge({ type: 'document-reader:viewport-request', key }, 600) as any).height).toBe(
			480
		);
		expect((bridge({ type: 'document-reader:viewport-request', key }, 2000) as any).height).toBe(
			1000
		);
		local.setItem(`owui:user:${key}`, '{broken');
		expect((bridge({ type: 'document-reader:load', key }, 900) as any).value).toBeNull();
		const blocked = createDocumentReaderBridge(html, 'user', {
			getItem() {
				throw new Error('blocked');
			}
		} as unknown as Storage)!;
		expect((blocked({ type: 'document-reader:load', key }, 900) as any).supported).toBe(false);
	});
	it('ignores unrelated embeds and invalid Reader metadata', () => {
		expect(createDocumentReaderBridge('<p>Other content</p>', 'user', storage())).toBeNull();
		expect(createDocumentReaderBridge(html, '', storage())).toBeNull();
		expect(
			createDocumentReaderBridge(html.replace(snapshot.fingerprint, 'wrong'), 'user', storage())
		).toBeNull();
	});
});
