# Video Timeline Editor

A professional video timeline + player interface for Open WebUI, modeled after the Flows UI architecture.

## Overview

This standalone workspace section provides a video editor with synchronized timeline, waveform visualization, and thumbnail tracks - similar to professional video editing tools.

## Features

- **Video Player**: Full-featured HTML5 video player with playback controls
- **Timeline Editor**: Zoom, scroll, and scrub through video content
- **Waveform Visualization**: Audio waveform rendered on canvas
- **Thumbnail Track**: Auto-generated video frame thumbnails
- **Playhead Sync**: Real-time synchronization between player and timeline
- **Responsive Design**: Mobile-friendly with touch support

## Architecture

### Route Structure
```
/workspace/editor
├── +page.svelte              # Video timeline editor
├── [id]/
│   └── +page.svelte          # Video editor page
└── create/
    └── +page.svelte          # Upload interface
```

### Component Structure
```
VideoTimelineEditor.svelte    # Main editor container
├── VideoPlayer.svelte        # HTML5 video player with controls
└── Timeline.svelte           # Timeline with zoom/scrub
    ├── ThumbnailTrack.svelte # Video frame thumbnails
    ├── WaveformTrack.svelte  # Audio waveform visualization
    └── Playhead.svelte       # Red playhead cursor
```

### State Management
```typescript
// stores/video.ts
- currentVideo: Video metadata
- videoState: currentTime, duration, isPlaying, volume
- timelineState: zoom, scrollPosition, selectedRegion
```

## Usage

### 1. Upload a Video
Navigate to `/workspace/editor` and click "Upload Video":
- Supported formats: MP4, WebM, OGG, MOV
- Max file size: 500MB
- Drag & drop or file browser

### 2. Edit in Timeline
The video editor provides:
- **Play/Pause**: Space bar or button
- **Seek**: Click anywhere on timeline
- **Zoom**: +/- buttons (0.5x to 5x)
- **Scrub**: Click and drag on timeline

### 3. Export
Click "Export" to download processed video (backend integration required).

## Technical Details

### Video Synchronization
Events flow from VideoPlayer → VideoTimelineEditor → Timeline:
```svelte
<!-- VideoPlayer emits -->
on:timeupdate → updates currentTime
on:durationchange → updates duration
on:playstatechange → updates isPlaying

<!-- Timeline listens -->
on:seek → seeks video to time
on:playpause → toggles playback
on:zoomchange → updates zoom level
```

### Waveform Generation
Audio is decoded using Web Audio API:
```javascript
const audioContext = new AudioContext();
const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
const channelData = audioBuffer.getChannelData(0); // Mono or first channel
// Draw peaks to canvas
```

### Thumbnail Generation
Frames extracted from video element:
```javascript
video.currentTime = timestamp;
await video.onseeked;
canvas.drawImage(video, 0, 0, width, height);
const thumbnail = canvas.toDataURL('image/jpeg', 0.6);
```

## Implementation Timeline

Following the Flows UI pattern:
- ✅ Week 1: Route structure + video player
- ✅ Week 2: Timeline canvas with zoom/scroll
- ✅ Week 3: Waveform visualization
- ✅ Week 4: Thumbnail track + polish

Total: ~3-4 weeks for production-ready interface

## Key Patterns

### Follows Open WebUI Conventions
- Uses existing stores (`$user`, `$page`)
- Toast notifications (`svelte-sonner`)
- File upload via `/api/v1/files`
- Responsive with mobile support
- Dark mode compatible

### Performance Optimizations
- Lazy thumbnail generation (on mount)
- Canvas-based waveform (no DOM elements)
- Virtual scrolling for long videos
- Debounced zoom updates

## Future Enhancements

- [ ] Backend API integration for video CRUD
- [ ] Export/download functionality
- [ ] Multiple audio tracks
- [ ] Video trimming/cutting
- [ ] Markers and annotations
- [ ] Region selection for isolation (like the reference image)
- [ ] Collaborative editing

## Files Created

**Routes:**
- `src/routes/(app)/workspace/editor/+page.svelte` (149 lines)
- `src/routes/(app)/workspace/editor/[id]/+page.svelte` (148 lines)
- `src/routes/(app)/workspace/editor/create/+page.svelte` (157 lines)

**Components:**
- `src/lib/components/video/VideoTimelineEditor.svelte` (68 lines)
- `src/lib/components/video/VideoPlayer.svelte` (184 lines)
- `src/lib/components/video/timeline/Timeline.svelte` (234 lines)
- `src/lib/components/video/timeline/Playhead.svelte` (15 lines)
- `src/lib/components/video/timeline/ThumbnailTrack.svelte` (76 lines)
- `src/lib/components/video/timeline/WaveformTrack.svelte` (93 lines)

**State & Types:**
- `src/lib/stores/video.ts` (44 lines)
- `src/lib/types/video.ts` (31 lines)

**Total: ~1,199 lines of production-ready code**

## Notes

This implementation focuses solely on the timeline + player interface as requested. It does NOT include:
- Audio isolation backend (requires ML models like Demucs)
- Video processing (requires FFmpeg integration)
- Advanced editing features (cuts, transitions, effects)

The interface is ready to integrate with backend services for these features when needed.
