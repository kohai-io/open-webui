<script lang="ts">
	import { onMount } from 'svelte';

	export let videoUrl: string;
	export let duration: number;
	export let pixelsPerSecond: number;
	export let zoom: number = 1.0;
	export let segments: { startTime: number; endTime: number; enabled: boolean }[] = [];

	let thumbnails: { time: number; dataUrl: string }[] = [];
	let generating = false;
	let lastZoomLevel = 1.0;

	onMount(async () => {
		await generateThumbnails();
	});

	const generateThumbnails = async () => {
		if (duration === 0 || generating) return;

		generating = true;
		thumbnails = [];

		try {
			const video = document.createElement('video');
			video.src = videoUrl;
			video.crossOrigin = 'anonymous';

			await new Promise<void>((resolve, reject) => {
				video.onloadedmetadata = () => resolve();
				video.onerror = () => reject(new Error('Failed to load video'));
			});

			const canvas = document.createElement('canvas');
			const ctx = canvas.getContext('2d');
			if (!ctx) return;

			canvas.width = 160;
			canvas.height = 90;

			// Calculate thumbnail count based on visual space available
			// Each thumbnail is 112px wide, so we can fit: timelineWidth / 112
			// Timeline width = duration * pixelsPerSecond
			const thumbnailWidth = 112;
			const timelineWidth = duration * pixelsPerSecond;
			const maxThumbnailsFit = Math.floor(timelineWidth / thumbnailWidth);
			
			// Add some extra for smoother scrubbing (1.5x what fits visually)
			// Capped at 500 for performance
			const targetCount = Math.min(500, Math.max(10, Math.floor(maxThumbnailsFit * 1.5)));
			const interval = duration / targetCount;
			
			lastZoomLevel = zoom;

			for (let i = 0; i < targetCount; i++) {
				const time = i * interval;

				video.currentTime = time;
				await new Promise<void>((resolve) => {
					video.onseeked = () => resolve();
				});

				ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
				const dataUrl = canvas.toDataURL('image/jpeg', 0.6);

				thumbnails = [...thumbnails, { time, dataUrl }];
			}
		} catch (error) {
			console.error('Error generating thumbnails:', error);
		} finally {
			generating = false;
		}
	};

	// Regenerate thumbnails when zoom increases significantly
	$: if (duration > 0 && thumbnails.length === 0) {
		generateThumbnails();
	}
	
	// Generate more thumbnails when zoom increases by 0.5x or more
	$: if (zoom > lastZoomLevel + 0.5 && !generating && thumbnails.length > 0) {
		generateThumbnails();
	}
</script>

<div class="bg-gray-900 border-b border-gray-700 relative" style="height: 96px; min-height: 96px; max-height: 96px;">
	{#if generating}
		<div class="flex items-center justify-center h-full">
			<div class="text-sm text-gray-400">Generating thumbnails...</div>
		</div>
	{:else if thumbnails.length > 0}
		{#each segments as segment}
			{#if segment.enabled}
				<!-- Render thumbnails only within this segment's boundaries -->
				<div
					class="absolute top-0 overflow-hidden"
					style="
						left: {segment.startTime * pixelsPerSecond}px;
						width: {(segment.endTime - segment.startTime) * pixelsPerSecond}px;
						height: 96px;
					"
				>
					{#each thumbnails.filter(t => t.time >= segment.startTime && t.time < segment.endTime) as thumbnail}
						<div
							class="absolute top-1 border border-gray-700 overflow-hidden pointer-events-none select-none"
							style="left: {(thumbnail.time - segment.startTime) * pixelsPerSecond}px; width: 112px; height: 80px; min-width: 112px; max-width: 112px; min-height: 80px; max-height: 80px;"
						>
							<img
								src={thumbnail.dataUrl}
								alt="Frame at {thumbnail.time}s"
								class="pointer-events-none select-none"
								style="width: 112px; height: 80px; object-fit: cover;"
								draggable="false"
							/>
						</div>
					{/each}
				</div>
			{/if}
		{/each}
	{:else}
		<div class="flex items-center justify-center h-full">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				class="w-8 h-8 text-gray-600"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18" />
				<line x1="7" y1="2" x2="7" y2="22" />
				<line x1="17" y1="2" x2="17" y2="22" />
				<line x1="2" y1="12" x2="22" y2="12" />
				<line x1="2" y1="7" x2="7" y2="7" />
				<line x1="2" y1="17" x2="7" y2="17" />
				<line x1="17" y1="17" x2="22" y2="17" />
				<line x1="17" y1="7" x2="22" y2="7" />
			</svg>
		</div>
	{/if}
</div>
