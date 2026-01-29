# Open WebUI Fork by @kohai-io 👋

> [!NOTE]
> **This is a fork of [Open WebUI](https://github.com/open-webui/open-webui)** maintained by [@kohai-io](https://github.com/kohai-io).
> 
> This fork is developed with assistance from Large Language Models (LLMs) and includes custom modifications and enhancements.
> 
> **For installation instructions, features, and documentation, see the [official upstream project](https://github.com/open-webui/open-webui)**

## About This Fork

This README focuses on what's different in this fork. For general Open WebUI information, installation guides, and full feature documentation, please visit the [upstream repository](https://github.com/open-webui/open-webui).


## Fork-Specific Changes 🔧

### Workspace Media Page (`/workspace/media`) 🆕 **FORK-SPECIFIC**

**This feature is unique to this fork and not present in upstream Open WebUI.**

A comprehensive media library management interface for browsing, organizing, and managing all uploaded files:

- **Unified media library**: Browse all images, videos, audio files, and documents in one place
- **Multiple view modes**:
  - Grid view with visual thumbnails
  - List view with detailed metadata
  - Hierarchical folder/chat organization
- **Smart filtering and search**:
  - Filter by media type (images, videos, audio, documents)
  - Search by filename
  - View by chat/folder association or orphaned files
- **Sorting options**: By date, name, size, or type
- **Batch operations**: Select multiple files for bulk actions
- **File preview**: Click to preview media with metadata display
- **Chat integration**: Quick navigation to associated chats
- **Delete management**: Remove unwanted files from library

**Performance Optimizations** (tested with 892+ files):

- **Fixed OOM Issues**: Resolved Out of Memory crashes during media page scrolling
  - Reduced Intersection Observer `rootMargin` from 200px to 50px to prevent aggressive image preloading
  - Reduced pagination sentinel `rootMargin` from 800px to 200px to prevent premature file loading
  - Disabled video/audio thumbnail loading (static icons 🎬/🎵 instead) to eliminate HTTP 206 partial content requests
  - Disabled `fetchPromptFromChat` calls to prevent SQLite database lock contention from concurrent chat search API calls

- **Component Reorganization**: Restructured workspace components for better maintainability
  - Moved media-related components to `src/lib/components/workspace/Media/`
  - Moved agent-related components to `src/lib/components/workspace/Agents/`

### Custom Features

- **Welcome Landing Page** (`/welcome`): Enhanced onboarding experience
  - Agent selection interface showing available assistants and functions
  - File attachment support (images and documents) that transfers to chat
  - Screen capture/camera integration for quick image input
  - Web search toggle for enabling search in queries
  - Voice mode quick access
  - Seamless transition to chat with pre-selected agents and files

- **Workspace Agents Page** (`/workspace/agents`): Centralized agent management
  - Categorized agent views:
    - **My Agents**: User-created agents and assistants
    - **Shared Agents**: Agents shared by other users
    - **System Agents**: Platform-wide available agents
    - **Foundational Models**: Base LLM models
  - Agent actions: Edit, Clone, Export, Share, Delete
  - Permission-based access control (owner/group-based write access)
  - Quick navigation to chat with selected agent
  - Component reorganization to `src/lib/components/workspace/Agents/`

- **Workspace Flows Page** (`/workspace/flows`): Pipeline and workflow management
  - Create, edit, and manage custom flows/pipelines
  - Flow actions: Create, Edit, Duplicate, Delete
  - Search and filter flows by name
  - Timestamp tracking for flow creation and updates
  - Integration with Open WebUI Pipelines framework

- **Workspace Editor Page** (`/workspace/editor`) ⚠️ **VERY ALPHA**: Video timeline editor for multi-video composition
  - **Canvas-based video player**: Custom video playback with timeline synchronization
  - **Timeline interface**: Visual timeline with drag-and-drop segment editing
    - Add media from library to timeline
    - Create multi-video sequences
    - Segment trimming and positioning
    - Enable/disable segments
    - Duplicate and delete segments
  - **Media pool**: Browse and add videos from media library to timeline
  - **Markers**: Add chapter markers at specific timeline positions
  - **Model integration** (placeholder): Send segments to AI models for processing
  - **Zoom controls**: Adjust timeline zoom level for precision editing
  - Components: `CanvasVideoPlayer`, `Timeline`, `MediaPool`, `ModelSegmentModal`
  - **Status**: Experimental feature under active development

- **Enhanced Chat Media Rendering**: Improved multimedia support in chat messages
  - **Video Support**: Inline video player with controls for `<video>` HTML tags
    - Automatic src extraction and sanitization
    - Full-width responsive player with rounded corners
    - Native browser controls (play, pause, volume, fullscreen)
  - **Audio Support**: Inline audio player for `<audio>` HTML tags
    - Support for both direct src and `<source>` tag formats
    - Full-width responsive player
  - **YouTube Embeds**: Native iframe embedding for YouTube videos
    - Automatic aspect-ratio preservation
    - Full feature support (autoplay, clipboard-write, etc.)
  - **Generic iFrame Support**: Sandboxed iframe rendering for embedded content
    - Auto-height adjustment for content
    - Security sandboxing for cross-origin content
  - **HTML File Rendering**: Direct rendering of HTML file content via iframe
    - Configurable sandbox permissions (forms, same-origin)
    - Full-screen support
  - Implementation in `src/lib/components/chat/Messages/Markdown/HTMLToken.svelte`

- **NeuralNetworkTheater (Pi Gateway)**: 3D visualization interface with:
  - Face and hand tracking visualization using MediaPipe
  - Audio-reactive particles and equalizer visualization
  - 3D chat history visualization with folder support
  - Gesture-based controls for time-of-day navigation
  - Mobile-friendly responsive design

## TODO 📝

### Media Page Enhancements

- **Video Thumbnail Generation**: Implement backend thumbnail generation for video files to display previews without loading full video content
  - Current state: Videos display static 🎬 icon to prevent OOM issues
  - Proposed solution: Server-side thumbnail generation using ffmpeg/opencv
  - Implementation: Create thumbnails on upload/first access, serve via `/api/v1/files/{id}/thumbnail` endpoint
  - Benefits: Visual previews without client-side memory exhaustion

## License 📜

This fork maintains the same license as the upstream Open WebUI project. See [LICENSE](./LICENSE) and [LICENSE_HISTORY](./LICENSE_HISTORY) for details.

## Upstream Project

Original Open WebUI created by [Timothy Jaeryang Baek](https://github.com/tjbck)  
Upstream repository: https://github.com/open-webui/open-webui  
Documentation: https://docs.openwebui.com/  
Discord: https://discord.gg/5rJgQTnV4s
