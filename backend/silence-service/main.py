"""
FastAPI app for silence detection service.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from db import (
    init_db,
    get_cached_silence,
    invalidate_cache,
    get_queue_status,
    add_to_queue,
    get_queue_length,
    check_rate_limit,
    increment_rate_limit,
)
from worker import worker
from silence import validate_video_id, MAX_VIDEO_DURATION_SEC

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

MAX_QUEUE_LENGTH = 50


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Initializing database...")
    init_db()

    logger.info("Starting queue worker...")
    await worker.start()

    yield

    # Shutdown
    logger.info("Shutting down...")
    await worker.stop()


app = FastAPI(
    title="Silence Detection Service",
    description="Detects silent segments in YouTube videos",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_client_ip(request: Request) -> str:
    """Get client IP from request, handling proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "queue_length": get_queue_length()}


@app.post("/silence/request")
async def request_silence_analysis(v: str, duration: float, request: Request):
    """
    Request silence analysis for a video.

    - If cached and duration matches: returns cached segments immediately
    - If cached but duration differs: invalidates cache and re-queues
    - If not cached: adds to processing queue

    Query params:
        v: YouTube video ID
        duration: Video duration in seconds (from YouTube player API)
    """
    video_id = v

    # Validate video ID
    if not validate_video_id(video_id):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": "invalid_video_id"},
        )

    # Validate duration
    if duration <= 0 or duration > MAX_VIDEO_DURATION_SEC:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": "invalid_duration"},
        )

    # Check cache first
    cached = get_cached_silence(video_id)

    if cached:
        # Cache hit - check if duration matches (within 1 second tolerance)
        if abs(cached["duration_sec"] - duration) <= 1.0:
            return {
                "status": "cached",
                "segments": cached["segments"],
                "duration_sec": cached["duration_sec"],
            }

        # Duration mismatch - video was edited, invalidate cache
        logger.info(
            f"Cache invalidated for {video_id}: duration changed "
            f"({cached['duration_sec']:.1f}s -> {duration:.1f}s)"
        )
        invalidate_cache(video_id)

    # Check if already in queue
    queue_status = get_queue_status(video_id)
    if queue_status:
        status = queue_status["status"]
        if status == "queued":
            return {"status": "queued", "position": queue_status["position"]}
        if status == "processing":
            return {"status": "processing"}
        if status == "failed":
            # Allow retry for failed jobs - fall through to add to queue
            pass

    # Check rate limit (only for new submissions)
    client_ip = get_client_ip(request)
    allowed, retry_after = check_rate_limit(client_ip)

    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "error": "rate_limited",
                "retry_after": retry_after,
            },
        )

    # Check queue length
    if get_queue_length() >= MAX_QUEUE_LENGTH:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "error": "queue_full"},
        )

    # Add to queue
    position = add_to_queue(video_id, client_ip)
    increment_rate_limit(client_ip)

    logger.info(f"Added {video_id} to queue at position {position}")

    return {"status": "queued", "position": position}


@app.get("/silence/status")
async def get_silence_status(v: str):
    """
    Get processing status for a video.

    Query params:
        v: YouTube video ID
    """
    video_id = v

    if not validate_video_id(video_id):
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": "invalid_video_id"},
        )

    # Check cache first
    cached = get_cached_silence(video_id)
    if cached:
        return {
            "status": "completed",
            "segments": cached["segments"],
            "duration_sec": cached["duration_sec"],
        }

    # Check queue
    queue_status = get_queue_status(video_id)
    if queue_status:
        status = queue_status["status"]

        if status == "queued":
            return {"status": "queued", "position": queue_status["position"]}

        if status == "processing":
            return {"status": "processing"}

        if status == "failed":
            return {
                "status": "failed",
                "error": queue_status["error"],
            }

    return {"status": "not_found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
