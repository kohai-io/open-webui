export type MediaType = 'all' | 'image' | 'video' | 'audio';
export type Mode = 'overview' | 'folder' | 'chat' | 'orphans';
export type ViewMode = 'grid' | 'list';
export type GroupBy = 'hierarchy' | 'none';
export type SortBy = 'name' | 'type' | 'size' | 'updated';
export type SortDir = 'asc' | 'desc';

export interface MediaFile {
  id: string;
  filename: string;
  mime?: string;
  updated_at: any;
  meta?: {
    content_type?: string;
    mime_type?: string;
    name?: string;
    size?: number;
    prompt?: string;
    chat_id?: string;
    source_chat_id?: string;
    collection_name?: string;
  };
  chat_id?: string;
}

export interface Chat {
  id: string;
  title: string;
  updated_at: any;
  folder_id?: string;
  folderId?: string;
  chat?: {
    messages?: any[];
    history?: {
      messages?: Record<string, any>;
    };
  };
}

export interface Folder {
  id: string;
  name: string;
  updated_at: any;
}

export interface MediaCounts {
  all: number;
  image: number;
  video: number;
  audio: number;
}

export interface GroupedItems {
  key: string;
  label: string;
  items: MediaFile[];
}

export interface MediaState {
  loading: boolean;
  error: string | null;
  files: MediaFile[];
  mode: Mode;
  selectedFolderId: string | null;
  selectedChatId: string | null;
  initialFilesLoaded: boolean;
  activeTab: MediaType;
  query: string;
  pageSize: number;
  visibleCount: number;
  viewMode: ViewMode;
  groupBy: GroupBy;
  sortBy: SortBy;
  sortDir: SortDir;
  previewItem: MediaFile | null;
  promptLoading: boolean;
  resolvedPrompt: string | null;
  deleting: Record<string, boolean>;
  chatsById: Record<string, Chat>;
  foldersById: Record<string, Folder>;
  fileToChat: Record<string, string | null>;
  linking: boolean;
  linkingErrors: number;
}
