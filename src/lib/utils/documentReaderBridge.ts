// A narrow host bridge for saved Reader embeds. Never accept caller-chosen storage
// keys or document text. FullHeightIframe checks the sending contentWindow first.
export function createDocumentReaderBridge(html: string, owner: string, storage: Storage) {
	if (!owner || html.length > 2 * 1024 * 1024) return null;
	const match = html.match(
		/<script id="reader-data" type="application\/json">([\s\S]*?)<\/script>/
	);
	if (!match) return null;
	let snapshot: any;
	try {
		snapshot = JSON.parse(match[1]);
	} catch {
		return null;
	}
	if (
		!snapshot ||
		snapshot.version !== 1 ||
		typeof snapshot.fingerprint !== 'string' ||
		!/^[a-f0-9]{64}$/.test(snapshot.fingerprint) ||
		!/^[a-f0-9]{64}$/.test(snapshot.resume_scope) ||
		typeof snapshot.created_at !== 'string' ||
		snapshot.created_at.length > 50 ||
		!Array.isArray(snapshot.passages) ||
		snapshot.passages.length > 500 ||
		!Array.isArray(snapshot.sections) ||
		snapshot.sections.length > 500 ||
		!snapshot.passages.every(
			(p: any) => p && typeof p.id === 'string' && /^p\d{1,6}$/.test(p.id)
		) ||
		!snapshot.sections.every((s: any) => s && typeof s.id === 'string' && /^s\d{1,6}$/.test(s.id))
	)
		return null;
	const passageIds = new Set(snapshot.passages.map((p: any) => p.id));
	const sectionIds = new Set(snapshot.sections.map((s: any) => s.id));
	const key = `document-reader:position:${snapshot.resume_scope}:${snapshot.fingerprint}:${snapshot.created_at}`;
	const storageKey = `owui:${owner}:${key}`;
	const levels = new Set(['map', 'takeaways', 'explanation', 'extracts', 'full']);
	function sanitize(value: any) {
		if (
			!value ||
			value.v !== 1 ||
			value.fingerprint !== snapshot.fingerprint ||
			!passageIds.has(value.passage) ||
			!levels.has(value.level) ||
			typeof value.offset !== 'number' ||
			!Number.isFinite(value.offset) ||
			Math.abs(value.offset) > 100000
		)
			return null;
		const map = value.mapAnchor;
		return {
			v: 1,
			fingerprint: snapshot.fingerprint,
			passage: value.passage,
			level: value.level,
			offset: value.offset,
			lastTextLevel:
				levels.has(value.lastTextLevel) && value.lastTextLevel !== 'map'
					? value.lastTextLevel
					: 'takeaways',
			expanded: Array.isArray(value.expanded)
				? value.expanded.filter((id: any) => passageIds.has(id)).slice(0, 30)
				: [],
			mapAnchor:
				map?.kind === 'map' &&
				sectionIds.has(map.id) &&
				typeof map.offset === 'number' &&
				Number.isFinite(map.offset) &&
				Math.abs(map.offset) <= 100000
					? { kind: 'map', id: map.id, offset: map.offset }
					: null
		};
	}
	return (message: any, viewportHeight: number) => {
		if (!message || message.key !== key) return null;
		if (message.type === 'document-reader:viewport-request') {
			return {
				type: 'document-reader:viewport',
				key,
				height: Math.max(480, Math.min(1000, viewportHeight - 200))
			};
		}
		if (message.type === 'document-reader:load') {
			try {
				const raw = storage.getItem(storageKey);
				let value = null;
				if (raw && raw.length <= 12000)
					try {
						value = sanitize(JSON.parse(raw));
					} catch {
						/* discard corrupt position */
					}
				storage.setItem(storageKey + ':check', '1');
				storage.removeItem(storageKey + ':check');
				return { type: 'document-reader:loaded', key, supported: true, value };
			} catch {
				return { type: 'document-reader:loaded', key, supported: false, value: null };
			}
		}
		if (message.type === 'document-reader:save') {
			const value = sanitize(message.value);
			if (value)
				try {
					storage.setItem(storageKey, JSON.stringify(value));
				} catch {
					return { type: 'document-reader:loaded', key, supported: false, value: null };
				}
		}
		return null;
	};
}
