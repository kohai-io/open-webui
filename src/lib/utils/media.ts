import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { MediaType, MediaFile, Chat, Folder, GroupBy, SortBy, SortDir, GroupedItems, Mode } from '$lib/types/media';

// Classification cache to avoid repeated type detection
const classifyCache = new WeakMap<MediaFile, MediaType | 'other'>();

export const classify = (file: MediaFile): MediaType | 'other' => {
  // Check cache first
  const cached = classifyCache.get(file);
  if (cached !== undefined) {
    return cached;
  }
  
  // Compute classification
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
    classifyCache.set(file, 'image');
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
    classifyCache.set(file, 'video');
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
    classifyCache.set(file, 'audio');
    return 'audio';
  }
  classifyCache.set(file, 'other');
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

// Helper functions for file access
const getName = (file: MediaFile) => (file?.filename || file?.meta?.name || '').toString().toLowerCase();
const getSize = (file: MediaFile) => (typeof file?.meta?.size === 'number' ? file.meta.size : 0);
const getUpdated = (file: MediaFile) => toEpoch(file?.updated_at);

/**
 * Filter files by tab, search query, mode, and chat association
 */
export const filterFiles = (
  files: MediaFile[],
  activeTab: MediaType,
  query: string,
  mode: Mode,
  selectedChatId: string | null,
  fileToChat: Record<string, string | null>
): MediaFile[] => {
  let filtered = [...files];

  // Tab filtering
  if (activeTab !== 'all') {
    filtered = filtered.filter((f) => classify(f) === activeTab);
  }

  // Search filtering
  if (query?.trim()) {
    const q = query.trim().toLowerCase();
    filtered = filtered.filter((f) => {
      const fname = getName(f);
      return fname.includes(q);
    });
  }

  // Mode-specific filtering
  if (mode === 'chat' && selectedChatId) {
    filtered = filtered.filter((f) => fileToChat[f.id] === selectedChatId);
  } else if (mode === 'orphans') {
    filtered = filtered.filter((f) => fileToChat[f.id] === null);
  }

  return filtered;
};

/**
 * Sort files by specified criteria
 */
export const sortFiles = (
  files: MediaFile[],
  sortBy: SortBy,
  sortDir: SortDir
): MediaFile[] => {
  const sorted = [...files];

  const cmp = (a: MediaFile, b: MediaFile) => {
    let va: any, vb: any;
    if (sortBy === 'name') {
      va = getName(a);
      vb = getName(b);
    } else if (sortBy === 'type') {
      va = classify(a);
      vb = classify(b);
    } else if (sortBy === 'size') {
      va = getSize(a);
      vb = getSize(b);
    } else {
      va = getUpdated(a);
      vb = getUpdated(b);
    }
    if (va < vb) return sortDir === 'asc' ? -1 : 1;
    if (va > vb) return sortDir === 'asc' ? 1 : -1;
    // Secondary sort by updated desc for stability
    const s = getUpdated(a) - getUpdated(b);
    return sortDir === 'asc' ? -s : s;
  };

  sorted.sort(cmp);
  return sorted;
};

/**
 * Group files - returns all files as single group
 * (hierarchy grouping is handled separately by MediaOverview component)
 */
export const groupFiles = (
  files: MediaFile[],
  groupBy: GroupBy,
  fileToChat: Record<string, string | null>,
  chatsById: Record<string, Chat>,
  foldersById: Record<string, Folder>,
  linking: boolean
): Record<string, GroupedItems> => {
  const groups: Record<string, GroupedItems> = {};
  
  // For 'none' or any other groupBy value, return flat list
  groups['__all__'] = { key: '__all__', label: 'All Media', items: files };
  
  return groups;
};

/**
 * Calculate media type counts (optimized single-pass)
 */
export const calculateCounts = (files: MediaFile[]) => {
  const counts = { all: files.length, image: 0, video: 0, audio: 0 };
  
  for (const f of files) {
    const type = classify(f);
    if (type === 'image') counts.image++;
    else if (type === 'video') counts.video++;
    else if (type === 'audio') counts.audio++;
  }
  
  return counts;
};
