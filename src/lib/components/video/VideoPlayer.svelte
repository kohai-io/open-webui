<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import type { VideoSegment } from '$lib/types/video';

	export let videoUrl: string;
	export let videoElement: HTMLVideoElement | null = null;
	export let segments: VideoSegment[] = [];

	const dispatch = createEventDispatcher();

	let isPlaying = false;
	let currentTime = 0;
	let duration = 0;
	let volume = 1.0;
	let playbackRate = 1.0;
	let isLooping = false;
	let lastCheckedTime = 0;
	let activeSegmentId: string | null = null;

	onMount(() => {
		if (videoElement) {
			videoElement.addEventListener('timeupdate', handleTimeUpdate);
			videoElement.addEventListener('durationchange', handleDurationChange);
			videoElement.addEventListener('play', handlePlay);
			videoElement.addEventListener('pause', handlePause);
			videoElement.addEventListener('volumechange', handleVolumeChange);
			videoElement.addEventListener('ended', handleEnded);

			return () => {
				videoElement?.removeEventListener('timeupdate', handleTimeUpdate);
				videoElement?.removeEventListener('durationchange', handleDurationChange);
				videoElement?.removeEventListener('play', handlePlay);
				videoElement?.removeEventListener('pause', handlePause);
				videoElement?.removeEventListener('volumechange', handleVolumeChange);
				videoElement?.removeEventListener('ended', handleEnded);
			};
		}
	});

	const handleTimeUpdate = () => {
		if (videoElement) {
			const actualVideoTime = videoElement.currentTime;
			
			// Find the active segment by ID (set during seek/play start)
			let currentSegment = activeSegmentId 
				? segments.find(s => s.id === activeSegmentId)
				: null;
			
			// If no active segment, try to find one based on timeline position
			if (!currentSegment) {
				// On initial play or if lost, find segment containing timeline position
				currentSegment = segments.find(s => currentTime >= s.startTime && currentTime < s.endTime);
				if (currentSegment) {
					activeSegmentId = currentSegment.id;
					// Set video to start of this segment's source
					if (currentSegment.sourceStartTime !== undefined) {
						videoElement.currentTime = currentSegment.sourceStartTime;
					}
				}
			}
			
			if (currentSegment) {
				// Verify segment has source times
				if (currentSegment.sourceStartTime === undefined || currentSegment.sourceEndTime === undefined) {
					console.error('❌ Active segment missing source times!', currentSegment);
					currentTime = actualVideoTime;
				} else {
					// Calculate timeline position based on offset within the segment's source
					const sourceOffset = actualVideoTime - currentSegment.sourceStartTime;
					currentTime = currentSegment.startTime + sourceOffset;
				}
			} else {
				currentTime = actualVideoTime;
			}
			
			dispatch('timeupdate', { time: currentTime });
			
			// Segment-aware playback control
			if (isPlaying && segments.length > 0 && currentSegment && Math.abs(actualVideoTime - lastCheckedTime) > 0.016) {
				lastCheckedTime = actualVideoTime;
				
				if (!currentSegment.enabled) {
					// We're in a disabled segment, jump to next enabled
					console.log('⏭️ In disabled segment, skipping to next...');
					const nextEnabledTime = getNextEnabledTime(currentTime);
					if (nextEnabledTime !== null) {
						const nextSegment = segments.find(s => nextEnabledTime >= s.startTime && nextEnabledTime < s.endTime);
						if (nextSegment && nextSegment.sourceStartTime !== undefined) {
							activeSegmentId = nextSegment.id;
							videoElement.currentTime = nextSegment.sourceStartTime;
						}
					} else {
						console.log('⏸️ No more enabled segments, pausing');
						activeSegmentId = null;
						videoElement.pause();
					}
				} else if (currentSegment.sourceEndTime !== undefined && actualVideoTime >= currentSegment.sourceEndTime - 0.033) {
					// Reached end of current segment's source content
					// Find next segment on timeline
					const sortedSegments = [...segments].sort((a, b) => a.startTime - b.startTime);
					const currentIndex = sortedSegments.findIndex(s => s.id === currentSegment.id);
					const nextSegment = currentIndex >= 0 && currentIndex < sortedSegments.length - 1 
						? sortedSegments[currentIndex + 1] 
						: null;
					
					if (nextSegment && nextSegment.enabled && nextSegment.sourceStartTime !== undefined) {
						// Jump to next segment
						console.log('⏭️ Jumping to next segment:', {
							from: {id: currentSegment.id.substring(0,8), sourceEnd: currentSegment.sourceEndTime},
							to: {id: nextSegment.id.substring(0,8), sourceStart: nextSegment.sourceStartTime},
							videoWasPaused: videoElement.paused,
							currentVideoTime: videoElement.currentTime.toFixed(2)
						});
						
						activeSegmentId = nextSegment.id;
						const targetSourceTime = nextSegment.sourceStartTime;
						
						// Set the video time
						videoElement.currentTime = targetSourceTime;
						currentTime = nextSegment.startTime;
						
						console.log('→ Set video.currentTime to:', targetSourceTime, 'paused:', videoElement.paused);
						
						// Ensure playback continues after seeking
						if (videoElement.paused) {
							console.log('→ Video was paused, calling play()');
							videoElement.play().catch(err => console.error('❌ Play failed:', err));
						} else {
							console.log('→ Video still playing after seek');
						}
					} else {
						// No next segment, pause
						activeSegmentId = null;
						videoElement.pause();
					}
				}
			}
		}
	};

	const handleDurationChange = () => {
		if (videoElement) {
			duration = videoElement.duration;
			dispatch('durationchange', { duration });
		}
	};

	const handlePlay = () => {
		isPlaying = true;
		dispatch('playstatechange', { isPlaying: true });
	};

	const handlePause = () => {
		isPlaying = false;
		dispatch('playstatechange', { isPlaying: false });
	};

	const handleVolumeChange = () => {
		if (videoElement) {
			volume = videoElement.volume;
		}
	};

	const handleEnded = () => {
		if (isLooping && videoElement) {
			// Loop back to the first enabled segment
			const firstEnabledSegment = segments.find(s => s.enabled);
			videoElement.currentTime = firstEnabledSegment ? firstEnabledSegment.startTime : 0;
			videoElement.play();
		}
	};

	// Public method to seek to a timeline position
	export const seekToTimelinePosition = (timelineTime: number) => {
		if (!videoElement) return;
		
		// Find segment containing this timeline position
		const targetSegment = segments.find(s => timelineTime >= s.startTime && timelineTime < s.endTime);
		
		if (targetSegment) {
			if (targetSegment.sourceStartTime === undefined || (targetSegment.sourceStartTime !== 0 && !targetSegment.sourceStartTime)) {
				console.error('❌ Segment missing sourceStartTime!', targetSegment);
				return;
			}
			
			activeSegmentId = targetSegment.id;
			const offset = timelineTime - targetSegment.startTime;
			const sourceTime = targetSegment.sourceStartTime + offset;
			videoElement.currentTime = sourceTime;
			currentTime = timelineTime;
		} else {
			// No segment at this position, clear active segment
			activeSegmentId = null;
			videoElement.currentTime = timelineTime;
			currentTime = timelineTime;
		}
	};

	const togglePlayPause = () => {
		if (videoElement) {
			if (isPlaying) {
				videoElement.pause();
			} else {
				// When starting playback, ensure we're at the right segment
				if (!activeSegmentId) {
					seekToTimelinePosition(currentTime);
				}
				videoElement.play();
			}
		}
	};

	const stopVideo = () => {
		if (videoElement) {
			videoElement.pause();
			videoElement.currentTime = 0;
		}
	};

	const skipBackward = (seconds: number = 5) => {
		if (videoElement) {
			// Work with timeline position, not source video time
			const targetTime = Math.max(0, currentTime - seconds);
			const validTime = getNextEnabledTime(targetTime, 'backward');
			seekToTimelinePosition(validTime !== null ? validTime : targetTime);
		}
	};

	const skipForward = (seconds: number = 5) => {
		if (videoElement) {
			// Work with timeline position, not source video time
			const targetTime = Math.min(duration, currentTime + seconds);
			const validTime = getNextEnabledTime(targetTime);
			seekToTimelinePosition(validTime !== null ? validTime : targetTime);
		}
	};

	// Find the next enabled time point, or return null if time is valid
	const getNextEnabledTime = (time: number, direction: 'forward' | 'backward' = 'forward'): number | null => {
		if (segments.length === 0) return null;
		
		// Check if current time is in an enabled segment
		const currentSegment = segments.find(s => time >= s.startTime && time < s.endTime);
		
		if (currentSegment && currentSegment.enabled) {
			// We're in an enabled segment, no need to skip
			return null;
		}
		
		// Find the next enabled segment
		if (direction === 'forward') {
			const nextSegment = segments.find(s => s.enabled && s.startTime >= time);
			if (nextSegment) {
				return nextSegment.startTime;
			}
			// No more enabled segments
			return null;
		} else {
			// Find previous enabled segment
			const prevSegments = segments.filter(s => s.enabled && s.endTime <= time);
			if (prevSegments.length > 0) {
				const prevSegment = prevSegments[prevSegments.length - 1];
				return prevSegment.endTime - 0.1; // Go near the end of previous segment
			}
			// No previous enabled segments, go to first enabled segment
			const firstEnabled = segments.find(s => s.enabled);
			return firstEnabled ? firstEnabled.startTime : 0;
		}
	};

	const stepFrame = (direction: number) => {
		if (videoElement) {
			const frameRate = 30;
			const frameDuration = 1 / frameRate;
			// Work with timeline position, not source video time
			let newTime = currentTime + (frameDuration * direction);
			newTime = Math.max(0, Math.min(duration, newTime));
			
			// Check if new time is in a disabled segment
			const validTime = getNextEnabledTime(newTime, direction > 0 ? 'forward' : 'backward');
			seekToTimelinePosition(validTime !== null ? validTime : newTime);
		}
	};

	const handleKeydown = (e: KeyboardEvent) => {
		switch (e.key) {
			case ' ':
			case 'k':
				e.preventDefault();
				togglePlayPause();
				break;
			case 'ArrowLeft':
				e.preventDefault();
				stepFrame(-1);
				break;
			case 'ArrowRight':
				e.preventDefault();
				stepFrame(1);
				break;
			case 'j':
				e.preventDefault();
				skipBackward(10);
				break;
			case 'l':
				e.preventDefault();
				skipForward(10);
				break;
			case 'm':
				e.preventDefault();
				toggleMute();
				break;
			case 'f':
				e.preventDefault();
				toggleFullscreen();
				break;
			case 'Home':
				e.preventDefault();
				stopVideo();
				break;
			case '0':
			case '1':
			case '2':
				e.preventDefault();
				const rates = [0.5, 1.0, 1.5, 2.0];
				const index = parseInt(e.key);
				if (index < rates.length) {
					setPlaybackRate(rates[index]);
				}
				break;
		}
	};

	const setPlaybackRate = (rate: number) => {
		if (videoElement) {
			videoElement.playbackRate = rate;
			playbackRate = rate;
		}
	};

	const toggleLoop = () => {
		isLooping = !isLooping;
		if (videoElement) {
			videoElement.loop = isLooping;
		}
	};

	const toggleMute = () => {
		if (videoElement) {
			videoElement.muted = !videoElement.muted;
		}
	};

	const toggleFullscreen = () => {
		if (videoElement) {
			if (document.fullscreenElement) {
				document.exitFullscreen();
			} else {
				videoElement.requestFullscreen();
			}
		}
	};

	const formatTime = (seconds: number) => {
		const h = Math.floor(seconds / 3600);
		const m = Math.floor((seconds % 3600) / 60);
		const s = Math.floor(seconds % 60);
		if (h > 0) {
			return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
		}
		return `${m}:${s.toString().padStart(2, '0')}`;
	};
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="relative w-full h-full flex flex-col items-center justify-center group">
	<!-- Video Element -->
	<video
		bind:this={videoElement}
		src={videoUrl}
		class="max-w-full max-h-full object-contain"
		on:click={togglePlayPause}
	>
		<track kind="captions" />
	</video>

	<!-- Video Controls Overlay -->
	<div
		class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4 opacity-0 group-hover:opacity-100 transition-opacity"
	>
		<!-- Progress Bar -->
		<div class="mb-3">
			<div class="relative h-1 bg-gray-600 rounded-full cursor-pointer">
				<div
					class="absolute h-full bg-blue-500 rounded-full"
					style="width: {duration > 0 ? (currentTime / duration) * 100 : 0}%"
				></div>
			</div>
		</div>

		<!-- Controls -->
		<div class="flex items-center justify-between text-white">
			<div class="flex items-center gap-2">
				<!-- Stop Button -->
				<button
					on:click={stopVideo}
					class="p-2 hover:bg-white/20 rounded-lg transition-colors"
					title="Stop (Home)"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						viewBox="0 0 24 24"
						fill="currentColor"
					>
						<rect x="6" y="6" width="12" height="12" />
					</svg>
				</button>

				<!-- Skip Backward -->
				<button
					on:click={() => skipBackward(5)}
					class="p-2 hover:bg-white/20 rounded-lg transition-colors"
					title="Skip Back 5s (←)"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M11 19l-7-7 7-7" />
						<path d="M18 19l-7-7 7-7" />
					</svg>
				</button>
				<!-- Play/Pause Button -->
				<button
					on:click={togglePlayPause}
					class="p-2 hover:bg-white/20 rounded-lg transition-colors"
					title={isPlaying ? 'Pause (Space/K)' : 'Play (Space/K)'}
				>
					{#if isPlaying}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-6 h-6"
							viewBox="0 0 24 24"
							fill="currentColor"
						>
							<rect x="6" y="4" width="4" height="16" />
							<rect x="14" y="4" width="4" height="16" />
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-6 h-6"
							viewBox="0 0 24 24"
							fill="currentColor"
						>
							<polygon points="5 3 19 12 5 21 5 3" />
						</svg>
					{/if}
				</button>

				<!-- Skip Forward -->
				<button
					on:click={() => skipForward(5)}
					class="p-2 hover:bg-white/20 rounded-lg transition-colors"
					title="Skip Forward 5s (→)"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M13 5l7 7-7 7" />
						<path d="M6 5l7 7-7 7" />
					</svg>
				</button>

				<div class="w-px h-6 bg-white/20 mx-1"></div>

				<!-- Playback Speed -->
				<div class="relative group/speed">
					<button
						class="px-2 py-1 hover:bg-white/20 rounded-lg transition-colors text-sm font-mono min-w-[48px]"
						title="Playback Speed (0-2)"
					>
						{playbackRate}x
					</button>
					<div class="absolute bottom-full left-0 mb-2 hidden group-hover/speed:block bg-gray-900/95 backdrop-blur-sm rounded-lg shadow-xl border border-gray-700 py-1 min-w-[80px]">
						{#each [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2] as rate}
							<button
								on:click={() => setPlaybackRate(rate)}
								class="w-full px-3 py-1.5 text-left text-sm hover:bg-white/10 {playbackRate === rate ? 'text-blue-400 font-semibold' : 'text-white'}"
							>
								{rate}x
							</button>
						{/each}
					</div>
				</div>

				<!-- Loop Toggle -->
				<button
					on:click={toggleLoop}
					class="p-2 hover:bg-white/20 rounded-lg transition-colors {isLooping ? 'text-blue-400' : ''}"
					title={isLooping ? 'Loop: On' : 'Loop: Off'}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						class="w-5 h-5"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
					>
						<path d="M17 2l4 4-4 4" />
						<path d="M3 11v-1a4 4 0 0 1 4-4h14" />
						<path d="M7 22l-4-4 4-4" />
						<path d="M21 13v1a4 4 0 0 1-4 4H3" />
					</svg>
				</button>

				<div class="w-px h-6 bg-white/20 mx-1"></div>

				<!-- Volume Button -->
				<button
					on:click={toggleMute}
					class="p-2 hover:bg-white/20 rounded-lg transition-colors"
					title={volume === 0 ? 'Unmute' : 'Mute'}
				>
					{#if volume === 0}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-5 h-5"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
							<line x1="23" y1="9" x2="17" y2="15" />
							<line x1="17" y1="9" x2="23" y2="15" />
						</svg>
					{:else}
						<svg
							xmlns="http://www.w3.org/2000/svg"
							class="w-5 h-5"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
							<path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
						</svg>
					{/if}
				</button>

				<!-- Time Display -->
				<span class="text-sm font-mono">
					{formatTime(currentTime)} / {formatTime(duration)}
				</span>
			</div>

			<!-- Fullscreen Button -->
			<button
				on:click={toggleFullscreen}
				class="p-2 hover:bg-white/20 rounded-lg transition-colors"
				title="Fullscreen"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					class="w-5 h-5"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path
						d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"
					/>
				</svg>
			</button>
		</div>
	</div>
</div>
