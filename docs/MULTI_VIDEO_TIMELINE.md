# Multi-Video Timeline Editor

## Overview
The timeline editor now supports **multiple video sources** on a single timeline using a canvas-based playback engine. This enables true non-linear editing capabilities.

## Architecture

### Components
1. **MediaPool** - Manages all media files (videos, images, audio)
2. **CanvasVideoPlayer** - Canvas-based renderer that switches between video sources
3. **Timeline** - Visual timeline with segments that reference media pool items
4. **Segments** - Clips that link to specific timecodes within media pool files

### Data Structure
```typescript
interface MediaFile {
  id: string;
  name: string;
  type: 'video' | 'audio' | 'image';
  url: string;
  duration?: number;
}

interface VideoSegment {
  id: string;
  mediaId: string;           // References MediaFile.id
  startTime: number;         // Position on timeline
  endTime: number;           // Position on timeline
  sourceStartTime: number;   // Timecode in source media
  sourceEndTime: number;     // Timecode in source media
  enabled: boolean;
}
```

## How It Works

### Playback Engine
- Each media file gets a hidden `<video>` element
- Canvas composites the active segment's video frames
- When reaching segment end, automatically switches to next segment's media source
- Seamless transitions between different video files

### Adding Media
1. Click "Add Media" or drag files into Media Pool
2. Supported: Video, audio, images
3. Media appears as thumbnail in pool

### Creating Timeline
1. Click media in pool to add to timeline
2. Use blade tool to cut segments
3. Drag segments to reorder
4. Trim segment edges to adjust in/out points

### Segment Operations
- **Blade Cut**: Splits segment at playhead, preserves source timecodes
- **Move**: Drag segment to new timeline position
- **Trim**: Drag blue edges to adjust duration and source selection
- **Delete**: (TODO) Remove segment from timeline

## Use Cases

### Multi-Video Editing
```
Timeline:  [ClipA: 0-3s] [ClipB: 3-8s] [ClipA: 8-11s]
           └─Video1.mp4  └─Video2.mp4  └─Video1.mp4
```

### AI-Generated Insertions
1. Generate video with model (e.g., Veo-3)
2. Add generated video to media pool
3. Insert as segment at desired timeline position
4. Reference segment timecodes for prompt context

### Image Sequences
1. Add images to media pool (default 5s duration each)
2. Create segments from images
3. Mix with video segments

## Current Limitations
- Audio mixing not yet implemented (only active segment audio plays)
- No transition effects between segments
- Export functionality not yet implemented
- Segment deletion requires manual store update

## Future Enhancements
- Audio track mixing
- Transition effects (fade, wipe, etc.)
- Multiple video tracks
- Export to video file
- Real-time preview rendering
- Timeline markers for AI model reference points
