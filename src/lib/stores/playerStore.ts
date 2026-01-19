import { writable, derived, get } from 'svelte/store';

export type PlayerState = 'unstarted' | 'ended' | 'playing' | 'paused' | 'buffering' | 'cued';

// Map YouTube API state numbers to readable strings
const YT_STATE_MAP: Record<number, PlayerState> = {
	[-1]: 'unstarted',
	[0]: 'ended',
	[1]: 'playing',
	[2]: 'paused',
	[3]: 'buffering',
	[5]: 'cued'
};

export function ytStateToString(ytState: number): PlayerState {
	return YT_STATE_MAP[ytState] ?? 'unstarted';
}

// Core player state
export const currentTime = writable(0);
export const duration = writable(0);
export const playbackRate = writable(1);
export const playerState = writable<PlayerState>('unstarted');

// Derived: is currently playing
export const isPlaying = derived(playerState, ($state) => $state === 'playing');

// Combined store for convenience
export const playerStore = derived(
	[currentTime, duration, playbackRate, playerState],
	([$currentTime, $duration, $playbackRate, $playerState]) => ({
		currentTime: $currentTime,
		duration: $duration,
		playbackRate: $playbackRate,
		state: $playerState
	})
);

// Time update subscription for skip features
type TimeCallback = (timeSeconds: number) => void;
const timeSubscribers: Set<TimeCallback> = new Set();

export function subscribeToTime(callback: TimeCallback): () => void {
	timeSubscribers.add(callback);
	return () => timeSubscribers.delete(callback);
}

export function notifyTimeSubscribers(timeSeconds: number): void {
	timeSubscribers.forEach((cb) => cb(timeSeconds));
}

// Reset store (for video navigation)
export function resetPlayerStore(): void {
	currentTime.set(0);
	duration.set(0);
	playbackRate.set(1);
	playerState.set('unstarted');
}

// Player actions - registered by YouTubePlayer component
export type PlayerActions = {
	seekTo: (seconds: number) => void;
	setPlaybackRate: (rate: number) => void;
	getPlaybackRate: () => number;
};

let playerActions: PlayerActions | null = null;

export function registerPlayerActions(actions: PlayerActions): void {
	playerActions = actions;
}

export function unregisterPlayerActions(): void {
	playerActions = null;
}

export function seekTo(seconds: number): boolean {
	if (!playerActions) return false;
	playerActions.seekTo(seconds);
	return true;
}

export function setPlayerPlaybackRate(rate: number): void {
	playerActions?.setPlaybackRate(rate);
}

export function getPlayerPlaybackRate(): number {
	return playerActions?.getPlaybackRate() ?? 1;
}
