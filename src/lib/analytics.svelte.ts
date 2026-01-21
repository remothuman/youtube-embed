import { browser} from '$app/environment';
import { onMount } from 'svelte';


// todo: add posthog maybe, can keep redaction (https://posthog.com/tutorials/web-redact-properties)

//  ----   code is mirrored in app.html   ----

// copied from mdn docs
async function hashMessage(message:string) {
    const msgUint8 = new TextEncoder().encode(message); // encode as (utf-8) Uint8Array
    const hashBuffer = await crypto.subtle.digest("SHA-256", msgUint8); // hash the message
    const hashArray = Array.from(new Uint8Array(hashBuffer)); // convert buffer to byte array
    const hashHex = hashArray
        .map((b) => b.toString(16).padStart(2, "0"))
        .join(""); // convert bytes to hex string
    return hashHex;
}

// redacts url past #, hashes query params, hashes page title
export async function getRedactedData() {
    //hash page title
    const pageTitle = document.title
    const redactedPageTitle = "hashed-" + await hashMessage(pageTitle)

    // hash query params  + redact past #
    async function redactSearchParams(searchParams:URLSearchParams) {
        for (const [key, value] of searchParams.entries()) {
            searchParams.set(key, await hashMessage(value))
        }
        return searchParams.toString()
    }
    const pageUrl = window.location.pathname
    const pageQueryParamsString = window.location.search
    const redactedPageUrl = (pageUrl + "?" + await redactSearchParams(new URLSearchParams(pageQueryParamsString))).split("#")[0]

    // hash referer's query params
    const referer = document.referrer
    const redactedRefererQueryParams = await redactSearchParams(new URLSearchParams(referer))
    const redactedRefererUrl = (referer + "?" + redactedRefererQueryParams).split("#")[0]



    return {redactedPageTitle, redactedPageUrl, redactedRefererUrl}
    
}

// --------


// function getClientId(){
//     if (!browser) {
//         return;
//     }

//     let cachedClientId = localStorage.getItem('analyticsClientId');
//     if (!cachedClientId) {
//         cachedClientId = crypto.randomUUID();
//         localStorage.setItem('analyticsClientId', cachedClientId);
//     }

//     console.log("clientId: ", cachedClientId)

//     return cachedClientId
// }

// const clientId = getClientId();


// const ANALYTICS_URL = 'https://analytics.cloudflare-473.workers.dev';

export async function sendAnalyticsEvent(eventName: string, details?: string) {
	// const url = details
	// 	? `${ANALYTICS_URL}?clientId="${clientId}"&eventName="${eventName}"&details="${details}"`
	// 	: `${ANALYTICS_URL}?clientId="${clientId}"&eventName="${eventName}"`;

	// await fetch(url);


    await new Promise(resolve => setTimeout(resolve, 300));

    const {redactedPageTitle, redactedPageUrl, redactedRefererUrl} = await getRedactedData();

    if (typeof umami === 'undefined') return;

    umami.track(props => {
        props.title = redactedPageTitle;
        props.url = redactedPageUrl;
        props.referrer = redactedRefererUrl;


        props.name = eventName;
        if (details) {
            props.details = details;
        }

        return props
    });

    
}


/*
Will send an event when:
    - user loads embedded video   (wont send the exact vid for now for privacy)
    - user stays on embedded video for 1,5,10 minutes
    - user loads homepage
    - user loads recommendations page
*/

export function runAnalyticsVideoPage() {
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
}
    