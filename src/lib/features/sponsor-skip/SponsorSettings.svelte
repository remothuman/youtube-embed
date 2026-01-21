<script lang="ts">
	import {
		type SponsorBlockSettings,
		type SponsorCategory,
		ALL_CATEGORIES,
		CATEGORY_LABELS
	} from './types';

	interface Props {
		settings: SponsorBlockSettings;
		onChange: (settings: SponsorBlockSettings) => void;
	}

	let { settings, onChange }: Props = $props();

	function setMode(mode: 'auto' | 'manual') {
		onChange({ ...settings, mode });
	}

	function toggleCategory(category: SponsorCategory) {
		const current = settings.skipCategories;
		const newCategories = current.includes(category)
			? current.filter((c) => c !== category)
			: [...current, category];

		onChange({ ...settings, skipCategories: newCategories });
	}
</script>

<div class="sponsor-settings text-sm space-y-3 p-2 bg-gray-800/50 rounded">
	<!-- Mode toggle -->
	<div class="flex items-center gap-2">
		<span class="text-gray-400">Mode:</span>
		<button
			class="px-2 py-0.5 rounded text-xs transition-colors"
			class:bg-emerald-600={settings.mode === 'auto'}
			class:text-white={settings.mode === 'auto'}
			class:bg-gray-700={settings.mode !== 'auto'}
			class:text-gray-300={settings.mode !== 'auto'}
			onclick={() => setMode('auto')}
		>
			Auto-skip
		</button>
		<button
			class="px-2 py-0.5 rounded text-xs transition-colors"
			class:bg-emerald-600={settings.mode === 'manual'}
			class:text-white={settings.mode === 'manual'}
			class:bg-gray-700={settings.mode !== 'manual'}
			class:text-gray-300={settings.mode !== 'manual'}
			onclick={() => setMode('manual')}
		>
			Show button
		</button>
	</div>

	<!-- Category checkboxes -->
	<div class="space-y-1">
		<span class="text-gray-400">Skip categories:</span>
		<div class="grid grid-cols-2 gap-1 mt-1">
			{#each ALL_CATEGORIES as category}
				<label class="flex items-center gap-1.5 text-gray-300 cursor-pointer hover:text-white">
					<input
						type="checkbox"
						checked={settings.skipCategories.includes(category)}
						onchange={() => toggleCategory(category)}
						class="rounded border-gray-600 bg-gray-700 text-emerald-500 focus:ring-emerald-500 focus:ring-offset-0"
					/>
					<span class="text-xs">{CATEGORY_LABELS[category]}</span>
				</label>
			{/each}
		</div>
	</div>
</div>
