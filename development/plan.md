# Video Tools Implementation Plan

## Phase -1: Svelte 5 Upgrade

*Prerequisite for modern reactivity patterns used throughout this plan.*

### -1.1 Upgrade Dependencies
- Update `svelte` to `^5.0.0` in package.json
- Update `@sveltejs/kit` to latest compatible version
- Update `svelte-check` and other svelte-related devDeps
- Run `pnpm install`

### -1.2 Verify Backwards Compatibility
- Run `pnpm check` to catch any type errors
- Test existing pages still work (home, video page, shorts)
- Svelte 5 is backwards compatible with Svelte 4 syntax
- New components will use Svelte 5 runes (`$state`, `$effect`, `$derived`)

---

## Phase 0: Foundation - YouTube IFrame Player API

*Reference implementation: `backend/yt-silence-skipper-demo/player.html`*

### 0.1 Create YouTube Player Component
- Create `src/lib/components/YouTubePlayer.svelte`
- Load YouTube IFrame API script dynamically (`https://www.youtube.com/iframe_api`)
- Use `window.onYouTubeIframeAPIReady` callback pattern for initialization
- Initialize player with `new YT.Player()` using existing videoId
- PlayerVars: `{ autoplay: 0, modestbranding: 1, rel: 0 }`
- Expose player controls: play, pause, seekTo, getCurrentTime, setPlaybackRate, getPlaybackRate
- Guard all player method calls: `if (!player || typeof player.getCurrentTime !== 'function') return`
- Maintain current responsive 16:9 aspect ratio styling

### 0.2 Player Store
- Create `src/lib/stores/playerStore.ts`
- State: `{ currentTime, duration, playbackRate, playerState }`
- playerState enum: `'unstarted' | 'ended' | 'playing' | 'paused' | 'buffering' | 'cued'` (maps to YT.PlayerState)
- Time polling: 100ms interval when PLAYING, stop on pause/end/buffer
- Cleanup pattern: always `clearInterval` before starting new interval (see demo `startTimeCheck`)
- Export `subscribeToTime(callback)` for skip features
- Cleanup interval on component destroy

### 0.3 Integrate into Video Page
- Replace raw iframe in `src/routes/[url]/+page.svelte` with YouTubePlayer component
- Wire up `onReady` and `onStateChange` events
- Test: verify no visual regression, player loads correctly

---

## Phase 1: Minimal UI Shell

### 1.1 Tools Dropdown Component
- Create `src/lib/components/VideoTools.svelte`
- Replace "more tools" link with expandable "▸ video tools" text
- Collapsed by default, expands to "▾ video tools" on click
- Empty container for now - features will add their own UI
- Minimal styling matching existing emerald link aesthetic

### 1.2 Active Tools Area
- Add slot/container below video for active tool UI
- Initially empty - populated when tools are enabled
- Each feature owns its own top-level UI component

### 1.3 URL Param Foundation
- Read `?tools=` param on page load
- Write helper: `updateToolsParam(toolName, active)`
- Format: `?tools=silence` (comma-separated, for tools not on by default)
- Sponsors enabled by default, doesn't need URL param
- No state store yet - features will manage their own state

---

## Phase 2: SponsorBlock (Skip Sponsors)

*Enabled by default in manual mode (shows skip button overlay when in sponsor segment). No backend needed - uses SponsorBlock public API.*

### 2.1 Types
```typescript
// src/lib/types/sponsorBlock.ts
type SponsorSegment = {
  segment: [number, number]; // [startSec, endSec]
  category: string;
  UUID: string;
}

type SponsorBlockSettings = {
  mode: 'auto' | 'manual';  // auto = skip immediately, manual = show skip button
  skipCategories: string[];
}

// Categories from SponsorBlock API
const ALL_CATEGORIES = [
  'sponsor',      // Paid promotion
  'selfpromo',    // Unpaid self-promotion
  'interaction',  // Subscribe/like reminders
  'intro',        // Intro animation
  'outro',        // Endcards/credits
  'preview',      // Preview/recap
  'music_offtopic', // Non-music in music video
  'filler'        // Tangent/filler
] as const;

const DEFAULT_ENABLED = ['sponsor', 'selfpromo'];
```

### 2.2 Data Fetching
- Create `src/lib/components/SponsorSkip.svelte`
- Fetch on page load (enabled by default)
- TanStack Query: `GET https://sponsor.ajay.app/api/skipSegments?videoID={videoId}`
- Query key: `['sponsorblock', videoId]`
- Handle 404 as "no segments" (not error)
- Long staleTime (segments rarely change)

### 2.3 Settings Persistence
- localStorage key: `yt-embed-sponsor-settings`
- Schema: `{ mode: 'auto' | 'manual', skipCategories: string[] }`
- Defaults: `{ mode: 'manual', skipCategories: ['sponsor', 'selfpromo'] }`
- Load on mount, save on change

### 2.4 Skip Logic
```typescript
let currentSponsor: SponsorSegment | null = null;  // for manual mode UI

$effect(() => {
  if (!active || !segments.length) return;

  const currentSec = $playerStore.currentTime;
  const enabledSegments = segments.filter(s =>
    settings.skipCategories.includes(s.category)
  );

  // Find current sponsor segment (if any)
  const inSegment = enabledSegments.find(seg => {
    const [start, end] = seg.segment;
    return currentSec >= start && currentSec < end - 0.1;
  });

  if (settings.mode === 'auto' && inSegment) {
    const [, end] = inSegment.segment;
    player.seekTo(end);
    trackSkip();
  }

  // For manual mode: expose current segment to UI
  currentSponsor = inSegment ?? null;
});
```

### 2.5 UI Components

**In Dropdown (`VideoTools.svelte`):**
- Toggle: "Skip sponsors" (on by default, user can disable)
- Gear icon → settings popover:
  - Mode toggle: "Auto-skip" | "Show button" (default: show button)
  - Category checkboxes

**Top Level (auto mode, when active):**
- Create `src/lib/components/SponsorSkipActive.svelte`
- Shows indicator that auto-skip is active: "SponsorBlock ✓ (3 segments)"
- Click to disable

**Overlay on Player (manual mode, when in sponsor segment):**
- Create `src/lib/components/SponsorSkipButton.svelte`
- Positioned bottom-right of player, above YouTube controls
- Only visible when `currentSponsor !== null`
- Button: "Skip sponsor →" with category label "(selfpromo)"
- Semi-transparent background, fades in/out
- On click: `player.seekTo(currentSponsor.segment[1])`

**UI States:**
- Default: enabled, manual mode (button appears only when in sponsor segment)
- Off: user explicitly disabled in dropdown
- Loading: "Skip sponsors ..." in dropdown
- Ready (auto mode): top-level "SponsorBlock ✓ (3)" indicator
- Ready (manual mode): nothing until sponsor segment, then overlay button
- Ready (no segments): "Skip sponsors (none found)" in dropdown
- Error: "Skip sponsors ⚠" with tooltip

### 2.6 Analytics
- `sendAnalyticsEvent('toolEnabled', 'sponsors')` when user re-enables (not on page load - it's default on)
- `sendAnalyticsEvent('toolDisabled', 'sponsors')` when user disables
- `sendAnalyticsEvent('sponsorSkipped', 'auto')` on auto-skip (debounced 10s)
- `sendAnalyticsEvent('sponsorSkipped', 'manual')` on manual skip button click

### 2.7 URL State
- Sponsors enabled by default (no URL param needed)
- `?tools=-sponsors` to explicitly disable (negative prefix)
- Or: just don't use URL state for sponsors since it's default on

---

## Phase 3: Silence Skipper

*Most complex feature. Backend processes audio, frontend skips/speeds through silence.*

### 3.1 Backend: Silence Detection Service

Location: `backend/silence-service/`

#### 3.1.1 Project Setup
```
backend/silence-service/
├── main.py           # FastAPI app, routes, CORS
├── silence.py        # Detection logic
├── queue.py          # Background worker
├── db.py             # SQLite operations
├── requirements.txt
├── Dockerfile
└── railway.toml
```

Dependencies: `fastapi`, `uvicorn`, `yt-dlp`, `pydub`, `python-multipart`, `youtube-transcript-api`

#### 3.1.2 SQLite Schema
```sql
PRAGMA journal_mode=WAL;

CREATE TABLE silence_cache (
  video_id TEXT PRIMARY KEY,
  segments TEXT NOT NULL,      -- JSON array
  duration_sec REAL NOT NULL,  -- used for cache invalidation + time-saved calc
  created_at INTEGER NOT NULL
);
-- Cache is indefinite. Invalidate only if video duration changes (covers 99%+ of re-uploads/edits).

CREATE TABLE queue (
  video_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,        -- queued, processing, completed, failed
  position INTEGER,
  ip TEXT,
  submitted_at INTEGER,
  started_at INTEGER,
  error TEXT
);

CREATE TABLE rate_limits (
  ip TEXT PRIMARY KEY,
  request_count INTEGER,
  window_start INTEGER
);
-- Rate limit entries auto-pruned on access: DELETE WHERE window_start < now - 86400

CREATE INDEX idx_queue_status ON queue(status);
```

#### 3.1.3 Queue Worker
- Background thread started on app startup
- Polls queue every 2 seconds for `status='queued'` ordered by `position`
- Processing timeout: 5 minutes per video
- Max queue length: 50 (reject new submissions when full)
- On crash recovery: reset any `status='processing'` to `status='queued'`

```python
# queue.py
async def process_queue():
    while True:
        job = get_next_queued_job()
        if job:
            mark_processing(job.video_id)
            try:
                segments = await extract_silence_segments(job.video_id)
                cache_results(job.video_id, segments)
                mark_completed(job.video_id)
            except Exception as e:
                mark_failed(job.video_id, str(e))
        await asyncio.sleep(2)
```

#### 3.1.4 Silence Detection
```python
# silence.py
from pydub.silence import detect_silence as pydub_detect_silence

def extract_silence_segments(video_id: str) -> list[dict]:
    # Download audio (lowest quality for speed)
    ydl_opts = {
        'format': 'worstaudio/worst',
        'outtmpl': f'/tmp/{video_id}.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '64',  # low quality fine for silence detection
        }],
    }

    # Detect silence using pydub
    audio = AudioSegment.from_file(filepath)
    segments = pydub_detect_silence(
        audio,
        min_silence_len=100,    # detect all ≥100ms, frontend filters
        silence_thresh=-40,      # dBFS
        seek_step=10            # ms, accuracy vs speed tradeoff
    )

    # Cleanup temp file
    os.remove(filepath)

    return [
        {"start_ms": s, "end_ms": e, "duration_ms": e - s}
        for s, e in segments
    ]
```

#### 3.1.5 Endpoints

**CORS**: `Access-Control-Allow-Origin: *` (or restrict to `yt.ttools.io`)

**POST /silence/request**
```
Params: v (videoId), duration (seconds, from YouTube player API)
Rate limit: 5 NEW submissions per IP per hour (cached hits don't count)

Cache logic:
- If cached AND cached.duration_sec == request.duration: return cached
- If cached AND duration differs: invalidate cache, re-queue for processing
- If not cached: add to queue

Response cases:
- Cached (duration matches): { "status": "cached", "segments": [...], "duration_sec": 1234 }
- Already queued: { "status": "queued", "position": 3 }
- Already processing: { "status": "processing" }
- Added to queue: { "status": "queued", "position": 5 }
- Rate limited: { "status": "error", "error": "rate_limited", "retry_after": 3600 }
- Queue full: { "status": "error", "error": "queue_full" }
```

**GET /silence/status**
```
Params: v (videoId)
Frontend polls every 2-3s while waiting

Response cases:
- Not found: { "status": "not_found" }
- Queued: { "status": "queued", "position": 2 }
- Processing: { "status": "processing" }
- Completed: { "status": "completed", "segments": [...], "duration_sec": 1234 }
- Failed: { "status": "failed", "error": "Video unavailable" }
```

**GET /health**
```
Response: { "status": "ok", "queue_length": 3 }
```

#### 3.1.6 Error Handling
| Error | Response |
|-------|----------|
| Invalid video ID | `{"error": "invalid_video_id"}` |
| Video unavailable | `{"error": "video_unavailable"}` |
| Age-restricted | `{"error": "age_restricted"}` |
| Too long (>12hr) | `{"error": "video_too_long"}` |
| yt-dlp failure | `{"error": "download_failed", "detail": "..."}` |

#### 3.1.7 Deployment (Railway)
```toml
# railway.toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30

[[mounts]]
source = "silence-data"
destination = "/data"
```

Dockerfile must include `ffmpeg`. Database path: `/data/silence.db`

Environment: `PORT`, `DATABASE_PATH=/data/silence.db`

---

### 3.2 Frontend: Silence Skip Integration

#### 3.2.1 Types
```typescript
// src/lib/types/silence.ts
type SilenceSegment = {
  start_ms: number;
  end_ms: number;
  duration_ms: number;
}

type SilenceSettings = {
  mode: 'skip' | 'speed';
  minSkipMs: number;           // default 500 - minimum silence to act on
  timeBeforeSkipping: number;  // default 0 - wait this long into silence before skipping
  timeAfterSkipping: number;   // default 100 - resume this early before silence ends
}

type SilenceState = {
  active: boolean;
  loading: boolean;
  status: 'idle' | 'queued' | 'processing' | 'ready' | 'error';
  queuePosition?: number;
  segments: SilenceSegment[] | null;
  error?: string;
}
```

#### 3.2.2 Data Fetching
- Create `src/lib/components/SilenceSkipper.svelte`
- **Important:** Wait for player `onReady` before submitting - need `duration` from player API
- TanStack Query for `/silence/request` and `/silence/status`
- Mutation to submit, then poll status until ready
- Query key: `['silence', videoId]`

```typescript
const silenceMutation = createMutation({
  mutationFn: ({ videoId, duration }: { videoId: string; duration: number }) =>
    fetch(`${API}/silence/request?v=${videoId}&duration=${duration}`, { method: 'POST' }),
  onSuccess: (data) => {
    if (data.status === 'cached') {
      setSegments(data.segments);
    } else {
      startPolling();
    }
  }
});

// Call with duration from player
silenceMutation.mutate({ videoId, duration: $playerStore.duration });

// Poll while queued/processing
const statusQuery = createQuery({
  queryKey: ['silence-status', videoId],
  queryFn: () => fetch(`${API}/silence/status?v=${videoId}`),
  refetchInterval: (data) =>
    data?.status === 'queued' || data?.status === 'processing' ? 2000 : false,
  enabled: isPolling,
});
```

#### 3.2.3 Settings Persistence
- localStorage key: `yt-embed-silence-settings`
- Schema: `SilenceSettings`
- Defaults: `{ mode: 'skip', minSkipMs: 500, timeBeforeSkipping: 0, timeAfterSkipping: 100 }`

#### 3.2.4 Skip/Speed Logic
```typescript
let inSilence = false;  // track for speed mode
let originalRate = 1;

$effect(() => {
  if (!active || !segments) return;

  const currentMs = $playerStore.currentTime * 1000;
  const { mode, minSkipMs, timeBeforeSkipping, timeAfterSkipping } = settings;

  // Filter by user's minimum
  const validSegments = segments.filter(s => s.duration_ms >= minSkipMs);

  // Find if we're in a silence segment
  const inSegment = validSegments.find(seg => {
    const actionStart = seg.start_ms + timeBeforeSkipping;
    const actionEnd = seg.end_ms - timeAfterSkipping;
    return currentMs >= actionStart && currentMs < actionEnd;
  });

  if (mode === 'skip') {
    if (inSegment) {
      const skipTo = inSegment.end_ms - timeAfterSkipping;
      player.seekTo(skipTo / 1000);
      trackSkip();
    }
  } else if (mode === 'speed') {
    if (inSegment && !inSilence) {
      // Entering silence - speed up (2x is YouTube IFrame API max)
      inSilence = true;
      originalRate = player.getPlaybackRate();
      player.setPlaybackRate(2);
    } else if (!inSegment && inSilence) {
      // Exiting silence - restore speed
      inSilence = false;
      player.setPlaybackRate(originalRate);
    }
  }
});

// Reset speed state on pause/seek
$effect(() => {
  if ($playerStore.state !== 'playing' && inSilence) {
    inSilence = false;
    player.setPlaybackRate(originalRate);
  }
});

// Also reset when: tool disabled, mode switched to skip, or component destroyed
```

#### 3.2.5 UI Components

**In Dropdown:**
- Simple on/off toggle: "Skip silence"

**Top Level (when active):**
- Create `src/lib/components/SilenceSkipperActive.svelte`
- Mode toggle: "Skip" | "2x speed"
- Min skip: slider or input (100ms - 2000ms)
- Time before/after skipping: inputs (0ms - 500ms)
- Time saved display: "32:15 → 28:42 (-3:33)"
- Toggle off button

**UI States:**
- Off: "Skip silence" toggle
- Queued: "Skip silence (queue: #3)"
- Processing: "Skip silence (analyzing...)"
- Ready: "Skip silence ✓"
- Error: "Skip silence ⚠" with retry button

#### 3.2.6 Time Saved Calculation
```typescript
function calculateTimeSaved(segments: SilenceSegment[], settings: SilenceSettings) {
  const validSegments = segments.filter(s => s.duration_ms >= settings.minSkipMs);
  const totalSkippedMs = validSegments.reduce((sum, seg) => {
    const skipDuration = seg.duration_ms - settings.timeBeforeSkipping - settings.timeAfterSkipping;
    return sum + Math.max(0, skipDuration);
  }, 0);

  if (settings.mode === 'speed') {
    return totalSkippedMs / 2; // 2x speed = half the time
  }
  return totalSkippedMs;
}
```

#### 3.2.7 Analytics
- `sendAnalyticsEvent('toolEnabled', 'silence')`
- `sendAnalyticsEvent('toolDisabled', 'silence')`
- `sendAnalyticsEvent('silenceSkipped')` debounced 10s
- `sendAnalyticsEvent('silenceQueueJoined')` when entering queue

#### 3.2.8 URL State
- When enabled: add `silence` to `?tools=` param
- On page load with `?tools=silence`: activate and fetch immediately

---

## Phase 4: Copy Transcript

### 4.1 Backend Endpoint

Add to silence-service: `GET /transcript`

```python
# transcript.py
from youtube_transcript_api import YouTubeTranscriptApi

@app.get("/transcript")
async def get_transcript(v: str, timestamps: bool = False):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(v)
    except NoTranscriptFound:
        return JSONResponse(
            status_code=404,
            content={"error": "no_transcript", "message": "No captions available"}
        )

    if timestamps:
        lines = [f"[{format_time(t['start'])}] {t['text']}" for t in transcript]
        text = "\n".join(lines)
    else:
        text = " ".join(t['text'] for t in transcript)

    return {"video_id": v, "transcript": text}

def format_time(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    return f"{mins}:{secs:02d}"
```

Cache in SQLite (same pattern as silence cache, 7 day TTL).

### 4.2 Frontend

**In Dropdown only** (no top-level UI - action only, no persistent state):

- "Copy transcript ▸" submenu
- Two options: "Plain text" / "With timestamps"
- On click: fetch → copy to clipboard

```typescript
async function copyTranscript(withTimestamps: boolean) {
  setCopying(true);
  try {
    const res = await fetch(`${API}/transcript?v=${videoId}&timestamps=${withTimestamps}`);
    if (!res.ok) throw new Error('No transcript');
    const { transcript } = await res.json();
    await navigator.clipboard.writeText(transcript);
    showToast('Copied!');
    sendAnalyticsEvent('transcriptCopied', withTimestamps ? 'withTimestamps' : 'plain');
  } catch (e) {
    showToast('No transcript available');
  } finally {
    setCopying(false);
  }
}
```

**UI States:**
- Default: show submenu options
- Loading: "Copying..."
- Success: "Copied!" (brief inline feedback)
- Error: "No transcript available"

---

## File Structure

```
src/
├── lib/
│   ├── components/
│   │   ├── YouTubePlayer.svelte
│   │   ├── VideoTools.svelte           # Dropdown container
│   │   ├── SponsorSkip.svelte           # Toggle + data fetching + skip logic
│   │   ├── SponsorSkipActive.svelte     # Top-level indicator (auto mode)
│   │   ├── SponsorSkipButton.svelte     # Player overlay skip button (manual mode)
│   │   ├── SponsorSettings.svelte       # Mode toggle + category picker
│   │   ├── SilenceSkipper.svelte        # Toggle + data fetching
│   │   ├── SilenceSkipperActive.svelte  # Top-level active UI
│   │   └── CopyTranscript.svelte        # Dropdown submenu
│   ├── stores/
│   │   └── playerStore.ts
│   ├── types/
│   │   ├── sponsorBlock.ts
│   │   └── silence.ts
│   └── config.ts                        # VITE_SILENCE_SERVICE_URL
├── routes/
│   └── [url]/
│       └── +page.svelte
backend/
└── silence-service/
    ├── main.py
    ├── silence.py
    ├── transcript.py
    ├── queue.py
    ├── db.py
    ├── requirements.txt
    ├── Dockerfile
    └── railway.toml
```

## Environment Variables

**Frontend (Vite):**
- `VITE_SILENCE_SERVICE_URL` - e.g., `https://silence.yt-embed.railway.app`
- In `src/lib/config.ts`: `export const SILENCE_API = import.meta.env.VITE_SILENCE_SERVICE_URL`

**Backend (Railway):**
- `PORT` - set by Railway
- `DATABASE_PATH` - `/data/silence.db`

---

## Error Handling Summary

| Scenario | Frontend Behavior |
|----------|-------------------|
| Silence service down | Toggle disabled, "Service unavailable" tooltip |
| Silence processing failed | Error state with retry button |
| Silence queue full | "Queue full, try later" |
| Age-restricted video | "Can't process age-restricted videos" |
| SponsorBlock API down | Toggle disabled, graceful message |
| SponsorBlock 404 | "No sponsors found" (not error) |
| Transcript unavailable | "No transcript for this video" |
| Clipboard API fails | "Couldn't copy, try again" |

Player always works regardless of tool service status.

---

## Analytics Events

| Event | Details | When |
|-------|---------|------|
| `toolEnabled` | `"silence"` / `"sponsors"` | User toggles on (sponsors: only if previously disabled) |
| `toolDisabled` | `"silence"` / `"sponsors"` | User toggles off |
| `transcriptCopied` | `"plain"` / `"withTimestamps"` | Clipboard write succeeds |
| `silenceSkipped` | - | Skip triggered (debounced 10s) |
| `sponsorSkipped` | `"auto"` / `"manual"` | Skip triggered (auto debounced 10s) |
| `silenceQueueJoined` | - | User enters processing queue |

---

## Notes

**Multiple tools active:** When both SponsorSkip and SilenceSkipper are enabled, both may try to seek. Sponsor segments are larger, so sponsor skip effectively takes precedence. Speed mode state (`inSilence`, `originalRate`) resets correctly on any seek. No special conflict handling needed.

---

## Implementation Order Summary

1. **Phase -1**: Svelte 5 upgrade - prerequisite for modern reactivity
2. **Phase 0**: Player API - foundation for all skip features
3. **Phase 1**: Minimal UI shell - just the container
4. **Phase 2**: SponsorBlock - validates skip pattern, ships fast
5. **Phase 3**: Silence - backend then frontend, most complex
6. **Phase 4**: Transcript - simple addition to existing backend

Each phase delivers working functionality. Types and state emerge from actual need rather than upfront design.
