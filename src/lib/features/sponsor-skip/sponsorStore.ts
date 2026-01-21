import { writable } from 'svelte/store';
import type { SponsorSegment } from './types';

// Current sponsor segment to skip (for manual mode overlay button)
// null = not in a sponsor segment
export const currentSponsorSegment = writable<SponsorSegment | null>(null);

// Callback when skip button is clicked
type SkipCallback = () => void;
let skipCallback: SkipCallback | null = null;

export function registerSkipCallback(cb: SkipCallback): void {
	skipCallback = cb;
}

export function unregisterSkipCallback(): void {
	skipCallback = null;
}

export function triggerSkip(): void {
	skipCallback?.();
}
