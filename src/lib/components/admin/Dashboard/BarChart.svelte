<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend } from 'chart.js';

	Chart.register(BarController, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

	export let labels: string[] = [];
	export let data: number[] = [];
	export let colors: string[] | string = 'rgba(99, 102, 241, 0.8)';
	export let height: number = 200;
	export let horizontal: boolean = false;

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;
	let hiddenBars: Set<number> = new Set();
	let originalData: number[] = [];
	let originalColors: string[] = [];
	let showResetBtn = false;

	$: colorArray = Array.isArray(colors) ? colors : Array(data.length).fill(colors);

	$: if (chart && data && !hiddenBars.size) {
		originalData = [...data];
		originalColors = [...colorArray];
		chart.data.labels = labels;
		chart.data.datasets[0].data = [...data];
		chart.data.datasets[0].backgroundColor = [...colorArray];
		chart.update();
	}

	function handleClick(event: any, elements: any[]) {
		if (!chart || elements.length === 0) return;
		
		const index = elements[0].index;
		
		if (hiddenBars.has(index)) {
			hiddenBars.delete(index);
			chart.data.datasets[0].data[index] = originalData[index];
			(chart.data.datasets[0].backgroundColor as string[])[index] = originalColors[index];
		} else {
			hiddenBars.add(index);
			chart.data.datasets[0].data[index] = 0;
			(chart.data.datasets[0].backgroundColor as string[])[index] = 'rgba(100, 100, 100, 0.2)';
		}
		
		hiddenBars = hiddenBars; // trigger reactivity
		showResetBtn = hiddenBars.size > 0;
		chart.update();
	}

	function resetChart() {
		if (!chart) return;
		
		hiddenBars.clear();
		hiddenBars = hiddenBars;
		
		for (let i = 0; i < originalData.length; i++) {
			chart.data.datasets[0].data[i] = originalData[i];
			(chart.data.datasets[0].backgroundColor as string[])[i] = originalColors[i];
		}
		
		showResetBtn = false;
		chart.update();
	}

	onMount(() => {
		if (!canvas) return;

		originalData = [...data];
		originalColors = [...colorArray];

		chart = new Chart(canvas, {
			type: 'bar',
			data: {
				labels,
				datasets: [{
					data: [...data],
					backgroundColor: [...colorArray],
					borderRadius: 6,
					borderSkipped: false
				}]
			},
			options: {
				indexAxis: horizontal ? 'y' : 'x',
				responsive: true,
				maintainAspectRatio: false,
				onClick: handleClick,
				plugins: {
					legend: { display: false },
					tooltip: {
						enabled: true,
						backgroundColor: 'rgba(0, 0, 0, 0.8)',
						titleColor: '#fff',
						bodyColor: '#fff',
						padding: 12,
						cornerRadius: 8,
						callbacks: {
							label: (context: any) => {
								const idx = context.dataIndex;
								if (hiddenBars.has(idx)) {
									return `${originalData[idx]} (hidden - click to restore)`;
								}
								return context.formattedValue;
							}
						}
					}
				},
				scales: {
					y: {
						beginAtZero: true,
						grid: { color: 'rgba(139, 148, 184, 0.1)' },
						ticks: { color: '#8b94b8', font: { size: 11 } }
					},
					x: {
						grid: { display: false },
						ticks: { color: '#8b94b8', font: { size: 11 } }
					}
				}
			}
		});

		canvas.style.cursor = 'pointer';
	});

	onDestroy(() => {
		if (chart) {
			chart.destroy();
			chart = null;
		}
	});
</script>

<div class="relative" style="height: {height}px;">
	<canvas bind:this={canvas}></canvas>
	{#if showResetBtn}
		<button
			class="absolute top-1 right-1 px-2 py-1 text-xs font-medium bg-indigo-500 hover:bg-indigo-600 text-white rounded transition-colors"
			on:click={resetChart}
		>
			Reset
		</button>
	{/if}
</div>
