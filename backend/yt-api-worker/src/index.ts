/**
 * Welcome to Cloudflare Workers! This is your first worker.
 *
 * - Run `npm run dev` in your terminal to start a development server
 * - Open a browser tab at http://localhost:8787/ to see your worker in action
 * - Run `npm run deploy` to publish your worker
 *
 * Bind resources to your worker in `wrangler.jsonc`. After adding bindings, a type definition for the
 * `Env` object can be regenerated with `npm run cf-typegen`.
 *
 * Learn more at https://developers.cloudflare.com/workers/
 */

export default {
	async fetch(request, env, ctx): Promise<Response> {
		// CORS
		const corsResponse = handleCORS(request);
		if (corsResponse) { return corsResponse; }

		const url = new URL(request.url);
		const params = url.searchParams;

		// Main API wrapper
		// video endpoint (snippet)
		if (url.pathname != '/videos' && params.get('part') != 'snippet') {
			return withCors(new Response('Only support /videos?part=snippet', { status: 400 }));
		}
		const id = params.get('id');
		if (!id) {
			return withCors(new Response('No id provided', { status: 400 }));
		}

		const API_BASE = "https://www.googleapis.com/youtube/v3/"
		const API_KEY = env.YT_API_KEY;
		if (!API_KEY) {
			return withCors(new Response('No YT_API_KEY provided internally', { status: 500 }));
		}
		const apiResponse = await fetch(`${API_BASE}videos?part=snippet&id=${id}&key=${env.YT_API_KEY}`);
		return withCors(apiResponse);

	},
} satisfies ExportedHandler<Env>;


const corsHeaders = {
	'Access-Control-Allow-Origin': '*', // can change to http://yt.ttools.io
	'Access-Control-Allow-Methods': 'GET, OPTIONS',
	'Access-Control-Allow-Headers': 'Content-Type',
};

function handleCORS(request: Request) {

	// Handle CORS preflight
	if (request.method === 'OPTIONS') {
		return new Response(null, { headers: corsHeaders });
	}
	else {
		return null;
	}
}

function withCors(response: Response) {
	const headers = new Headers(response.headers);
	for (const [key, value] of Object.entries(corsHeaders)) {
		headers.set(key, value);
	}
	return new Response(response.body, {
		status: response.status,
		statusText: response.statusText,
		headers,
	});
}