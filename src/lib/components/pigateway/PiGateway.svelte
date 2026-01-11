<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { showPiGateway } from '$lib/stores';
	import NeuralNetworkTheater from './NeuralNetworkTheater.svelte';
	
	let container: HTMLDivElement;
	let showContent = false;
	let glitchActive = false;
	
	const activateGlitch = async () => {
		glitchActive = true;
		await new Promise(resolve => setTimeout(resolve, 1500));
		showContent = true;
		glitchActive = false;
	};
	
	const close = async () => {
		showContent = false;
		glitchActive = true;
		await new Promise(resolve => setTimeout(resolve, 800));
		showPiGateway.set(false);
	};
	
	const handleKeydown = (e: KeyboardEvent) => {
		if (e.key === 'Escape') {
			close();
		}
	};
	
	onMount(() => {
		activateGlitch();
		document.addEventListener('keydown', handleKeydown);
	});
	
	onDestroy(() => {
		document.removeEventListener('keydown', handleKeydown);
	});
</script>

<div 
	bind:this={container}
	class="fixed inset-0 z-[9999] bg-black overflow-hidden"
	class:glitch={glitchActive}
>
	{#if glitchActive}
		<div class="glitch-overlay">
			<div class="glitch-line" style="top: 20%; animation-delay: 0s;"></div>
			<div class="glitch-line" style="top: 45%; animation-delay: 0.3s;"></div>
			<div class="glitch-line" style="top: 70%; animation-delay: 0.6s;"></div>
			<div class="scanline"></div>
			<div class="crt-flicker"></div>
			
			<div class="glitch-text">
				<div class="text-center">
					<div class="pi-symbol text-9xl mb-4">π</div>
					<div class="text-2xl font-mono tracking-wider">JACKING INTO THE NET...</div>
					<div class="text-sm font-mono mt-2 opacity-50">NEURAL INTERFACE ACTIVE</div>
					<div class="text-xs font-mono mt-1 opacity-30">320GB DATASTREAM</div>
				</div>
			</div>
		</div>
	{/if}
	
	{#if showContent}
		<NeuralNetworkTheater onClose={close} />
	{/if}
</div>

<style>
	.glitch-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background: black;
		overflow: hidden;
	}
	
	.glitch-text {
		color: #00ffff;
		text-shadow: 
			0 0 10px #00ffff,
			0 0 20px #00ffff,
			0 0 30px #ff00ff,
			2px 2px 0 #ff00ff,
			-2px -2px 0 #0080ff;
		animation: flicker 0.3s infinite alternate, color-shift 3s ease-in-out infinite;
	}
	
	.pi-symbol {
		font-family: 'Times New Roman', serif;
		font-weight: bold;
		animation: pulse-glow 1s ease-in-out infinite, rotate-3d 4s linear infinite;
		transform-style: preserve-3d;
	}
	
	@keyframes pulse-glow {
		0%, 100% {
			text-shadow: 
				0 0 10px #00ffff,
				0 0 20px #00ffff,
				0 0 30px #ff00ff,
				0 0 40px #0080ff;
		}
		50% {
			text-shadow: 
				0 0 20px #00ffff,
				0 0 30px #00ffff,
				0 0 40px #ff00ff,
				0 0 50px #0080ff,
				0 0 60px #ff00ff;
		}
	}
	
	@keyframes rotate-3d {
		0% { transform: rotateY(0deg); }
		100% { transform: rotateY(360deg); }
	}
	
	@keyframes color-shift {
		0%, 100% { color: #00ffff; }
		33% { color: #ff00ff; }
		66% { color: #0080ff; }
	}
	
	@keyframes flicker {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.8; }
	}
	
	.glitch-line {
		position: absolute;
		left: 0;
		right: 0;
		height: 3px;
		background: linear-gradient(90deg, 
			transparent, 
			rgba(0, 255, 255, 0.8), 
			rgba(255, 0, 255, 0.8),
			rgba(0, 128, 255, 0.8),
			transparent
		);
		animation: scan 2s linear infinite;
		box-shadow: 0 0 10px rgba(0, 255, 255, 0.5);
	}
	
	@keyframes scan {
		0% {
			transform: translateY(-100px);
			opacity: 0;
		}
		10%, 90% {
			opacity: 1;
		}
		100% {
			transform: translateY(100px);
			opacity: 0;
		}
	}
	
	.scanline {
		position: absolute;
		inset: 0;
		background: linear-gradient(
			to bottom,
			transparent 50%,
			rgba(0, 255, 0, 0.03) 50%
		);
		background-size: 100% 4px;
		pointer-events: none;
		animation: scanline-move 0.5s linear infinite;
	}
	
	@keyframes scanline-move {
		0% { transform: translateY(0); }
		100% { transform: translateY(4px); }
	}
	
	.crt-flicker {
		position: absolute;
		inset: 0;
		background: radial-gradient(
			ellipse at center,
			transparent 0%,
			rgba(0, 0, 0, 0.3) 100%
		);
		pointer-events: none;
		animation: vignette 0.1s ease-in-out infinite;
	}
	
	@keyframes vignette {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.9; }
	}
	
	:global(.dark) .glitch-text {
		color: #00ff00;
	}
</style>
