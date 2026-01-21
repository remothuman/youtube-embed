<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { sponsorSettings } from './sponsorSettingsStore';
	import { sendAnalyticsEvent } from '$lib/analytics.svelte';
	import { type SponsorBlockSettings, type SponsorSegment, ALL_CATEGORIES } from './types';
	import SponsorSettings from './SponsorSettings.svelte';

	interface Props {
		videoId: string;
	}

	let { videoId }: Props = $props();

	let showSettings = $state(false);

	// Query for segment count display (same query key as monitor, will share cache)
	const sponsorQuery = createQuery({
		get queryKey() { return ['sponsorblock', videoId]; },
		queryFn: async (): Promise<SponsorSegment[]> => {
			const res = await fetch(
				`https://sponsor.ajay.app/api/skipSegments?videoID=${videoId}&categories=${encodeURIComponent(JSON.stringify([...ALL_CATEGORIES]))}`
			);
			if (res.status === 404) return [];
			if (!res.ok) throw new Error('Failed to fetch sponsor segments');
			return res.json();
		},
		staleTime: 1000 * 60 * 60,
		enabled: $sponsorSettings.enabled
	});

	function toggleEnabled() {
		const wasEnabled = $sponsorSettings.enabled;
		sponsorSettings.update((s) => ({ ...s, enabled: !s.enabled }));
		if (!wasEnabled) {
			sendAnalyticsEvent('toolEnabled', 'sponsors');
		} else {
			sendAnalyticsEvent('toolDisabled', 'sponsors');
		}
	}

	function handleSettingsChange(newSettings: SponsorBlockSettings) {
		sponsorSettings.set(newSettings);
	}

	let segmentCount = $derived($sponsorQuery.data?.length ?? 0);
</script>

<div class="sponsor-skip-toggle flex items-center gap-2">
	<button
		class="text-sm hover:text-emerald-300 transition-colors"
		class:text-emerald-400={$sponsorSettings.enabled}
		class:text-gray-400={!$sponsorSettings.enabled}
		onclick={toggleEnabled}
	>
		{#if !$sponsorSettings.enabled}
			Skip sponsors
		{:else if $sponsorQuery.isLoading}
			Skip sponsors ...
		{:else if $sponsorQuery.isError}
			Skip sponsors <span class="text-yellow-500" title="Error fetching segments">⚠</span>
		{:else if segmentCount === 0}
			Skip sponsors (none found)
		{:else}
			Skip sponsors ✓
		{/if}
	</button>

	{#if $sponsorSettings.enabled}
		<button
			class="text-gray-400 hover:text-gray-300 text-sm"
			onclick={() => (showSettings = !showSettings)}
			title="Settings"
		>
			⚙
		</button>
	{/if}
</div>

{#if showSettings && $sponsorSettings.enabled}
	<div class="mt-2 ml-4">
		<SponsorSettings settings={$sponsorSettings} onChange={handleSettingsChange} />
	</div>
{/if}
