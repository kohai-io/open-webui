export const CANVAS_SIZE = 1024;

interface Transform {
	id: string;
	x: number;
	y: number;
	scaleX: number;
	scaleY: number;
	rotation: number;
}

export interface CanvasImage extends Transform {
	kind: 'image';
	name: string;
	src: string;
	width: number;
	height: number;
}

export interface CanvasStroke extends Transform {
	kind: 'stroke';
	points: number[];
	color: string;
	size: number;
}

export type CanvasItem = CanvasImage | CanvasStroke;
export interface CanvasResult {
	id: string;
	url: string;
	prompt: string;
	mode: 'text' | 'canvas';
}
export interface CanvasDocument {
	version: 1;
	items: CanvasItem[];
	results: CanvasResult[];
	prompt: string;
}

export const emptyDocument = (): CanvasDocument => ({
	version: 1,
	items: [],
	results: [],
	prompt: ''
});

// Immutable snapshots share the image data strings; only modified strokes are copied.
export function historyPush(history: CanvasItem[][], items: CanvasItem[]): CanvasItem[][] {
	return [...history.slice(-29), items];
}

export function placeImage(
	src: string,
	name: string,
	width: number,
	height: number,
	count: number
): CanvasImage {
	const limit = count === 0 ? CANVAS_SIZE : CANVAS_SIZE * 0.6;
	const scale = Math.min(limit / width, limit / height);
	const w = width * scale;
	const h = height * scale;
	const offset = count === 0 ? 0 : ((count % 5) - 2) * 40;
	return {
		id: crypto.randomUUID(),
		kind: 'image',
		src,
		name,
		width: w,
		height: h,
		x: (CANVAS_SIZE - w) / 2 + offset,
		y: (CANVAS_SIZE - h) / 2 + offset,
		scaleX: 1,
		scaleY: 1,
		rotation: 0
	};
}
