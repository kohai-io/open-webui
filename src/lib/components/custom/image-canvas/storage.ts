import { openDB } from 'idb';
import type { CanvasDocument } from './document';

async function database() {
	return openDB('owui-image-canvas', 1, {
		upgrade(db) {
			db.createObjectStore('drafts');
		}
	});
}

export async function loadDraft(userId: string): Promise<CanvasDocument | undefined> {
	const db = await database();
	try {
		const draft = await db.get('drafts', userId);
		return draft?.version === 1 ? draft : undefined;
	} finally {
		db.close();
	}
}

export async function saveDraft(userId: string, document: CanvasDocument): Promise<void> {
	const db = await database();
	try {
		await db.put('drafts', document, userId);
	} finally {
		db.close();
	}
}
