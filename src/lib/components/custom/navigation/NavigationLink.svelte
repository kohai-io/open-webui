<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { settings } from '$lib/stores';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	export let href: string;
	export let label: string;
	export let compact = false;
	export let onNavigate: () => void = () => {};

	$: active = $page.url.pathname === href;
	$: activeClass = $settings?.highContrastMode
		? 'bg-black/[0.035] dark:bg-white/[0.06]'
		: 'bg-black/[0.035] dark:bg-white/[0.045]';
</script>

<!-- Match the upstream Sidebar rows in expanded and collapsed navigation. -->
<div class={compact ? '' : 'px-1 flex justify-center text-gray-700 dark:text-gray-300'}>
	<Tooltip content={compact ? label : ''} placement="right" className="flex grow">
		<a
			{href}
			aria-label={label}
			aria-current={active ? 'page' : undefined}
			draggable="false"
			class={compact
				? 'cursor-pointer flex size-8 items-center justify-center transition group'
				: `grow flex items-center space-x-2 rounded-xl px-2 py-1.5 transition ${active ? activeClass : 'hover:bg-gray-100 dark:hover:bg-gray-900'}`}
			on:click={(event) => {
				event.stopPropagation();
				if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
				event.preventDefault();
				goto(href);
				onNavigate();
			}}
		>
			<div
				class={compact
					? `self-center flex size-[calc(30px*var(--app-text-scale,1))] items-center justify-center rounded-lg transition ${active ? activeClass : 'group-hover:bg-gray-100 dark:group-hover:bg-gray-900'}`
					: 'self-center flex size-4 shrink-0 items-center justify-center'}
			>
				<slot />
			</div>
			{#if !compact}
				<div class="flex self-center translate-y-[0.5px]">
					<div class="self-center text-[0.8125rem] leading-5">{label}</div>
				</div>
			{/if}
		</a>
	</Tooltip>
</div>
