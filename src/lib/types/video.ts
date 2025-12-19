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
}

export interface WaveformData {
	peaks: Float32Array;
	duration: number;
	sampleRate: number;
}

export interface ThumbnailData {
	timestamp: number;
	dataUrl: string;
}

export interface Marker {
	id: string;
	time: number;
	label: string;
	color?: string;
	type?: 'chapter' | 'note' | 'flag';
}

export interface VideoSegment {
	id: string;
	mediaId: string; // Reference to media in media pool
	startTime: number; // Position on timeline
	endTime: number; // Position on timeline
	sourceStartTime: number; // Original video timecode start
	sourceEndTime: number; // Original video timecode end
	enabled: boolean;
	volume?: number;
	speed?: number;
}
