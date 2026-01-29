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

**Performance**: Optimized for large libraries (tested with 892+ files) with lazy loading and memory-efficient rendering.

### Custom Features

- **Welcome Landing Page** (`/welcome`): Enhanced onboarding experience
  - Agent selection interface showing available assistants and functions
  - File attachment support (images and documents) that transfers to chat
  - Screen capture/camera integration for quick image input
  - Web search toggle for enabling search in queries
  - Voice mode quick access
  - Seamless transition to chat with pre-selected agents and files

- **Workspace Agents Page** (`/workspace/agents`): Centralized agent management
  - Categorized views: My Agents, Shared Agents, System Agents, Foundational Models
  - Agent actions: Edit, Clone, Export, Share, Delete
  - Permission-based access control
  - Quick navigation to chat with selected agent

- **Workspace Flows Page** (`/workspace/flows`): Pipeline and workflow management
  - Create, edit, duplicate, and delete flows/pipelines
  - Search and filter flows
  - Integration with Open WebUI Pipelines framework

- **Workspace Editor Page** (`/workspace/editor`) ⚠️ **VERY ALPHA**: Video timeline editor
  - Multi-video composition with drag-and-drop timeline
  - Add media from library, trim segments, add markers
  - Canvas-based video player with timeline sync
  - Experimental feature under active development

- **Enhanced Chat Media Rendering**: Improved multimedia support in chat messages
  - Inline video and audio players with native controls
  - YouTube embed support with aspect-ratio preservation
  - Sandboxed iframe rendering for embedded content
  - HTML file rendering with configurable permissions

- **NeuralNetworkTheater (Pi Gateway)**: 3D visualization interface with:
  - Face and hand tracking visualization using MediaPipe
  - Audio-reactive particles and equalizer visualization
  - 3D chat history visualization with folder support
  - Gesture-based controls for time-of-day navigation
  - Mobile-friendly responsive design

## TODO 📝

- **Video Thumbnail Generation**: Backend thumbnail generation for video files (currently showing static icons)

## License 📜

This fork maintains the same license as the upstream Open WebUI project. See [LICENSE](./LICENSE) and [LICENSE_HISTORY](./LICENSE_HISTORY) for details.

## Upstream Project

Original Open WebUI created by [Timothy Jaeryang Baek](https://github.com/tjbck)  
Upstream repository: https://github.com/open-webui/open-webui  
Documentation: https://docs.openwebui.com/  
Discord: https://discord.gg/5rJgQTnV4s
