import { writable, derived } from 'svelte/store';
import type { Marker, VideoSegment } from '$lib/types/video';

export interface Video {
	id: string;
	name: string;
	description?: string;
	file_id: string;
	duration: number;
	thumbnail?: string;
	created_at: number;
	updated_at: number;
}

export interface VideoState {
	currentTime: number;
	duration: number;
	isPlaying: boolean;
	volume: number;
	playbackRate: number;
}

export interface TimelineState {
	zoom: number;
	scrollPosition: number;
	selectedRegion: { start: number; end: number } | null;
	activeTool: 'select' | 'blade';
	snapping: boolean;
	isDragging: boolean;
}

export const currentVideo = writable<Video | null>(null);

export const videoState = writable<VideoState>({
	currentTime: 0,
	duration: 0,
	isPlaying: false,
	volume: 1.0,
	playbackRate: 1.0
});

export const timelineState = writable<TimelineState>({
	zoom: 1.0,
	scrollPosition: 0,
	selectedRegion: null,
	activeTool: 'select',
	snapping: true,
	isDragging: false
});

export const markers = writable<Marker[]>([]);

export const segments = writable<VideoSegment[]>([]);

export const isProcessing = writable<boolean>(false);

export const progress = derived(videoState, ($videoState) => {
	if ($videoState.duration === 0) return 0;
	return ($videoState.currentTime / $videoState.duration) * 100;
});
