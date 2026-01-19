<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import {
		currentTime,
		duration,
		playbackRate,
		playerState,
		ytStateToString,
		notifyTimeSubscribers,
		resetPlayerStore
	} from '$lib/stores/playerStore';

	interface Props {
		videoId: string;
	}

	let { videoId }: Props = $props();

	let playerElement: HTMLDivElement;
	let player: YT.Player | null = null;
	let timeInterval: ReturnType<typeof setInterval> | null = null;
	let apiReady = $state(false);
	let initializedVideoId: string | null = null; // Track which videoId the player was initialized with

	// Load YouTube IFrame API script
	function loadYouTubeAPI(): Promise<void> {
		return new Promise((resolve) => {
			// Already loaded
			if (window.YT && window.YT.Player) {
				resolve();
				return;
			}

			// Check if script is already being loaded (by another instance or previous load)
			const existingScript = document.querySelector('script[src="https://www.youtube.com/iframe_api"]');

			if (window.onYouTubeIframeAPIReady || existingScript) {
				const existingCallback = window.onYouTubeIframeAPIReady;
				window.onYouTubeIframeAPIReady = () => {
					existingCallback?.();
					resolve();
				};
				return;
			}

			// Start loading
			window.onYouTubeIframeAPIReady = () => {
				resolve();
			};

			const script = document.createElement('script');
			script.src = 'https://www.youtube.com/iframe_api';
			document.head.appendChild(script);
		});
	}

	function initPlayer(): void {
		if (!playerElement || !window.YT || player) return;

		player = new window.YT.Player(playerElement, {
			videoId,
			playerVars: {
				autoplay: 0,
				modestbranding: 1,
				rel: 0
			},
			events: {
				onReady: handleReady,
				onStateChange: handleStateChange
			}
		});
		initializedVideoId = videoId;
	}

	function handleReady(event: YT.PlayerEvent): void {
		if (!player || typeof player.getDuration !== 'function') return;
		duration.set(player.getDuration());
		playbackRate.set(player.getPlaybackRate?.() ?? 1);
	}

	function handleStateChange(event: YT.OnStateChangeEvent): void {
		const state = ytStateToString(event.data);
		playerState.set(state);

		if (state === 'playing') {
			startTimePolling();
		} else {
			stopTimePolling();
		}
	}

	function startTimePolling(): void {
		stopTimePolling();
		timeInterval = setInterval(() => {
			if (!player || typeof player.getCurrentTime !== 'function') return;
			const time = player.getCurrentTime();
			currentTime.set(time);
			notifyTimeSubscribers(time);
		}, 100);
	}

	function stopTimePolling(): void {
		if (timeInterval) {
			clearInterval(timeInterval);
			timeInterval = null;
		}
	}

	// Exposed player controls (guarded)
	export function play(): void {
		if (player && typeof player.playVideo === 'function') {
			player.playVideo();
		}
	}

	export function pause(): void {
		if (player && typeof player.pauseVideo === 'function') {
			player.pauseVideo();
		}
	}

	export function seekTo(seconds: number): void {
		if (player && typeof player.seekTo === 'function') {
			player.seekTo(seconds, true);
		}
	}

	export function getCurrentTime(): number {
		if (player && typeof player.getCurrentTime === 'function') {
			return player.getCurrentTime();
		}
		return 0;
	}

	export function setPlaybackRate(rate: number): void {
		if (player && typeof player.setPlaybackRate === 'function') {
			player.setPlaybackRate(rate);
			playbackRate.set(rate);
		}
	}

	export function getPlaybackRate(): number {
		if (player && typeof player.getPlaybackRate === 'function') {
			return player.getPlaybackRate();
		}
		return 1;
	}

	export function getDuration(): number {
		if (player && typeof player.getDuration === 'function') {
			return player.getDuration();
		}
		return 0;
	}

	onMount(async () => {
		resetPlayerStore();
		await loadYouTubeAPI();
		apiReady = true;
		initPlayer();
	});

	onDestroy(() => {
		stopTimePolling();
		if (player && typeof player.destroy === 'function') {
			player.destroy();
		}
		player = null;
	});

	// Handle videoId changes (only load if actually different from current)
	$effect(() => {
		if (apiReady && videoId && videoId !== initializedVideoId) {
			if (player && typeof player.loadVideoById === 'function') {
				resetPlayerStore();
				player.loadVideoById(videoId);
				initializedVideoId = videoId;
			}
		}
	});
</script>

<div class="youtube-player-wrapper">
	<div bind:this={playerElement} class="youtube-player"></div>
</div>

<style>
	.youtube-player-wrapper {
		position: relative;
		width: 100%;
		height: 0;
		padding-bottom: 56.25%; /* 16:9 aspect ratio */
	}

	.youtube-player-wrapper :global(iframe) {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		outline: none;
	}
</style>
