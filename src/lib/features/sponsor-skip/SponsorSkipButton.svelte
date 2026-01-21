<script lang="ts">
	import { currentSponsorSegment, triggerSkip } from './sponsorStore';
	import { CATEGORY_LABELS } from './types';

	// Read segment from store
	let segment = $derived($currentSponsorSegment);
	let categoryLabel = $derived(segment ? CATEGORY_LABELS[segment.category] : '');
</script>

{#if segment}
	<div class="sponsor-skip-overlay">
		<button class="skip-button" onclick={triggerSkip}>
			Skip {categoryLabel.toLowerCase()} →
		</button>
	</div>
{/if}

<style>
	.sponsor-skip-overlay {
		position: absolute;
		bottom: 60px; /* Above YouTube controls */
		right: 12px;
		z-index: 100;
		pointer-events: auto;
	}

	.skip-button {
		background: rgba(0, 0, 0, 0.75);
		color: white;
		border: 1px solid rgba(255, 255, 255, 0.3);
		padding: 8px 16px;
		border-radius: 4px;
		font-size: 14px;
		cursor: pointer;
		transition: all 0.2s ease;
		backdrop-filter: blur(4px);
	}

	.skip-button:hover {
		background: rgba(16, 185, 129, 0.9); /* emerald-500 */
		border-color: rgba(16, 185, 129, 1);
	}
</style>
