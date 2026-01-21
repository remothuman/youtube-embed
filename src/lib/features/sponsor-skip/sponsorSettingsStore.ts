import { writable, get } from 'svelte/store';
import { browser } from '$app/environment';
import {
	type SponsorBlockSettings,
	type SponsorCategory,
	ALL_CATEGORIES,
	DEFAULT_SETTINGS,
	DEFAULT_ENABLED_CATEGORIES,
	STORAGE_KEY
} from './types';

function validateSettings(data: unknown): SponsorBlockSettings {
	if (typeof data !== 'object' || data === null) return { ...DEFAULT_SETTINGS };
	const obj = data as Record<string, unknown>;
	return {
		enabled: typeof obj.enabled === 'boolean' ? obj.enabled : DEFAULT_SETTINGS.enabled,
		mode: obj.mode === 'auto' || obj.mode === 'manual' ? obj.mode : DEFAULT_SETTINGS.mode,
		skipCategories: Array.isArray(obj.skipCategories)
			? obj.skipCategories.filter(
					(c): c is SponsorCategory => ALL_CATEGORIES.includes(c as SponsorCategory)
				)
			: [...DEFAULT_ENABLED_CATEGORIES]
	};
}

function loadSettings(): SponsorBlockSettings {
	if (!browser) return { ...DEFAULT_SETTINGS };
	const stored = localStorage.getItem(STORAGE_KEY);
	if (!stored) return { ...DEFAULT_SETTINGS };
	try {
		return validateSettings(JSON.parse(stored));
	} catch {
		return { ...DEFAULT_SETTINGS };
	}
}

function createSponsorSettingsStore() {
	const { subscribe, set, update } = writable<SponsorBlockSettings>(loadSettings());

	function save(settings: SponsorBlockSettings) {
		if (browser) {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
		}
	}

	return {
		subscribe,
		set: (value: SponsorBlockSettings) => {
			set(value);
			save(value);
		},
		update: (fn: (s: SponsorBlockSettings) => SponsorBlockSettings) => {
			update((current) => {
				const next = fn(current);
				save(next);
				return next;
			});
		},
		get: () => get({ subscribe })
	};
}

export const sponsorSettings = createSponsorSettingsStore();
