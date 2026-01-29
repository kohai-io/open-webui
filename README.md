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

### Media Page Performance Fixes

This fork includes critical performance optimizations for the media page when handling large media libraries (tested with 892+ files):

- **Fixed OOM Issues**: Resolved Out of Memory crashes during media page scrolling
  - Reduced Intersection Observer `rootMargin` from 200px to 50px to prevent aggressive image preloading
  - Reduced pagination sentinel `rootMargin` from 800px to 200px to prevent premature file loading
  - Disabled video/audio thumbnail loading (static icons 🎬/🎵 instead) to eliminate HTTP 206 partial content requests
  - Disabled `fetchPromptFromChat` calls to prevent SQLite database lock contention from concurrent chat search API calls

- **Component Reorganization**: Restructured workspace components for better maintainability
  - Moved media-related components to `src/lib/components/workspace/Media/`
  - Moved agent-related components to `src/lib/components/workspace/Agents/`

### Custom Features

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
