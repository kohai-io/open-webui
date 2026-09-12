import { WEBUI_BASE_URL } from '$lib/constants';

export const MAX_IMAGE_BYTES = 20 * 1024 * 1024;

export async function readImage(file: Blob): Promise<string> {
	if (!['image/png', 'image/jpeg', 'image/webp', 'image/gif', 'image/avif'].includes(file.type)) {
		throw new Error('Choose a PNG, JPEG, WebP, GIF or AVIF image.');
	}
	if (file.size > MAX_IMAGE_BYTES) throw new Error('Each image must be smaller than 20 MB.');
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onload = () => resolve(reader.result as string);
		reader.onerror = () => reject(new Error('Unable to read image.'));
		reader.readAsDataURL(file);
	});
}

export async function decodeImage(src: string): Promise<HTMLImageElement> {
	const image = new Image();
	image.src = src;
	await image.decode();
	if (
		!image.naturalWidth ||
		!image.naturalHeight ||
		image.naturalWidth * image.naturalHeight > 40_000_000
	) {
		throw new Error('Choose an image smaller than 40 megapixels.');
	}
	return image;
}

export function resultUrl(src: string): string {
	const base = new URL(WEBUI_BASE_URL || '/', window.location.origin);
	const url = new URL(src, base);
	// Generated images are OWUI files. Do not forward the token to arbitrary URLs.
	if (
		url.origin !== base.origin ||
		!url.pathname.startsWith(`${base.pathname.replace(/\/$/, '')}/api/v1/files/`)
	) {
		throw new Error('The image backend returned an unsupported file URL.');
	}
	return url.href;
}

export async function loadResult(src: string, token: string): Promise<string> {
	const response = await fetch(resultUrl(src), { headers: { authorization: `Bearer ${token}` } });
	if (!response.ok) throw new Error(`Unable to load generated image (${response.status}).`);
	return readImage(await response.blob());
}
