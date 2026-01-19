"""
Background queue worker for processing silence detection jobs.
"""

import asyncio
import logging
from typing import Callable

from db import (
    claim_next_job,
    mark_completed,
    mark_failed,
    reset_processing_jobs,
    cache_silence,
    cleanup_old_failed_jobs,
)
from silence import extract_silence_segments, SilenceDetectionError

logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 2
PROCESSING_TIMEOUT_SEC = 300  # 5 minutes per video


class QueueWorker:
    """Background worker that processes silence detection jobs."""

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._on_job_complete: Callable[[str], None] | None = None

    def set_job_complete_callback(self, callback: Callable[[str], None]):
        """Set callback to be called when a job completes (for testing/monitoring)."""
        self._on_job_complete = callback

    async def start(self):
        """Start the background worker."""
        if self._running:
            return

        logger.info("Starting queue worker...")

        # Crash recovery: reset any jobs stuck in 'processing'
        reset_processing_jobs()
        logger.info("Reset any stuck processing jobs")

        # Clean up old failed jobs
        cleanup_old_failed_jobs(max_age_hours=24)

        self._running = True
        self._task = asyncio.create_task(self._process_loop())

    async def stop(self):
        """Stop the background worker."""
        logger.info("Stopping queue worker...")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Queue worker stopped")

    async def _process_loop(self):
        """Main processing loop."""
        while self._running:
            try:
                # Atomically claim next job (marks as processing in same transaction)
                job = claim_next_job()

                if job:
                    video_id = job["video_id"]
                    logger.info(f"Processing job: {video_id}")

                    try:
                        await self._process_job(video_id)
                    except Exception as e:
                        logger.error(f"Error processing {video_id}: {e}")
                        mark_failed(video_id, str(e))

                await asyncio.sleep(POLL_INTERVAL_SEC)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Queue worker error: {e}")
                await asyncio.sleep(POLL_INTERVAL_SEC)

    async def _process_job(self, video_id: str):
        """Process a single job with timeout."""
        try:
            # Run silence detection with timeout
            # Use asyncio.to_thread to run blocking I/O in thread pool
            segments, duration_sec = await asyncio.wait_for(
                asyncio.to_thread(extract_silence_segments, video_id),
                timeout=PROCESSING_TIMEOUT_SEC,
            )

            # Cache results
            cache_silence(video_id, segments, duration_sec)
            mark_completed(video_id)

            logger.info(
                f"Completed {video_id}: {len(segments)} segments, {duration_sec:.1f}s duration"
            )

            if self._on_job_complete:
                self._on_job_complete(video_id)

        except asyncio.TimeoutError:
            logger.error(f"Timeout processing {video_id}")
            mark_failed(video_id, "Processing timeout - video may be too long")

        except SilenceDetectionError as e:
            logger.error(f"Detection error for {video_id}: {e.code} - {e.message}")
            mark_failed(video_id, f"{e.code}: {e.message}")

        except Exception as e:
            logger.error(f"Unexpected error processing {video_id}: {e}")
            mark_failed(video_id, f"Unexpected error: {str(e)[:200]}")


# Global worker instance
worker = QueueWorker()
