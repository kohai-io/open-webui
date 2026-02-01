<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Chart, DoughnutController, ArcElement, Tooltip, Legend } from 'chart.js';

	Chart.register(DoughnutController, ArcElement, Tooltip, Legend);

	export let labels: string[] = [];
	export let data: number[] = [];
	export let colors: string[] = [];
	export let height: number = 200;
	export let showLegend: boolean = true;

	let canvas: HTMLCanvasElement;
	let chart: Chart | null = null;
	let hiddenSegments: Set<number> = new Set();
	let originalData: number[] = [];
	let originalColors: string[] = [];
	let showResetBtn = false;

	$: if (chart && data && !hiddenSegments.size) {
		originalData = [...data];
		originalColors = [...colors];
		chart.data.labels = labels;
		chart.data.datasets[0].data = [...data];
		chart.data.datasets[0].backgroundColor = [...colors];
		chart.update();
	}

	function handleClick(event: any, elements: any[]) {
		if (!chart || elements.length === 0) return;
		
		const index = elements[0].index;
		
		if (hiddenSegments.has(index)) {
			hiddenSegments.delete(index);
			chart.data.datasets[0].data[index] = originalData[index];
			(chart.data.datasets[0].backgroundColor as string[])[index] = originalColors[index];
		} else {
			hiddenSegments.add(index);
			chart.data.datasets[0].data[index] = 0;
			(chart.data.datasets[0].backgroundColor as string[])[index] = 'rgba(100, 100, 100, 0.2)';
		}
		
		hiddenSegments = hiddenSegments;
		showResetBtn = hiddenSegments.size > 0;
		chart.update();
	}

	function resetChart() {
		if (!chart) return;
		
		hiddenSegments.clear();
		hiddenSegments = hiddenSegments;
		
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
		originalColors = [...colors];

		chart = new Chart(canvas, {
			type: 'doughnut',
			data: {
				labels,
				datasets: [{
					data: [...data],
					backgroundColor: [...colors],
					borderWidth: 2,
					borderColor: 'rgba(255, 255, 255, 0.1)'
				}]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				onClick: handleClick,
				plugins: {
					legend: {
						display: showLegend,
						position: 'bottom',
						labels: {
							color: '#8b94b8',
							padding: 12,
							usePointStyle: true,
							pointStyle: 'circle'
						}
					},
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
								if (hiddenSegments.has(idx)) {
									return `${labels[idx]}: ${originalData[idx]} (hidden - click to restore)`;
								}
								return `${context.label}: ${context.formattedValue}`;
							}
						}
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
