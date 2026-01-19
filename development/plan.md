# Video Tools Implementation Plan

## Phase 0: Foundation - YouTube IFrame Player API Migration

### 0.1 Create YouTube Player Component
- Create `src/lib/components/YouTubePlayer.svelte`
- Load YouTube IFrame API script dynamically (`https://www.youtube.com/iframe_api`)
- Initialize player with `new YT.Player()` using existing videoId
- Expose player controls: play, pause, seekTo, getCurrentTime, setPlaybackRate, getPlaybackRate
- Create Svelte store for player state (currentTime, playerState, duration)
- Time polling: 100ms interval, start on PLAYING state, stop on other states
- Maintain current responsive 16:9 aspect ratio styling

### 0.2 Integrate Player into Video Page
- Replace raw iframe in `src/routes/[url]/+page.svelte` with YouTubePlayer component
- Wire up `onReady` and `onStateChange` events
- Test: verify no visual regression, player loads correctly

---

## Phase 1: Video Tools UI Shell + State Management

### 1.1 Create Tools Dropdown Component
- Create `src/lib/components/VideoTools.svelte`
- Replace "more tools" link with expandable "▸ video tools" text
- Collapsed by default, expands on click to show "▾ video tools"
- Minimal styling matching existing emerald link aesthetic

### 1.2 Tool State Architecture

**All tools always visible in dropdown.** State management is for:

1. **Active state** (is the tool running?)
   - Reset to OFF on video navigation
   - When user enables: added to URL params
   - URL params = session state (shareable)

2. **Settings** (tool configuration)
   - Stored in localStorage
   - Persists across sessions
   - Applied when tool is active

**State flow:**
- Page load: all tools visible in dropdown, none active
- If URL has `?tools=silence`: activate those tools immediately
- User clicks toggle → tool becomes active → added to URL params
- User navigates to new video → active state resets, settings persist

### 1.3 State Management Implementation
- Create `src/lib/stores/toolsStore.ts`
```typescript
type ToolState = {
  active: boolean;     // currently enabled (from URL or user action)
  loading: boolean;
  error: string | null;
}

type SilenceSettings = {
  mode: 'skip' | 'speed';  // skip silence or speed through at 2x
  minSkipMs: number;       // default 500
  leadInMs: number;        // default 100
  leadOutMs: number;       // default 0
}

type SponsorBlockSettings = {
  skipCategories: string[];  // default: ['sponsor', 'selfpromo']
}

type ToolsState = {
  silence: ToolState & {
    settings: SilenceSettings;
    segments: SilenceSegment[] | null;  // cached from backend
  };
  sponsors: ToolState & {
    settings: SponsorBlockSettings;
  };
}
```

### 1.4 LocalStorage Schema
```typescript
type SavedToolDefaults = {
  silenceSettings: {
    mode: 'skip' | 'speed';   // default 'skip'
    minSkipMs: number;        // default 500
    leadInMs: number;         // default 100
    leadOutMs: number;        // default 0
  };
  sponsorBlockSettings: {
    skipCategories: string[];  // default: ['sponsor', 'selfpromo']
  };
}
// Key: 'yt-embed-tool-defaults'
```

### 1.5 URL Params
- Only active (user-enabled) tools go in URL: `?v=xxx&tools=silence,sponsors`
- On page load with URL params: those tools activate immediately
- Shareable: send URL with tools param to share active tool state

### 1.6 UI Layout

**Two display areas with per-tool customization:**

1. **Top level** (below video, next to "about" link):
   - Shows currently **active** tools only
   - Compact, tool-specific UI (not identical to dropdown)
   - Empty on first load

2. **Dropdown** "▸ video tools":
   - Contains **all** tools
   - Full controls with settings access
   - Expand/collapse

**Flow:**
- First visit: Top level empty, all tools in dropdown
- User enables tool: appears at top level with compact UI
- User can control from either location

---

### 1.7 Per-Tool UI Specification

**Principle**: Dropdown is simple on/off. Settings live at top level where active tools appear.

#### Copy Transcript
- **Dropdown**: "Copy transcript ▸" submenu with "Plain text" / "With timestamps"
- **Top level**: Not shown (action-only, no persistent state)

#### Skip Silence
- **Dropdown**: Simple on/off toggle
- **Top level** (when active) - settings directly visible for easy per-video tweaking:
  - Mode toggle: "Skip" vs "2x"
  - Min skip slider/input (ms)
  - Lead-in / Lead-out inputs
  - Adjusted duration: "32:15 → 28:42 (-3:33)"
  - Toggle off button

#### Skip Sponsors (SponsorBlock)
- **Dropdown**: Simple on/off toggle
- **Top level** (when active):
  - Label: "SponsorBlock (3)" showing segment count
  - ⚙️ gear icon → opens category settings menu:
    - sponsor (default ON)
    - selfpromo (default ON)
    - interaction (default OFF)
    - intro (default OFF)
    - outro (default OFF)
    - preview (default OFF)
    - music_offtopic (default OFF)
    - filler (default OFF)
  - Toggle off button

### 1.9 Analytics Integration
- Fire `sendAnalyticsEvent('toolEnabled', toolName)` when toggled on
- Fire `sendAnalyticsEvent('toolDisabled', toolName)` when toggled off

---

## Phase 2: Silence Skipper

### 2.1 Backend: Silence Detection Service
Location: `backend/silence-service/`

#### 2.1.1 Project Setup
- FastAPI Python project
- Dependencies: fastapi, uvicorn, yt-dlp, pydub, python-multipart
- SQLite with WAL mode for caching

#### 2.1.2 Queue System
- Global processing queue (only 1 video at a time to avoid IP ban)
- In-memory queue with SQLite persistence for crash recovery
- Queue state: `{video_id, status, position, submitted_at, ip}`
- Statuses: `queued`, `processing`, `completed`, `failed`

#### 2.1.3 Endpoints

**CORS**: All endpoints return `Access-Control-Allow-Origin: *` (or restrict to yt.ttools.io)

**POST /silence/request**
- Params: `v` (videoId)
- Rate limit: 5 submissions per IP per hour
- If already cached: return results immediately
- If already in queue: return current position
- Else: add to queue, return position
- Response: `{status: "queued"|"processing"|"cached", position?: number, segments?: []}`

**GET /silence/status**
- Params: `v` (videoId)
- Frontend polls this every 2-3s while waiting
- Returns current status, queue position, or results if ready
- Response: `{status, position?, segments?, error?}`

**GET /health**
- Returns `{status: "ok", queue_length: N}`

#### 2.1.4 Processing Logic
- Download audio only via yt-dlp (lowest quality, temp file)
- Detect silence with pydub (threshold: -40dB, min chunk: 100ms)
- Return ALL detected silences (frontend filters by user settings)
- Store results in SQLite: `video_id, segments_json, created_at`
- Segments format: `[{start_ms, end_ms, duration_ms}, ...]`
- Delete temp audio file after processing
- On failure: mark as failed, allow retry after cooldown

#### 2.1.5 SQLite Schema
```sql
-- WAL mode enabled on connection
PRAGMA journal_mode=WAL;

CREATE TABLE silence_cache (
  video_id TEXT PRIMARY KEY,
  segments TEXT NOT NULL, -- JSON array
  created_at INTEGER NOT NULL
);

CREATE TABLE queue (
  video_id TEXT PRIMARY KEY,
  status TEXT NOT NULL, -- queued, processing, completed, failed
  position INTEGER,
  ip TEXT,
  submitted_at INTEGER,
  error TEXT
);

CREATE TABLE rate_limits (
  ip TEXT PRIMARY KEY,
  request_count INTEGER,
  window_start INTEGER
);
```

#### 2.1.6 Deployment
- Dockerfile with ffmpeg, yt-dlp
- Deploy to Railway.app
- Environment: `PORT`, `DATABASE_PATH`
- Health check: `GET /health`

### 2.2 Frontend: Silence Skip Integration
Location: `src/lib/components/SilenceSkipper.svelte`

#### 2.2.1 Data Fetching
- TanStack Query with polling/refetch for queue status
- Query key: `['silence', videoId]`
- On mount (if tool enabled): check status
- If queued/processing: poll every 2s until ready
- If cached: use immediately

#### 2.2.2 UI States
- **Off**: Toggle shows "Skip silence"
- **Loading/Queued**: "Skip silence (queue: #3)" or "Skip silence (processing...)"
- **Ready**: "Skip silence ✓" with active styling
- **Error**: "Skip silence ⚠" with tooltip explaining error
- **Service down**: Graceful message, tool disabled

#### 2.2.3 Skip Logic
- Subscribe to player time polling (100ms via playerStore)
- Filter segments by minSkipMs setting (client-side)
- Check if currentTime falls within filtered segment (accounting for leadOutMs)
- If in silence: `player.seekTo(segment.end - leadInMs)`
- Fire `sendAnalyticsEvent('silenceSkipped')` (debounced, max 1 per 10s)

```typescript
// Pseudocode
const filteredSegments = segments.filter(s => s.duration_ms >= settings.minSkipMs);
for (const seg of filteredSegments) {
  const skipStart = seg.start_ms + settings.leadOutMs;
  const skipEnd = seg.end_ms - settings.leadInMs;
  if (currentMs >= skipStart && currentMs < skipEnd) {
    player.seekTo(skipEnd / 1000);
    break;
  }
}
```

---

## Phase 3: SponsorBlock Integration

### 3.1 Data Fetching
Location: `src/lib/components/SponsorSkip.svelte`

- TanStack Query: `GET https://sponsor.ajay.app/api/skipSegments?videoID={videoId}`
- Query key: `['sponsorblock', videoId]`
- Handle 404 as "no segments" (not error)
- Cache with long staleTime (segments don't change often)

### 3.2 Category Filtering
- Read enabled categories from toolsStore (sourced from localStorage)
- Filter fetched segments by category before applying skip logic
- Available categories from SponsorBlock API:
  - `sponsor` - Paid promotion
  - `selfpromo` - Unpaid self-promotion
  - `interaction` - Subscribe/like reminders
  - `intro` - Intro animation
  - `outro` - Endcards/credits
  - `preview` - Preview/recap
  - `music_offtopic` - Non-music in music video
  - `filler` - Tangent/filler

### 3.3 UI States
- **Off**: Toggle shows "Skip sponsors"
- **Loading**: "Skip sponsors ..."
- **Ready (has segments)**: "Skip sponsors ✓ (3)" - count of segments matching enabled categories
- **Ready (no segments)**: "Skip sponsors (none)"
- **Error**: "Skip sponsors ⚠"
- Settings gear icon → expands SponsorSettings.svelte

### 3.4 Skip Logic
- Subscribe to player time polling (100ms via playerStore)
- Filter segments by enabled categories
- Check if currentTime falls within any enabled segment
- If entering segment: `player.seekTo(segment.endTime)`
- Fire `sendAnalyticsEvent('sponsorSkipped')` (debounced, max 1 per 10s)

---

## Phase 4: Copy Transcript

### 4.1 Backend Endpoint
Add to silence-service or separate: `GET /transcript`

- Params: `v` (videoId), `timestamps` (boolean, default false)
- Use `youtube-transcript-api` Python library
- Format output:
  - Plain: just text joined with spaces/newlines
  - With timestamps: `[0:00] First line\n[0:05] Second line`
- Cache in SQLite
- Return 404 if no transcript available

### 4.2 Frontend: Copy Buttons
Location: Inside `VideoTools.svelte` dropdown

- "Copy transcript" dropdown with two options:
  - "Copy (plain text)"
  - "Copy (with timestamps)"
- On click: fetch transcript, copy to clipboard
- States:
  - Default: show options
  - Loading: "Copying..."
  - Success: "Copied!" (brief toast or inline feedback)
  - Error: "No transcript available" or "Failed to copy"
- Fire `sendAnalyticsEvent('transcriptCopied', 'plain' | 'withTimestamps')`

---

## File Structure After Implementation

```
src/
├── lib/
│   ├── components/
│   │   ├── YouTubePlayer.svelte     # IFrame API player wrapper
│   │   ├── VideoTools.svelte        # Tools dropdown + top-level active tools
│   │   ├── SilenceSkipper.svelte    # Silence skip logic + UI state
│   │   ├── SilenceSettings.svelte   # Silence settings (minSkip, margins)
│   │   ├── SponsorSkip.svelte       # Sponsor skip logic + UI state
│   │   └── SponsorSettings.svelte   # SponsorBlock category picker
│   ├── stores/
│   │   ├── playerStore.ts           # Player state (currentTime, playing, etc)
│   │   └── toolsStore.ts            # Tool active state + settings
│   ├── config.ts                    # VITE_SILENCE_SERVICE_URL etc
│   └── analytics.ts                 # (existing)
├── routes/
│   └── [url]/
│       ├── +page.svelte             # Updated with new components
│       └── ViewsLikesDislikes.svelte
backend/
├── silence-service/
│   ├── main.py                      # FastAPI app, routes, CORS
│   ├── silence.py                   # Silence detection logic
│   ├── transcript.py                # Transcript fetching
│   ├── queue.py                     # Processing queue management
│   ├── db.py                        # SQLite operations (WAL mode)
│   ├── rate_limit.py                # Rate limiting
│   ├── requirements.txt
│   ├── Dockerfile
│   └── railway.toml                 # Railway deployment config
├── yt-api-worker/                   # (existing)
└── yt-silence-skipper/              # (reference implementation, can archive)
```

## Environment Variables

Frontend (Vite, public):
- `VITE_SILENCE_SERVICE_URL` - Backend URL (e.g., `https://silence-service.railway.app`)

---

## Implementation Order

1. **Phase 0**: Player API migration (foundation for all skip features)
2. **Phase 1**: Tools UI shell + URL state (scaffold for features)
3. **Phase 2**: Silence skipper backend → then frontend
4. **Phase 3**: SponsorBlock (no backend, quick win)
5. **Phase 4**: Transcript copy (backend + simple frontend)

---

## API Contracts

### Silence Service

**POST /silence/request?v={videoId}**
```json
// Already cached
{ "status": "cached", "segments": [{"start_ms": 12500, "end_ms": 14200, "duration_ms": 1700}] }

// Added to queue
{ "status": "queued", "position": 3 }

// Already processing
{ "status": "processing" }

// Rate limited
{ "status": "error", "error": "rate_limited", "retryAfter": 3600 }
```

**GET /silence/status?v={videoId}**
```json
// In queue
{ "status": "queued", "position": 2 }

// Processing
{ "status": "processing" }

// Ready
{ "status": "completed", "segments": [{"start_ms": 12500, "end_ms": 14200, "duration_ms": 1700}] }

// Failed
{ "status": "failed", "error": "Video unavailable" }

// Not found (never requested)
{ "status": "not_found" }
```

### Transcript Service

**GET /transcript?v={videoId}&timestamps=false**
```json
// Success
{
  "videoId": "dQw4w9WgXcQ",
  "transcript": "Never gonna give you up never gonna let you down..."
}

// With timestamps
{
  "videoId": "dQw4w9WgXcQ",
  "transcript": "[0:00] Never gonna give you up\n[0:04] never gonna let you down..."
}

// No transcript
{ "error": "no_transcript", "message": "No captions available" }
```

### SponsorBlock (external)
```
GET https://sponsor.ajay.app/api/skipSegments?videoID={videoId}
Response 200: [{"segment": [start, end], "category": "sponsor"}, ...]
Response 404: No segments found
```

---

## Analytics Events

Following existing `sendAnalyticsEvent(eventName, details?)` pattern:

| Event | Details | When |
|-------|---------|------|
| `toolEnabled` | `"silence"` / `"sponsors"` | User toggles tool on |
| `toolDisabled` | `"silence"` / `"sponsors"` | User toggles tool off |
| `transcriptCopied` | `"plain"` / `"withTimestamps"` | User copies transcript |
| `silenceSkipped` | - | Silence segment skipped (debounced 10s) |
| `sponsorSkipped` | - | Sponsor segment skipped (debounced 10s) |
| `silenceQueueJoined` | - | User joins silence processing queue |

---

## Error Handling Strategy

| Scenario | Frontend Behavior |
|----------|-------------------|
| Silence service down | Toggle disabled, tooltip "Service unavailable" |
| Silence processing failed | Show error state, offer retry button |
| Silence queue full | Show position, poll for updates |
| SponsorBlock API down | Toggle disabled, graceful message |
| SponsorBlock 404 | "No sponsors found" (not an error) |
| Transcript unavailable | "No transcript for this video" |
| Clipboard API fails | "Couldn't copy, try again" |

Player always works regardless of tool service status.

---

## Open Questions

None - all resolved.
