// Silence detection API types

// Compact array format: [start_ms, end_ms, duration_ms]
export type SilenceSegment = [number, number, number];

export type SilenceMode = 'skip' | 'speed';

export type SilenceSettings = {
	mode: SilenceMode;
	minSkipMs: number; // minimum silence duration to act on (default 500)
	timeBeforeSkipping: number; // wait this long into silence before skipping (default 0)
	timeAfterSkipping: number; // resume this early before silence ends (default 100)
};

export const DEFAULT_SETTINGS: SilenceSettings = {
	mode: 'skip',
	minSkipMs: 500,
	timeBeforeSkipping: 0,
	timeAfterSkipping: 100
};

export const STORAGE_KEY = 'yt-embed-silence-settings';

// Backend response types
export type SilenceStatus =
	| 'not_found'
	| 'cached'
	| 'queued'
	| 'processing'
	| 'completed'
	| 'failed'
	| 'error';

export type SilenceResponse = {
	status: SilenceStatus;
	segments?: SilenceSegment[];
	duration_sec?: number;
	position?: number;
	error?: string;
	retry_after?: number;
};
