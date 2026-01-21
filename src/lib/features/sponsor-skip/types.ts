// SponsorBlock API types
// API docs: https://wiki.sponsor.ajay.app/w/API_Docs

export type SponsorSegment = {
	segment: [number, number]; // [startSec, endSec]
	category: SponsorCategory;
	UUID: string;
};

export type SponsorCategory =
	| 'sponsor' // Paid promotion
	| 'selfpromo' // Unpaid self-promotion
	| 'interaction' // Subscribe/like reminders
	| 'intro' // Intro animation
	| 'outro' // Endcards/credits
	| 'preview' // Preview/recap
	| 'music_offtopic' // Non-music in music video
	| 'filler'; // Tangent/filler

export const ALL_CATEGORIES: readonly SponsorCategory[] = [
	'sponsor',
	'selfpromo',
	'interaction',
	'intro',
	'outro',
	'preview',
	'music_offtopic',
	'filler'
] as const;

export const CATEGORY_LABELS: Record<SponsorCategory, string> = {
	sponsor: 'Sponsor',
	selfpromo: 'Self-promotion',
	interaction: 'Interaction reminder',
	intro: 'Intro',
	outro: 'Outro',
	preview: 'Preview/Recap',
	music_offtopic: 'Non-music section',
	filler: 'Filler'
};

export const DEFAULT_ENABLED_CATEGORIES: SponsorCategory[] = ['sponsor', 'selfpromo'];

export type SponsorBlockMode = 'auto' | 'manual';

export type SponsorBlockSettings = {
	enabled: boolean;
	mode: SponsorBlockMode;
	skipCategories: SponsorCategory[];
};

export const DEFAULT_SETTINGS: SponsorBlockSettings = {
	enabled: true,
	mode: 'manual',
	skipCategories: [...DEFAULT_ENABLED_CATEGORIES]
};

export const STORAGE_KEY = 'yt-embed-sponsor-settings';
