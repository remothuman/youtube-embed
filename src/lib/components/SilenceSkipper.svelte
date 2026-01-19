<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { createMutation, createQuery, useQueryClient } from '@tanstack/svelte-query';
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import {
		playerStore,
		seekTo,
		setPlayerPlaybackRate,
		getPlayerPlaybackRate
	} from '$lib/stores/playerStore';
	import { sendAnalyticsEvent } from '$lib/analytics';
	import { isToolActive, updateToolsParam } from '$lib/utils/videoToolsParams';
	import { SILENCE_API_URL } from '$lib/config';
	import {
		type SilenceSegment,
		type SilenceSettings,
		type SilenceResponse,
		DEFAULT_SETTINGS,
		STORAGE_KEY
	} from '$lib/types/silence';
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
	let isPolling = $state(false);

	// Skip state for speed mode
	let inSilence = $state(false);
	let originalRate = $state(1);

	// Track recently skipped segment to prevent re-triggering
	let recentlySkippedEndMs = $state<number | null>(null);

	// Debounce tracking for analytics
	let lastSkipTime = 0;

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
		// Reset playback rate if we were in speed mode
		if (inSilence) {
			setPlayerPlaybackRate(originalRate);
		}
		// Ensure polling stops
		isPolling = false;
	});

	// Save settings to localStorage
	function saveSettings() {
		if (browser) {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
		}
	}

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
			if (data.status === 'cached' || data.status === 'completed') {
				// Got segments immediately
				queryClient.setQueryData(['silence', videoId], data);
				isPolling = false;
			} else if (data.status === 'queued' || data.status === 'processing') {
				// Need to poll for status
				isPolling = true;
				sendAnalyticsEvent('silenceQueueJoined');
			}
		}
	});

	// Poll for status while processing
	const statusQuery = createQuery({
		queryKey: ['silence-status', videoId],
		queryFn: async (): Promise<SilenceResponse> => {
			const res = await fetch(`${SILENCE_API_URL}/silence/status?v=${videoId}`);
			if (!res.ok) throw new Error('Failed to fetch status');
			return res.json();
		},
		refetchInterval: (query) => {
			const data = query.state.data;
			if (data?.status === 'queued' || data?.status === 'processing') {
				return 2000; // Poll every 2 seconds
			}
			return false; // Stop polling
		},
		enabled: isPolling
	});

	// When status changes to completed, stop polling and store result
	$effect(() => {
		if ($statusQuery.data?.status === 'completed' || $statusQuery.data?.status === 'cached') {
			queryClient.setQueryData(['silence', videoId], $statusQuery.data);
			isPolling = false;
		} else if ($statusQuery.data?.status === 'failed') {
			isPolling = false;
		}
	});

	// Main query for cached/completed results
	const silenceQuery = createQuery({
		queryKey: ['silence', videoId],
		queryFn: async (): Promise<SilenceResponse> => {
			// This is a placeholder - data is set by mutation/status query
			const res = await fetch(`${SILENCE_API_URL}/silence/status?v=${videoId}`);
			if (!res.ok) throw new Error('Failed to fetch status');
			return res.json();
		},
		enabled: false, // Only populated via setQueryData
		staleTime: Infinity
	});

	// Get current response data
	let responseData = $derived($silenceQuery.data ?? $statusQuery.data ?? $submitMutation.data);
	let segments = $derived(responseData?.segments ?? null);
	let status = $derived(responseData?.status ?? 'not_found');
	let queuePosition = $derived(responseData?.position);

	// Filter segments by user settings
	function getFilteredSegments(): SilenceSegment[] {
		if (!segments) return [];
		return segments.filter((seg) => seg.duration_ms >= settings.minSkipMs);
	}

	// Skip/Speed logic - runs on time updates
	$effect(() => {
		if (!enabled || !segments?.length) {
			if (inSilence) {
				setPlayerPlaybackRate(originalRate);
				inSilence = false;
			}
			return;
		}

		const currentMs = $playerStore.currentTime * 1000;
		const { mode, timeBeforeSkipping, timeAfterSkipping } = settings;
		const validSegments = getFilteredSegments();

		// Find if we're in a silence segment (with margins applied)
		const inSegment = validSegments.find((seg) => {
			const actionStart = seg.start_ms + timeBeforeSkipping;
			const actionEnd = seg.end_ms - timeAfterSkipping;
			return currentMs >= actionStart && currentMs < actionEnd;
		});

		if (mode === 'skip' && inSegment) {
			// Check if we already skipped this segment (prevent re-triggering)
			const skipEndMs = inSegment.end_ms - timeAfterSkipping;
			if (skipEndMs !== recentlySkippedEndMs) {
				recentlySkippedEndMs = skipEndMs;
				seekTo(skipEndMs / 1000);
				trackSkip();
				// Clear after a short delay to allow skipping same segment if user seeks back
				setTimeout(() => {
					recentlySkippedEndMs = null;
				}, 1000);
			}
		} else if (mode === 'speed') {
			if (inSegment && !inSilence) {
				// Entering silence - speed up
				inSilence = true;
				originalRate = getPlayerPlaybackRate();
				setPlayerPlaybackRate(2);
			} else if (!inSegment && inSilence) {
				// Exiting silence - restore speed
				inSilence = false;
				setPlayerPlaybackRate(originalRate);
			}
		}
	});

	// Reset speed state on pause/seek
	$effect(() => {
		if ($playerStore.state !== 'playing' && inSilence) {
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
			if ($playerStore.duration > 0) {
				$submitMutation.mutate({ videoId, duration: $playerStore.duration });
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
		if ($playerStore.duration > 0) {
			$submitMutation.mutate({ videoId, duration: $playerStore.duration });
		}
	}

	// Watch for player ready to auto-submit if enabled via URL
	$effect(() => {
		if (
			enabled &&
			$playerStore.duration > 0 &&
			!$submitMutation.isPending &&
			!$submitMutation.isSuccess &&
			status === 'not_found'
		) {
			$submitMutation.mutate({ videoId, duration: $playerStore.duration });
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
	let videoDuration = $derived(responseData?.duration_sec ?? $playerStore.duration);

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
