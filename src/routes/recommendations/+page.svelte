<script lang="ts">
	import { sendAnalyticsEvent } from "$lib/analytics.svelte";
	import { onMount } from "svelte";


    onMount(() => {
        sendAnalyticsEvent("loadedRecommendationsPage");
    })
</script>



<main class="max-w-5xl mx-auto p-2 pt-16">
    
    <h1 class="text-4xl font-bold underline decoration-4">
        Recommendations
    </h1>
    <p class="mt-4">
        Recommendations for tools to use alongside this site:
    </p>

    <ul class="mt-8 list-disc pl-5">
        <li>
            <p>
                <a href="https://github.com/gorhill/uBlock" target="_blank" rel="noreferrer noopener" data-umami-event="clicked ublock link">
                    Ublock Origin
                </a> 
                to block ads, trackers, and onscreen elements</p>
        </li>
        <li class="md:ml-20 ml-8">
            <p>
                Filter to block "related videos" popup when you pause: <br>
                <span class="quote">www.youtube.com##.ytp-pause-overlay</span> 
            </p>
        </li>

        <li class="mt-4">
            <p>
                <a href="https://sponsor.ajay.app/" target="_blank" rel="noreferrer noopener" data-umami-event="clicked sponsorblock link">
                    SponsorBlock
                </a>
                to skip over sponsors
            </p>
        </li>
    </ul>

    <br>
    <br>
    
    <h1 class="text-4xl font-bold underline decoration-4 mb-4">
        Information
    </h1>

    <p>
        To check if you are signed in while on this site (and therefore influencing your youtube algorithm if you have watch history on), 
        right click on the video and click account. My testing shows this works in chrome but not brave or firefox due to cookie isolation.
    </p>
    <p>
        The embed has "privacy enhanced mode" set to disabled.
    </p>
    
    <p class="mt-4" >
        This site is currently free for me to host at any scale (due to the core functionality being run as an SPA / client side only, and cloudflare pages offering a free cdn), so I will keep it running as long as I can.
    </p>

    <br>
    <br>

    <h1 class="text-4xl font-bold underline decoration-4 mb-4">
        Analytics
    </h1>
    <p>
        In order to tell if people are actually using this site, and to practice website administration, I have included a few different analytics services in this website. I have tried to keep it privacy respecting, and I don't collect what videos you watch. 
    </p>

    <p class="mt-4">
        These services are: google analytics (will likely be blocked by ublock origin and many adblockers automatically), umami analytics, cloudflare web analytics, and a custom made analytics service (currently broken due to planetscale free tier ending). I do not generally include google analytics on my other websites, but this is site is for viewing youtube so google has the data anyway I think.
    </p>

    <p class="mt-4">
        You can see the umami analytics <a href="https://umami.ttools.io/share/BvCzQbYVfvi9AECn/youtube.ttools.io" target="_blank" rel="noreferrer noopener" data-umami-event="clicked umami link">here</a>.
    </p>
    <!-- <p>
        I've also included my own analytics that ublock won't block by default. It sends a randomly generated clientId (saved in localstorage) to my servers about what you do: namely what pages you visit and if you stay on a video page for 1, 5, or 10 minutes. I don't include what specific videos you watch, just that you're watching something.
        I just want an idea if anyone is using my app yk, tracking this stuff is actually standard practice on the web as far as I can tell.
    </p> -->    
    <p class="mt-4">
        You can opt out of analytics by getting ublock origin, and adding analytics.cloudflare-473.workers.dev and umami.ttools.io to your blocklist.
        
        and/or adding umami.disabled=1 to your localstorage
    </p>
    <br>
    
    <br>
    <br>
</main>

<!-- <br class="mb-[100vh]"> -->

<svelte:head>
    <title>Recommendations - Youtube Embed Viewer</title>
    <meta name="description" content="Recommended tools / extensions to use along side youtube or Youtube Embed Viewer">
</svelte:head>

<style>
    main {
        font-size: 1.5rem;
    }
    a {
        color: #34d399;
        text-decoration: underline;
    }
    .quote {
        border-radius: 0.375rem;
        padding-left: 0.25rem;
        padding-right: 0.25rem;
        padding-top: 0;
        padding-bottom: 0;
        width: fit-content;
        background-color: rgb(48, 48, 48);
    }
</style>