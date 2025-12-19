<script lang="ts">
	import { onMount } from 'svelte';

	export let videoUrl: string;
	export let duration: number;
	export let pixelsPerSecond: number;
	export let segments: { startTime: number; endTime: number; enabled: boolean }[] = [];

	let canvas: HTMLCanvasElement;
	let waveformData: Float32Array | null = null;
	let generating = false;

	onMount(async () => {
		await generateWaveform();
	});

	const generateWaveform = async () => {
		if (generating || !videoUrl) return;

		generating = true;

		try {
			const audioContext = new AudioContext();
			const response = await fetch(videoUrl);
			const arrayBuffer = await response.arrayBuffer();

			const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

			const channelData = audioBuffer.getChannelData(0);
			waveformData = channelData;

			drawWaveform();
		} catch (error) {
			console.error('Error generating waveform:', error);
		} finally {
			generating = false;
		}
	};

	const drawWaveform = () => {
		if (!canvas || !waveformData) return;

		const ctx = canvas.getContext('2d');
		if (!ctx) return;

		const width = canvas.width;
		const height = canvas.height;
		const samples = waveformData.length;
		const samplesPerPixel = Math.max(1, Math.floor(samples / width));

		ctx.clearRect(0, 0, width, height);

		ctx.fillStyle = '#3b82f6';
		ctx.strokeStyle = '#3b82f6';

		for (let x = 0; x < width; x++) {
			const start = x * samplesPerPixel;
			const end = Math.min(start + samplesPerPixel, samples);

			let min = 1.0;
			let max = -1.0;

			for (let i = start; i < end; i++) {
				const sample = waveformData[i];
				if (sample < min) min = sample;
				if (sample > max) max = sample;
			}

			const barHeight = Math.max(1, (max - min) * (height / 2));
			const y = height / 2 - (max * height) / 2;

			ctx.fillRect(x, y, 1, barHeight);
		}
	};

	$: if (canvas && waveformData) {
		canvas.width = Math.max(800, duration * pixelsPerSecond);
		canvas.height = 80;
		drawWaveform();
	}

	$: if (duration > 0 && !waveformData && !generating) {
		generateWaveform();
	}
</script>

<div class="bg-gray-900 border-b border-gray-700 relative overflow-hidden" style="height: 80px; min-height: 80px; max-height: 80px;">
	{#if generating}
		<div class="flex items-center justify-center h-full">
			<div class="text-sm text-gray-400">Generating waveform...</div>
		</div>
	{:else if waveformData}
		<!-- Clip waveform canvas to segment boundaries -->
		{#each segments as segment}
			{#if segment.enabled}
				<div
					class="absolute top-0 overflow-hidden"
					style="
						left: {segment.startTime * pixelsPerSecond}px;
						width: {(segment.endTime - segment.startTime) * pixelsPerSecond}px;
						height: 80px;
					"
				>
					<canvas 
						bind:this={canvas} 
						style="
							height: 80px; 
							position: absolute;
							left: {-segment.startTime * pixelsPerSecond}px;
						"
					></canvas>
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
				<path d="M9 18V5l12-2v13" />
				<circle cx="6" cy="18" r="3" />
				<circle cx="18" cy="16" r="3" />
			</svg>
		</div>
	{/if}
</div>
