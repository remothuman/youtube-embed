// Minimal seek coordination to prevent SilenceSkipper and SponsorSkip
// from both calling seekTo() in the same frame when segments overlap

let lastSeekTime = 0;
const SEEK_DEBOUNCE_MS = 100;

export function canSeek(): boolean {
	return Date.now() - lastSeekTime >= SEEK_DEBOUNCE_MS;
}

export function markSeek(): void {
	lastSeekTime = Date.now();
}
