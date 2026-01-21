<script lang="ts">
	import { sendAnalyticsEvent } from "$lib/analytics.svelte";
	import { onMount } from "svelte";


    onMount(() => {
        sendAnalyticsEvent("loadedMethodsPage");
    })

    
</script>



<main class="max-w-[65rem] mx-auto p-2 pt-16">
    
    <h1 class="text-3xl font-bold underline decoration-4">
        Methods To Get Around The Youtube Adblock Ban
    </h1>

    <ol class="mt-8 list-decimal pl-5">
        <li>
            Replace the 
            <q>.com</q> in a youtube url with  <q>.ttools.io</q>.
            <span>&nbsp;&nbsp;&nbsp;</span> 
            Video will play unblocked (+ see dislike count)
        </li>

        <li class="mt-3.5">
            Replace the <q>/watch?v=</q> in a youtube url with  <q>/embed/</q>.    
            <span>&nbsp;&nbsp;&nbsp;</span> 
            Video will play unblocked in full window.
        </li>

        <br>

        <li>
            Switch Browsers. Sometimes youtube will block only some of your browsers. Different people report different browsers being blocked. I recommend trying brave browser which has adblock built in.
        </li>
        <li class="mt-3.5">
            Sign out of youtube or open the link in incognito mode.
        </li>
        
        <br>

        <li>
            Use <a href="https://github.com/FraserChapman/plunger" target="_blank" rel="noreferrer noopener">this</a> extension, it will replace your youtube player with an embed right on the youtube.com, thereby unblocking your video
        </li>
        <li class="mt-3.5">
            Get 
            <a href="https://github.com/gorhill/uBlock">Ublock Origin</a>
            and check if its updated with 
            <a href="https://drhyperion451.github.io/does-uBO-bypass-yt/"
                target="_blank" rel="noreferrer noopener"
            >
                this link</a>.
            This is supposed to work but it does not always work for me.
        </li>

        <!-- <br> -->

        <li class="mt-3.5">
            Use 
            <a href="https://chromewebstore.google.com/detail/ad-speedup-skip-video-ads/pcjlckhhhmlefmobnnoolakplfppdchi">
                this
            </a>
            extension. It will speed up ads on youtube by 16x and mute them, while not technically blocking them.
        </li>

        <br>
        
        <li>
            View the video on an alternative youtube frontend website, such as 
            <a href="https://redirect.invidious.io/">Invidious</a>. 
        </li>
        <li class="mt-3.5">
            View the video on an alternative youtube frontend app, such as
            <a href="https://newpipe.net/"> NewPipe</a> or
            <a href="https://grayjay.app/">Grayjay</a>. Or Revanced.
        </li>
        <li class="mt-3.5">
            Check if the youtube channel is mirrored on a youtube competitor, 
            such as 
            <a href="https://lbry.com">LBRY</a>/<a href="https://odysee.com">Odysee</a>, 
            <a href="https://rumble.com">Rumble</a>, 
            or 
            <a href="https://nebula.tv/">Nebula</a>.
        </li>
        

        
        <br>
        
        <li>
            <a href="https://www.youtube.com/premium">
                Pay for youtube premium</a>.
        </li>
    </ol>
    
    <br>

    <p>
        <span class="font-bold">Suggest other methods: </span>
        Email me at 
        <a href="mailto:suggest@ttools.io">contact@ttools.io</a>, 
        or comment down below.
        
    </p>
    <p class="mt-8">Youtube, if you feel this page violates your terms of service or the law, contact me, I will take it down.</p>
    
    <!-- <br> -->
    
    <br>
    <h2 class="text-2xl font-bold underline decoration-2">Comments </h2>
    <div id="cusdis_thread"
        data-host="https://cusdis.com"
        data-app-id="55d5f35b-064f-40fb-8940-5c1eb9772732"
        data-page-id="Methods To Get Around Youtube Adblock Ban"
        data-page-url="https://youtube.ttools.io/methods"
        data-page-title="Methods To Get Around Youtube Adblock Ban"
        data-theme="dark"
    >
    </div>

    <br class="mb-[40vh]">
    
    
</main>



<!-- <br class="mb-[100vh]"> -->

<svelte:head>
    <title>Methods To Get Around Youtube Adblock Ban</title>
    <meta name="description" content="Recommended tools / extensions to use along side youtube or Youtube Embed Viewer">
    <!-- <script async src="https://cusdis.com/js/cusdis.es.js"></script> -->
</svelte:head>

<style>
    main {
        font-size: 1.4rem;
    }
    a {
        color: #34d399;
        text-decoration: underline;
    }
    q {
        border-radius: 0.375rem;
        padding: 0;
        width: fit-content;
        background-color: rgb(60, 60, 60);
    }
    ol > br {
        margin-top: 0.25rem;
    }
</style>