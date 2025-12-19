import { writable } from 'svelte/store';

export interface MediaFile {
	id: string;
	name: string;
	type: 'video' | 'audio' | 'image';
	url: string;
	duration?: number;
	thumbnail?: string;
	width?: number;
	height?: number;
	metadata?: Record<string, any>;
}

export interface TimelineSegment {
	id: string;
	mediaId: string;
	sourceStartTime: number;
	sourceEndTime: number;
	startTime: number;
	endTime: number;
	enabled: boolean;
	volume?: number;
	speed?: number;
}

function createMediaPoolStore() {
	const { subscribe, set, update } = writable<MediaFile[]>([]);

	return {
		subscribe,
		addMedia: (media: MediaFile) => {
			update(items => [...items, media]);
		},
		removeMedia: (mediaId: string) => {
			update(items => items.filter(m => m.id !== mediaId));
		},
		updateMedia: (mediaId: string, updates: Partial<MediaFile>) => {
			update(items => items.map(m => 
				m.id === mediaId ? { ...m, ...updates } : m
			));
		},
		clear: () => set([]),
		getById: (mediaId: string, items: MediaFile[]) => {
			return items.find(m => m.id === mediaId);
		}
	};
}

export const mediaPool = createMediaPoolStore();
