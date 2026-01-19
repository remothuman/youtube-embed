// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces

// Umami analytics global (loaded via script tag)
interface UmamiTrackProps {
	title?: string;
	url?: string;
	referrer?: string;
	hostname?: string;
	language?: string;
	screen?: string;
	// Allow custom properties
	[key: string]: unknown;
}

interface Umami {
	track(callback: (props: UmamiTrackProps) => UmamiTrackProps): void;
	track(eventName: string, data?: Record<string, unknown>): void;
}

declare global {
	namespace App {
		// interface Error {}
		// interface Locals {}
		// interface PageData {}
		// interface Platform {}
	}

	// eslint-disable-next-line no-var
	var umami: Umami | undefined;

	// YouTube IFrame Player API types
	namespace YT {
		const PlayerState: {
			UNSTARTED: -1;
			ENDED: 0;
			PLAYING: 1;
			PAUSED: 2;
			BUFFERING: 3;
			CUED: 5;
		};

		interface PlayerOptions {
			videoId?: string;
			width?: number | string;
			height?: number | string;
			playerVars?: {
				autoplay?: 0 | 1;
				modestbranding?: 0 | 1;
				rel?: 0 | 1;
				controls?: 0 | 1;
				enablejsapi?: 0 | 1;
				origin?: string;
				[key: string]: unknown;
			};
			events?: {
				onReady?: (event: PlayerEvent) => void;
				onStateChange?: (event: OnStateChangeEvent) => void;
				onError?: (event: OnErrorEvent) => void;
			};
		}

		interface PlayerEvent {
			target: Player;
		}

		interface OnStateChangeEvent {
			target: Player;
			data: number;
		}

		interface OnErrorEvent {
			target: Player;
			data: number;
		}

		class Player {
			constructor(element: HTMLElement | string, options: PlayerOptions);
			playVideo(): void;
			pauseVideo(): void;
			stopVideo(): void;
			seekTo(seconds: number, allowSeekAhead: boolean): void;
			loadVideoById(videoId: string, startSeconds?: number): void;
			cueVideoById(videoId: string, startSeconds?: number): void;
			getCurrentTime(): number;
			getDuration(): number;
			getPlaybackRate(): number;
			setPlaybackRate(rate: number): void;
			getAvailablePlaybackRates(): number[];
			getPlayerState(): number;
			getVolume(): number;
			setVolume(volume: number): void;
			mute(): void;
			unMute(): void;
			isMuted(): boolean;
			destroy(): void;
		}
	}

	// eslint-disable-next-line no-var
	var onYouTubeIframeAPIReady: (() => void) | undefined;
}

export {};
