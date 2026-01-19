<script lang="ts">
	import type { SilenceSegment, SilenceSettings } from '$lib/types/silence';

	interface Props {
		settings: SilenceSettings;
		segments: SilenceSegment[];
		videoDuration: number; // seconds
		onChange: (settings: SilenceSettings) => void;
		onDisable: () => void;
	}

	let { settings, segments, videoDuration, onChange, onDisable }: Props = $props();

	// Calculate time saved based on current settings
	function calculateTimeSaved(): { original: number; adjusted: number; saved: number } {
		const validSegments = segments.filter((s) => s.duration_ms >= settings.minSkipMs);
		const totalSkippedMs = validSegments.reduce((sum, seg) => {
			const skipDuration =
				seg.duration_ms - settings.timeBeforeSkipping - settings.timeAfterSkipping;
			return sum + Math.max(0, skipDuration);
		}, 0);

		const savedMs = settings.mode === 'speed' ? totalSkippedMs / 2 : totalSkippedMs;
		const savedSec = savedMs / 1000;

		return {
			original: videoDuration,
			adjusted: videoDuration - savedSec,
			saved: savedSec
		};
	}

	function formatTime(seconds: number): string {
		const mins = Math.floor(seconds / 60);
		const secs = Math.floor(seconds % 60);
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	let timeSaved = $derived(calculateTimeSaved());

	function handleModeChange(mode: 'skip' | 'speed') {
		onChange({ ...settings, mode });
	}

	function handleMinSkipChange(e: Event) {
		const value = parseInt((e.target as HTMLInputElement).value);
		onChange({ ...settings, minSkipMs: value });
	}

	function handleTimeBeforeChange(e: Event) {
		const value = parseInt((e.target as HTMLInputElement).value);
		onChange({ ...settings, timeBeforeSkipping: value });
	}

	function handleTimeAfterChange(e: Event) {
		const value = parseInt((e.target as HTMLInputElement).value);
		onChange({ ...settings, timeAfterSkipping: value });
	}
</script>

<div class="silence-skipper-active bg-gray-800/50 rounded p-3 text-sm space-y-3">
	<!-- Header with time saved and disable button -->
	<div class="flex items-center justify-between">
		<span class="text-emerald-400">
			{formatTime(timeSaved.original)} → {formatTime(timeSaved.adjusted)}
			<span class="text-emerald-300">(-{formatTime(timeSaved.saved)})</span>
		</span>
		<button class="text-gray-400 hover:text-gray-300 text-xs" onclick={onDisable}> disable </button>
	</div>

	<!-- Mode toggle -->
	<div class="flex items-center gap-2">
		<span class="text-gray-400">Mode:</span>
		<div class="flex gap-1">
			<button
				class="px-2 py-0.5 rounded text-xs transition-colors"
				class:bg-emerald-600={settings.mode === 'skip'}
				class:text-white={settings.mode === 'skip'}
				class:bg-gray-700={settings.mode !== 'skip'}
				class:text-gray-300={settings.mode !== 'skip'}
				onclick={() => handleModeChange('skip')}
			>
				Skip
			</button>
			<button
				class="px-2 py-0.5 rounded text-xs transition-colors"
				class:bg-emerald-600={settings.mode === 'speed'}
				class:text-white={settings.mode === 'speed'}
				class:bg-gray-700={settings.mode !== 'speed'}
				class:text-gray-300={settings.mode !== 'speed'}
				onclick={() => handleModeChange('speed')}
			>
				2x speed
			</button>
		</div>
	</div>

	<!-- Min silence slider -->
	<div class="space-y-1">
		<div class="flex items-center justify-between">
			<span class="text-gray-400">Min silence:</span>
			<span class="text-gray-300">{settings.minSkipMs}ms</span>
		</div>
		<input
			type="range"
			min="100"
			max="2000"
			step="100"
			value={settings.minSkipMs}
			oninput={handleMinSkipChange}
			class="w-full h-1 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
		/>
	</div>

	<!-- Time before/after inputs -->
	<div class="flex gap-4">
		<div class="flex-1 space-y-1">
			<label class="text-gray-400 text-xs block">
				Wait before skip
				<span class="flex items-center gap-1 mt-1">
					<input
						type="number"
						min="0"
						max="500"
						step="50"
						value={settings.timeBeforeSkipping}
						oninput={handleTimeBeforeChange}
						class="w-16 px-2 py-1 bg-gray-700 rounded text-gray-200 text-xs"
					/>
					<span class="text-gray-400 text-xs">ms</span>
				</span>
			</label>
		</div>
		<div class="flex-1 space-y-1">
			<label class="text-gray-400 text-xs block">
				End early by
				<span class="flex items-center gap-1 mt-1">
					<input
						type="number"
						min="0"
						max="500"
						step="50"
						value={settings.timeAfterSkipping}
						oninput={handleTimeAfterChange}
						class="w-16 px-2 py-1 bg-gray-700 rounded text-gray-200 text-xs"
					/>
					<span class="text-gray-400 text-xs">ms</span>
				</span>
			</label>
		</div>
	</div>

	<!-- Segment count -->
	<div class="text-gray-500 text-xs">
		{segments.filter((s) => s.duration_ms >= settings.minSkipMs).length} silence segments found
	</div>
</div>
