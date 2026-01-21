<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import {
		currentTime,
		playerState,
		duration as durationStore,
		seekTo,
		setPlayerPlaybackRate,
		getPlayerPlaybackRate
	} from '$lib/stores/playerStore';
	import { canSeek, markSeek } from '$lib/features/shared/seekLock';
	import { sendAnalyticsEvent } from '$lib/analytics.svelte';
	import { isToolActive, updateToolsParam } from '$lib/features/shared/videoToolsParams';
	import { SILENCE_API_URL } from '$lib/config';
	import {
		type SilenceSegment,
		type SilenceSettings,
		type SilenceResponse,
		DEFAULT_SETTINGS,
		STORAGE_KEY
	} from './types';
	import SilenceSkipperActive from './SilenceSkipperActive.svelte';

	interface Props {
		videoId: string;
		showActiveUI?: boolean; // Whether to render the active UI (for placement flexibility)
	}

	let { videoId, showActiveUI = false }: Props = $props();

	const queryClient = useQueryClient();

	// Settings state
	let settings = $state<SilenceSettings>({ ...DEFAULT_SETTINGS });

	// UI state
	let enabled = $state(false);

	// Skip state for speed mode
	let inSilence = $state(false);
	let originalRate = $state(1);

	// Track recently skipped segment by ID to prevent re-triggering
	let recentlySkippedSegmentId = $state<string | null>(null);

	// Debounce tracking for analytics
	let lastSkipTime = 0;

	// Reset state when video changes
	$effect(() => {
		videoId; // Track videoId
		return () => {
			// Cleanup on videoId change
			$submitMutation.reset();
			recentlySkippedSegmentId = null;
			// Clear old query data for this video
			queryClient.removeQueries({ queryKey: ['silence-status'] });
			if (inSilence) {
				setPlayerPlaybackRate(originalRate);
				inSilence = false;
			}
		};
	});

	// Validate settings from localStorage
	function validateSettings(data: unknown): SilenceSettings {
		if (typeof data !== 'object' || data === null) return { ...DEFAULT_SETTINGS };
		const obj = data as Record<string, unknown>;
		return {
			mode: obj.mode === 'skip' || obj.mode === 'speed' ? obj.mode : DEFAULT_SETTINGS.mode,
			minSkipMs:
				typeof obj.minSkipMs === 'number' && obj.minSkipMs >= 100 && obj.minSkipMs <= 2000
					? obj.minSkipMs
					: DEFAULT_SETTINGS.minSkipMs,
			timeBeforeSkipping:
				typeof obj.timeBeforeSkipping === 'number' &&
				obj.timeBeforeSkipping >= 0 &&
				obj.timeBeforeSkipping <= 500
					? obj.timeBeforeSkipping
					: DEFAULT_SETTINGS.timeBeforeSkipping,
			timeAfterSkipping:
				typeof obj.timeAfterSkipping === 'number' &&
				obj.timeAfterSkipping >= 0 &&
				obj.timeAfterSkipping <= 500
					? obj.timeAfterSkipping
					: DEFAULT_SETTINGS.timeAfterSkipping
		};
	}

	// Load settings from localStorage and check URL param
	onMount(() => {
		if (browser) {
			const stored = localStorage.getItem(STORAGE_KEY);
			if (stored) {
				try {
					const parsed = JSON.parse(stored);
					settings = validateSettings(parsed);
				} catch {
					// Invalid JSON, use defaults
				}
			}

			// Check if silence tool is active in URL
			if (isToolActive($page.url, 'silence')) {
				enabled = true;
			}
		}
	});

	onDestroy(() => {
		// Always try to restore if in speed mode and rate is 2x
		if (settings.mode === 'speed' && (inSilence || getPlayerPlaybackRate() === 2)) {
			setPlayerPlaybackRate(originalRate || 1);
		}
	});

	// Save settings to localStorage
	function saveSettings() {
		if (browser) {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
		}
	}

	// Status polling query - uses data to control polling (not external state)
	const statusQuery = createQuery({
		get queryKey() { return ['silence-status', videoId]; },
		queryFn: async (): Promise<SilenceResponse> => {
			const res = await fetch(`${SILENCE_API_URL}/silence/status?v=${videoId}`);
			if (!res.ok) throw new Error('Failed to fetch status');
			return res.json();
		},
		enabled: false, // Manually triggered via refetch()
		refetchInterval: (query) => {
			const data = query.state.data;
			if (!data) return false; // Not started yet
			// Stop polling when completed, cached, failed, or not_found
			if (data.status === 'completed' || data.status === 'cached' ||
			    data.status === 'failed' || data.status === 'not_found') {
				return false;
			}
			// Poll every 2s while queued or processing
			return 2000;
		}
	});

	// Submit video for processing
	const submitMutation = createMutation({
		mutationFn: async ({ videoId, duration }: { videoId: string; duration: number }) => {
			const res = await fetch(
				`${SILENCE_API_URL}/silence/request?v=${videoId}&duration=${duration}`,
				{ method: 'POST' }
			);
			if (!res.ok) throw new Error('Failed to submit video');
			return res.json() as Promise<SilenceResponse>;
		},
		onSuccess: (data) => {
			if (data.status === 'queued' || data.status === 'processing') {
				sendAnalyticsEvent('silenceQueueJoined');
				// Seed the status query with initial data and start polling
				queryClient.setQueryData(['silence-status', videoId], data);
				$statusQuery.refetch();
			}
			// For cached/completed, mutation data is enough - no polling needed
		}
	});

	// Get current response data - prefer status query data when available
	let responseData = $derived($statusQuery.data ?? $submitMutation.data);
	let segments = $derived(responseData?.segments ?? null);
	let status = $derived(responseData?.status ?? 'not_found');
	let queuePosition = $derived(responseData?.position);

	// Filter segments by user settings - memoized to avoid recomputing on every time update
	let filteredSegments = $derived.by(() => {
		if (!segments) return [];
		const { timeBeforeSkipping, timeAfterSkipping, minSkipMs } = settings;
		const minMargins = timeBeforeSkipping + timeAfterSkipping;
		return segments.filter(
			(seg) => seg[2] >= minSkipMs && seg[2] > minMargins
		);
	});

	// Find current segment - derived to avoid repeated computation
	let currentSegment = $derived.by(() => {
		if (!enabled || !filteredSegments.length) return null;
		const currentMs = $currentTime * 1000;
		const { timeBeforeSkipping, timeAfterSkipping } = settings;
		return filteredSegments.find((seg) => {
			const actionStart = seg[0] + timeBeforeSkipping;
			const actionEnd = seg[1] - timeAfterSkipping;
			return currentMs >= actionStart && currentMs < actionEnd;
		}) ?? null;
	});

	// Skip mode: seek past silence segments
	$effect(() => {
		if (!enabled || settings.mode !== 'skip' || !currentSegment) return;

		const segmentId = `${currentSegment[0]}-${currentSegment[1]}`;
		if (segmentId === recentlySkippedSegmentId || !canSeek()) return;

		const skipEndMs = currentSegment[1] - settings.timeAfterSkipping;
		const didSeek = seekTo(skipEndMs / 1000);
		if (didSeek) {
			markSeek();
			recentlySkippedSegmentId = segmentId;
			trackSkip();
			setTimeout(() => {
				recentlySkippedSegmentId = null;
			}, 2000);
		}
	});

	// Speed mode: track segment entry/exit without reactive loops
	// Use $effect.pre to run before DOM updates, read currentSegment, compare with local tracking
	let wasInSegment = false;
	$effect(() => {
		if (!enabled || settings.mode !== 'speed') {
			// Cleanup: restore rate if we were in silence
			if (wasInSegment) {
				setPlayerPlaybackRate(originalRate);
				wasInSegment = false;
				inSilence = false;
			}
			return;
		}

		const nowInSegment = currentSegment !== null;

		if (nowInSegment && !wasInSegment) {
			// Entering silence - speed up
			wasInSegment = true;
			inSilence = true;
			originalRate = getPlayerPlaybackRate();
			setPlayerPlaybackRate(2);
		} else if (!nowInSegment && wasInSegment) {
			// Exiting silence - restore speed
			wasInSegment = false;
			inSilence = false;
			setPlayerPlaybackRate(originalRate);
		}
	});

	// Reset speed state on pause
	$effect(() => {
		if ($playerState !== 'playing' && inSilence) {
			wasInSegment = false;
			inSilence = false;
			setPlayerPlaybackRate(originalRate);
		}
	});

	function trackSkip() {
		const now = Date.now();
		// Debounce: only track once per 10 seconds
		if (now - lastSkipTime > 10000) {
			lastSkipTime = now;
			sendAnalyticsEvent('silenceSkipped');
		}
	}

	function toggleEnabled() {
		enabled = !enabled;

		if (enabled) {
			sendAnalyticsEvent('toolEnabled', 'silence');
			updateToolsParam($page.url, 'silence', true);

			// Submit for processing if we have duration
			if ($durationStore > 0) {
				$submitMutation.mutate({ videoId, duration: $durationStore });
			}
		} else {
			sendAnalyticsEvent('toolDisabled', 'silence');
			updateToolsParam($page.url, 'silence', false);

			// Reset speed if in speed mode
			if (inSilence) {
				setPlayerPlaybackRate(originalRate);
				inSilence = false;
			}
		}
	}

	function handleRetry() {
		if ($durationStore > 0) {
			$submitMutation.mutate({ videoId, duration: $durationStore });
		}
	}

	// Watch for player ready to auto-submit if enabled via URL
	$effect(() => {
		if (
			enabled &&
			$durationStore > 0 &&
			!$submitMutation.isPending &&
			!$submitMutation.isSuccess &&
			status === 'not_found'
		) {
			$submitMutation.mutate({ videoId, duration: $durationStore });
		}
	});

	// Settings change handler for active UI
	function handleSettingsChange(newSettings: SilenceSettings) {
		settings = newSettings;
		saveSettings();

		// Reset speed mode if switching to skip mode while in silence
		if (newSettings.mode === 'skip' && inSilence) {
			setPlayerPlaybackRate(originalRate);
			inSilence = false;
		}
	}

	// Video duration for active UI
	let videoDuration = $derived(responseData?.duration_sec ?? $durationStore);

	// Whether to show active UI
	let isReady = $derived(enabled && (status === 'completed' || status === 'cached') && segments !== null);

	// Determine display state
	let displayStatus = $derived.by(() => {
		if (!enabled) return 'off';
		if ($submitMutation.isPending) return 'submitting';
		if (status === 'queued') return 'queued';
		if (status === 'processing') return 'processing';
		if (status === 'completed' || status === 'cached') return 'ready';
		if (status === 'failed' || $submitMutation.isError) return 'error';
		return 'off';
	});
</script>

<!-- Dropdown toggle -->
<div class="silence-skipper-toggle">
	<button
		class="text-sm hover:text-emerald-300 transition-colors"
		class:text-emerald-400={enabled}
		class:text-gray-400={!enabled}
		onclick={toggleEnabled}
		disabled={!SILENCE_API_URL}
		title={!SILENCE_API_URL ? 'Service unavailable' : undefined}
	>
		{#if !SILENCE_API_URL}
			Skip silence <span class="text-yellow-500">⚠</span>
		{:else if displayStatus === 'off'}
			Skip silence
		{:else if displayStatus === 'submitting'}
			Skip silence ...
		{:else if displayStatus === 'queued'}
			Skip silence (queue: #{queuePosition ?? '?'})
		{:else if displayStatus === 'processing'}
			Skip silence (analyzing...)
		{:else if displayStatus === 'ready'}
			Skip silence ✓
		{:else if displayStatus === 'error'}
			<span>
				Skip silence <span class="text-yellow-500">⚠</span>
			</span>
		{/if}
	</button>

	{#if displayStatus === 'error'}
		<button class="text-sm text-gray-400 hover:text-gray-300 ml-2" onclick={handleRetry}>
			retry
		</button>
	{/if}
</div>

<!-- Active UI (rendered separately for placement flexibility) -->
{#if showActiveUI && isReady && segments}
	<SilenceSkipperActive
		{settings}
		{segments}
		{videoDuration}
		onChange={handleSettingsChange}
		onDisable={toggleEnabled}
	/>
{/if}
