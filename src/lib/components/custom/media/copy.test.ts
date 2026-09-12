import { readFileSync } from 'node:fs';
import { createInstance } from 'i18next';
import { JavascriptLexer } from 'i18next-parser';
import { describe, expect, it } from 'vitest';
import upstreamEnglish from '$lib/i18n/locales/en-US/translation.json';
import { mediaText } from './copy';

describe('feature-local Media copy', () => {
	it('provides English fallback and interpolates counts without a custom locale bundle', async () => {
		const i18n = createInstance();
		await i18n.init({ lng: 'en-US', resources: {} });
		expect(mediaText(i18n, 'title')).toBe('Media');
		expect(mediaText(i18n, 'loaded', { count: 1 })).toBe('Media files loaded: 1');
	});

	it('uses supplied custom translations without changing upstream resources', async () => {
		const i18n = createInstance();
		await i18n.init({ lng: 'fr', resources: { fr: { customMedia: { title: 'Médias' } } } });
		expect(mediaText(i18n, 'title')).toBe('Médias');
	});

	it('does not introduce keys into upstream locale extraction', () => {
		for (const path of ['./Media.svelte', '../navigation/CustomLinks.svelte']) {
			const source = readFileSync(new URL(path, import.meta.url), 'utf8');
			const entries = new JavascriptLexer().extract(source);
			const newKeys = entries.map((entry) => entry.key).filter((key) => !(key in upstreamEnglish));
			expect(newKeys).toEqual([]);
		}
	});
});
