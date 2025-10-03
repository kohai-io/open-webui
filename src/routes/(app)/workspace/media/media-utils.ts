import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { MediaType, MediaFile } from './media-types';

export const classify = (file: MediaFile): MediaType | 'other' => {
  const meta = file?.meta || {};
  const ct = (
    meta.content_type || meta.mime_type || file?.mime || ''
  )
    .toString()
    .toLowerCase();
  const name = (
    meta.name || file?.filename || ''
  )
    .toString()
    .toLowerCase();

  // Image detection
  if (
    ct.startsWith('image/') ||
    name.endsWith('.png') ||
    name.endsWith('.jpg') ||
    name.endsWith('.jpeg') ||
    name.endsWith('.gif') ||
    name.endsWith('.webp') ||
    name.endsWith('.bmp') ||
    name.endsWith('.svg') ||
    name.endsWith('.tif') ||
    name.endsWith('.tiff')
  ) {
    return 'image';
  }

  // Video detection
  if (
    ct.startsWith('video/') ||
    name.endsWith('.mp4') ||
    name.endsWith('.mov') ||
    name.endsWith('.webm') ||
    name.endsWith('.avi') ||
    name.endsWith('.mkv') ||
    name.endsWith('.m4v')
  ) {
    return 'video';
  }

  // Audio detection
  if (
    ct.startsWith('audio/') ||
    name.endsWith('.mp3') ||
    name.endsWith('.wav') ||
    name.endsWith('.m4a') ||
    name.endsWith('.ogg') ||
    name.endsWith('.flac') ||
    name.endsWith('.aac')
  ) {
    return 'audio';
  }
  return 'other';
};

export const contentUrl = (id: string) => `${WEBUI_API_BASE_URL}/files/${id}/content`;
export const fileMetaUrl = (id: string) => `${WEBUI_API_BASE_URL}/files/${id}`;

export const formatBytes = (bytes?: number) => {
  const b = typeof bytes === 'number' ? bytes : 0;
  if (b === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return `${(b / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
};

export const toEpoch = (v: any) => {
  if (typeof v === 'number') {
    // Backend stores epoch in seconds (int(time.time())). JS Date expects milliseconds.
    // Heuristic: if value is less than 1e12, treat as seconds and convert.
    return v < 1e12 ? v * 1000 : v;
  }
  if (typeof v === 'string') {
    const t = Date.parse(v);
    return isNaN(t) ? 0 : t;
  }
  return 0;
};

export const formatDate = (v: any) => {
  const ts = toEpoch(v);
  if (!ts) return '';
  try {
    const d = new Date(ts);
    return d.toLocaleString();
  } catch {
    return '';
  }
};

export const extractAssistantPrompt = (text: string): string | null => {
  if (!text) return null;
  // Common patterns: "**Prompt:**\n..." or "Prompt:\n..."
  const idx = text.toLowerCase().indexOf('prompt:');
  if (idx === -1) return null;
  let slice = text.slice(idx + 'prompt:'.length);
  // Trim leading formatting characters and whitespace
  slice = slice.replace(/^\s*\*+\s*/i, '').trimStart();
  // Stop at typical separators or headings
  const stopMarkers = [
    '\n---',
    '\n**aspect ratio',
    '\n**parameters',
    '\n**model',
    '\n**notes',
    '\n\n',
  ];
  let end = slice.length;
  for (const mark of stopMarkers) {
    const p = slice.toLowerCase().indexOf(mark);
    if (p !== -1 && p < end) end = p;
  }
  const extracted = slice.slice(0, end).trim();
  return extracted || null;
};

export const copyText = async (text: string): Promise<boolean> => {
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback for older browsers
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }
    return true;
  } catch (e) {
    console.error('Failed to copy text', e);
    return false;
  }
};
