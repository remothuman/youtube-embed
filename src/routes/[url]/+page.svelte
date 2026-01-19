<script lang="ts">
	import { page } from '$app/stores';
	import { createQuery } from '@tanstack/svelte-query';
	import { onMount } from 'svelte';
	import ViewsLikesDislikes from './ViewsLikesDislikes.svelte';
	import { sendAnalyticsEvent } from '$lib/analytics';
	import YouTubePlayer from '$lib/components/YouTubePlayer.svelte';

	let videoId = $page.url.searchParams.get('v') as string; 
	
	const API_BASE = "https://yt-api-worker.cloudflare-473.workers.dev"

	const query = createQuery({
		queryKey: ['snippet', videoId],
		queryFn: () => {
			return fetch(`${API_BASE}/videos?part=snippet&id=${videoId}`)
				.then((r) => r.json())
				.then((r) => {
                    console.log("Youtube API Snippet Result", r)
					return r.items[0].snippet;
				});
		},
        staleTime: 1000 * 60 * 60, //might change this
        // gcTime: Infinity,
	});

    $: title = $query.data?.title

    // video url is hashed for user privacy
	onMount(() => {
		sendAnalyticsEvent("loadedVideoPage");
		setTimeout(() => {
			sendAnalyticsEvent("stayedOnVideoPageFor1Min")
		}, 1000 * 60)
		setTimeout(() => {
			sendAnalyticsEvent("stayedOnVideoPageFor5Min")
		}, 1000 * 60 * 5)
		setTimeout(() => {
			sendAnalyticsEvent("stayedOnVideoPageFor10Min")
		}, 1000 * 60 * 10)
	})
</script>

<main class="max-w-5xl mx-auto p-2">
    <br>
	<YouTubePlayer {videoId} />
    <h1 class="text-xl font-bold">
        {#if $query.isLoading}
		    Loading Title...
        {:else if $query.isError}
            <!-- Error fetching title: {$query.error.message} -->
        {:else if $query.isSuccess}
            {title}
        {/if}
    </h1>

    <ViewsLikesDislikes videoId={videoId} />


    <br>

    <a 
		href="https://youtube.ttools.io" 
		target="_blank" rel="noreferrer noopener"
		class="text-emerald-400 underline"
	> about </a> <br>
    <a 
		href="https://www.ttools.io" target="_blank" rel="noreferrer noopener"
		class="text-emerald-400 underline"
	> more tools </a>
</main>

<svelte:head>
    {#if $query.isSuccess}
        <title>{title} - YT Embed</title>
    {:else}
        <title>YT Embed - {videoId}</title>
    {/if}

	<!-- <meta name="description" content="Embedded Youtube Video of {title}"> -->
	<!-- ^^ would use if had ssr. VV This does work.     Will edit as functionality is added of course -->
	<meta name="description" content="Embedded Youtube Video of {videoId}. Includes dislike count. May bypass adblockblock">
</svelte:head>

