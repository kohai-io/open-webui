<script lang="ts">
	import { afterUpdate } from 'svelte';
	import { Stage, Layer, Rect, Image as KImage, Line, Transformer } from 'svelte-konva';
	import type Konva from 'konva';
	import { CANVAS_SIZE, type CanvasItem, type CanvasStroke } from './document';

	export let items: CanvasItem[] = [];
	export let images: Map<string, HTMLImageElement>;
	export let selected = '';
	export let tool: 'select' | 'draw' = 'select';
	export let color = '#171717';
	export let brushSize = 8;
	export let disabled = false;
	export let onchange: (items: CanvasItem[]) => void;

	let stage: { node: Konva.Stage };
	let transformer: { node: Konva.Transformer };
	let width = 600;
	let height = 600;
	let stroke: CanvasStroke | null = null;
	let pointerId: number | null = null;
	$: scale = Math.max(0.05, Math.min(width - 24, height - 24, 850) / CANVAS_SIZE);

	afterUpdate(() => {
		if (!stage || !transformer) return;
		// Keyed Svelte components retain their Konva nodes when the layer order changes.
		items.forEach((item, index) => stage.node.findOne(`#${item.id}`)?.zIndex(index + 1));
		const node =
			selected && tool === 'select' && !disabled ? stage.node.findOne(`#${selected}`) : null;
		transformer.node.nodes(node ? [node] : []);
		transformer.node.moveToTop();
	});

	function position() {
		const point = stage.node.getRelativePointerPosition();
		return (
			point && {
				x: Math.max(0, Math.min(CANVAS_SIZE, point.x)),
				y: Math.max(0, Math.min(CANVAS_SIZE, point.y))
			}
		);
	}

	function pointerDown(event: Konva.KonvaEventObject<PointerEvent>) {
		if (disabled || !event.evt.isPrimary || event.evt.button > 0) return;
		if (tool === 'select') {
			if (event.target === stage.node || event.target.name() === 'background') selected = '';
			return;
		}
		const point = position();
		if (!point) return;
		selected = '';
		pointerId = event.evt.pointerId;
		(event.evt.target as HTMLElement).setPointerCapture?.(pointerId);
		stroke = {
			id: crypto.randomUUID(),
			kind: 'stroke',
			x: 0,
			y: 0,
			scaleX: 1,
			scaleY: 1,
			rotation: 0,
			points: [point.x, point.y, point.x + 0.01, point.y + 0.01],
			color,
			size: brushSize
		};
	}

	function pointerMove(event: Konva.KonvaEventObject<PointerEvent>) {
		if (!stroke || event.evt.pointerId !== pointerId) return;
		const point = position();
		if (point) stroke = { ...stroke, points: [...stroke.points, point.x, point.y] };
	}

	function finishStroke() {
		if (stroke) onchange([...items, stroke]);
		stroke = null;
		pointerId = null;
	}

	function transform(event: Konva.KonvaEventObject<Event>) {
		const node = event.target;
		onchange(
			items.map((item) =>
				item.id === node.id()
					? {
							...item,
							x: node.x(),
							y: node.y(),
							scaleX: node.scaleX(),
							scaleY: node.scaleY(),
							rotation: node.rotation()
						}
					: item
			)
		);
	}

	export function exportPng(): string {
		if (stroke) finishStroke();
		transformer.node.hide();
		try {
			return stage.node.toDataURL({ pixelRatio: 1 / scale, mimeType: 'image/png' });
		} finally {
			transformer.node.show();
		}
	}
</script>

<div class="surface" bind:clientWidth={width} bind:clientHeight={height} data-testid="image-canvas">
	<Stage
		bind:this={stage}
		width={CANVAS_SIZE * scale}
		height={CANVAS_SIZE * scale}
		scaleX={scale}
		scaleY={scale}
		onpointerdown={pointerDown}
		onpointermove={pointerMove}
		onpointerup={finishStroke}
		onpointercancel={finishStroke}
		divWrapperProps={{
			style: `touch-action: none; cursor: ${tool === 'draw' ? 'crosshair' : 'default'}; box-shadow: 0 2px 16px #0002;`
		}}
	>
		<Layer>
			<Rect name="background" width={CANVAS_SIZE} height={CANVAS_SIZE} fill="#ffffff" />
			{#each items as item (item.id)}
				{#if item.kind === 'image'}
					<KImage
						id={item.id}
						image={images.get(item.src)}
						x={item.x}
						y={item.y}
						width={item.width}
						height={item.height}
						scaleX={item.scaleX}
						scaleY={item.scaleY}
						rotation={item.rotation}
						staticConfig
						draggable={tool === 'select' && !disabled}
						listening={tool === 'select' && !disabled}
						onpointerdown={() => (selected = item.id)}
						ondragend={transform}
						ontransformend={transform}
					/>
				{:else}
					<Line
						id={item.id}
						points={item.points}
						stroke={item.color}
						strokeWidth={item.size}
						lineCap="round"
						lineJoin="round"
						x={item.x}
						y={item.y}
						scaleX={item.scaleX}
						scaleY={item.scaleY}
						rotation={item.rotation}
						staticConfig
						draggable={tool === 'select' && !disabled}
						listening={tool === 'select' && !disabled}
						onpointerdown={() => (selected = item.id)}
						ondragend={transform}
						ontransformend={transform}
					/>
				{/if}
			{/each}
			{#if stroke}<Line
					points={stroke.points}
					stroke={stroke.color}
					strokeWidth={stroke.size}
					lineCap="round"
					lineJoin="round"
					listening={false}
				/>{/if}
			<Transformer
				bind:this={transformer}
				flipEnabled={false}
				keepRatio={true}
				enabledAnchors={['top-left', 'top-right', 'bottom-left', 'bottom-right']}
				boundBoxFunc={(oldBox, newBox) =>
					Math.abs(newBox.width) < 8 || Math.abs(newBox.height) < 8 ? oldBox : newBox}
			/>
		</Layer>
	</Stage>
</div>

<style>
	.surface {
		width: 100%;
		height: 100%;
		min-height: 280px;
		display: flex;
		align-items: center;
		justify-content: center;
		overflow: hidden;
		background: #8881;
		border-radius: 12px;
	}
</style>
