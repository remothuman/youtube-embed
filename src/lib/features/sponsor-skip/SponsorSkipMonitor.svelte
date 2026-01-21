<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { createQuery } from '@tanstack/svelte-query';
	import { playerStore, seekTo } from '$lib/stores/playerStore';
	import { canSeek, markSeek } from '$lib/features/shared/seekLock';
	import { currentSponsorSegment, registerSkipCallback, unregisterSkipCallback } from './sponsorStore';
	import { sponsorSettings } from './sponsorSettingsStore';
	import { sendAnalyticsEvent } from '$lib/analytics.svelte';
	import { type SponsorSegment, ALL_CATEGORIES } from './types';

	interface Props {
		videoId: string;
	}

	let { videoId }: Props = $props();

	// Track current segment locally for skip logic
	let currentSegmentForSkip = $state<SponsorSegment | null>(null);

	// Track recently skipped segments to prevent re-triggering
	let recentlySkipped = $state<Set<string>>(new Set());

	// Debounce tracking for analytics
	let lastAutoSkipTime = 0;

	// Fetch segments from SponsorBlock API
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

	function getEnabledSegments(): SponsorSegment[] {
		if (!$sponsorQuery.data) return [];
		return $sponsorQuery.data.filter((seg) =>
			$sponsorSettings.skipCategories.includes(seg.category)
		);
	}

	function handleManualSkip() {
		if (currentSegmentForSkip) {
			const [, end] = currentSegmentForSkip.segment;
			seekTo(end);
			sendAnalyticsEvent('sponsorSkipped', 'manual');
			currentSegmentForSkip = null;
			currentSponsorSegment.set(null);
		}
	}

	function trackAutoSkip() {
		const now = Date.now();
		if (now - lastAutoSkipTime > 10000) {
			lastAutoSkipTime = now;
			sendAnalyticsEvent('sponsorSkipped', 'auto');
		}
	}

	onMount(() => {
		registerSkipCallback(handleManualSkip);
	});

	onDestroy(() => {
		unregisterSkipCallback();
		currentSponsorSegment.set(null);
	});

	// Skip logic - runs on time updates
	$effect(() => {
		if (!$sponsorSettings.enabled || !$sponsorQuery.data?.length) {
			currentSegmentForSkip = null;
			currentSponsorSegment.set(null);
			return;
		}

		const currentSec = $playerStore.currentTime;
		const enabledSegments = getEnabledSegments();

		const inSegment = enabledSegments.find((seg) => {
			const [start, end] = seg.segment;
			return currentSec >= start && currentSec < end - 0.1;
		});

		if ($sponsorSettings.mode === 'auto' && inSegment && !recentlySkipped.has(inSegment.UUID) && canSeek()) {
			const [, end] = inSegment.segment;
			const didSeek = seekTo(end);
			if (didSeek) {
				markSeek();
				recentlySkipped.add(inSegment.UUID);
				trackAutoSkip();
				setTimeout(() => {
					recentlySkipped.delete(inSegment.UUID);
					recentlySkipped = recentlySkipped;
				}, 2000);
			}
			currentSegmentForSkip = null;
			currentSponsorSegment.set(null);
		} else {
			currentSegmentForSkip = inSegment ?? null;
			currentSponsorSegment.set($sponsorSettings.mode === 'manual' ? (inSegment ?? null) : null);
		}
	});
</script>
