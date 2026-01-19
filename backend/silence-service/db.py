"""
SQLite database operations for silence detection service.
"""

import sqlite3
import json
import time
import os
from contextlib import contextmanager
from typing import Optional

DATABASE_PATH = os.environ.get("DATABASE_PATH", "/data/silence.db")


def get_db_path() -> str:
    """Get database path, ensuring directory exists."""
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    return DATABASE_PATH


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path(), timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database with schema."""
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")

        # Silence cache - indefinite cache, keyed by video_id
        conn.execute("""
            CREATE TABLE IF NOT EXISTS silence_cache (
                video_id TEXT PRIMARY KEY,
                segments TEXT NOT NULL,
                duration_sec REAL NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)

        # Processing queue
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                video_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                position INTEGER,
                ip TEXT,
                submitted_at INTEGER,
                started_at INTEGER,
                error TEXT
            )
        """)

        # Rate limits
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rate_limits (
                ip TEXT PRIMARY KEY,
                request_count INTEGER,
                window_start INTEGER
            )
        """)

        conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status)")
        conn.commit()


# --- Cache operations ---

def get_cached_silence(video_id: str) -> Optional[dict]:
    """Get cached silence segments for a video."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT segments, duration_sec FROM silence_cache WHERE video_id = ?",
            (video_id,)
        ).fetchone()

        if row:
            return {
                "segments": json.loads(row["segments"]),
                "duration_sec": row["duration_sec"]
            }
        return None


def cache_silence(video_id: str, segments: list, duration_sec: float):
    """Cache silence segments for a video."""
    with get_connection() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO silence_cache (video_id, segments, duration_sec, created_at)
            VALUES (?, ?, ?, ?)
        """, (video_id, json.dumps(segments), duration_sec, int(time.time())))
        conn.commit()


def invalidate_cache(video_id: str):
    """Remove cached data for a video (when duration changes)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM silence_cache WHERE video_id = ?", (video_id,))
        conn.commit()


# --- Queue operations ---

def get_queue_status(video_id: str) -> Optional[dict]:
    """Get queue status for a video."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT status, position, error FROM queue WHERE video_id = ?",
            (video_id,)
        ).fetchone()

        if row:
            return {
                "status": row["status"],
                "position": row["position"],
                "error": row["error"]
            }
        return None


def add_to_queue(video_id: str, ip: str) -> int:
    """Add video to processing queue. Returns position."""
    with get_connection() as conn:
        # Get next position
        row = conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 as next_pos FROM queue WHERE status = 'queued'"
        ).fetchone()
        position = row["next_pos"]

        conn.execute("""
            INSERT OR REPLACE INTO queue (video_id, status, position, ip, submitted_at)
            VALUES (?, 'queued', ?, ?, ?)
        """, (video_id, position, ip, int(time.time())))
        conn.commit()

        return position


def claim_next_job() -> Optional[dict]:
    """Atomically get and claim the next job to process."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT video_id, ip FROM queue
            WHERE status = 'queued'
            ORDER BY position ASC
            LIMIT 1
        """).fetchone()

        if row:
            # Claim it - check rowcount to handle race condition
            cursor = conn.execute("""
                UPDATE queue SET status = 'processing', started_at = ?
                WHERE video_id = ? AND status = 'queued'
            """, (int(time.time()), row["video_id"]))
            conn.commit()

            # If rowcount is 0, another worker claimed it first
            if cursor.rowcount > 0:
                return {"video_id": row["video_id"], "ip": row["ip"]}

        return None


def mark_completed(video_id: str):
    """Mark a job as completed and remove from queue."""
    with get_connection() as conn:
        conn.execute("DELETE FROM queue WHERE video_id = ?", (video_id,))
        conn.commit()


def mark_failed(video_id: str, error: str):
    """Mark a job as failed."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE queue SET status = 'failed', error = ?
            WHERE video_id = ?
        """, (error, video_id))
        conn.commit()


def reset_processing_jobs():
    """Reset any 'processing' jobs to 'queued' (crash recovery)."""
    with get_connection() as conn:
        conn.execute("UPDATE queue SET status = 'queued' WHERE status = 'processing'")
        conn.commit()


def get_queue_length() -> int:
    """Get number of jobs in queue (queued + processing)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as count FROM queue WHERE status IN ('queued', 'processing')"
        ).fetchone()
        return row["count"]


def cleanup_old_failed_jobs(max_age_hours: int = 24):
    """Remove old failed jobs from queue."""
    with get_connection() as conn:
        cutoff = int(time.time()) - (max_age_hours * 3600)
        conn.execute("""
            DELETE FROM queue
            WHERE status = 'failed' AND submitted_at < ?
        """, (cutoff,))
        conn.commit()


# --- Rate limit operations ---

RATE_LIMIT_WINDOW = 3600  # 1 hour
MAX_REQUESTS_PER_WINDOW = 5


def check_rate_limit(ip: str) -> tuple[bool, int]:
    """
    Check if IP is rate limited.
    Returns (is_allowed, retry_after_seconds).
    """
    now = int(time.time())

    with get_connection() as conn:
        # Clean up old entries
        conn.execute(
            "DELETE FROM rate_limits WHERE window_start < ?",
            (now - 86400,)  # Prune entries older than 24 hours
        )

        row = conn.execute(
            "SELECT request_count, window_start FROM rate_limits WHERE ip = ?",
            (ip,)
        ).fetchone()

        if row:
            window_start = row["window_start"]
            request_count = row["request_count"]

            # Window expired - reset
            if now - window_start >= RATE_LIMIT_WINDOW:
                conn.execute(
                    "UPDATE rate_limits SET request_count = 0, window_start = ? WHERE ip = ?",
                    (now, ip)
                )
                conn.commit()
                return True, 0

            # Within window - check limit
            if request_count >= MAX_REQUESTS_PER_WINDOW:
                retry_after = RATE_LIMIT_WINDOW - (now - window_start)
                return False, retry_after

            return True, 0

        return True, 0


def increment_rate_limit(ip: str):
    """Increment rate limit counter for IP."""
    now = int(time.time())

    with get_connection() as conn:
        row = conn.execute(
            "SELECT request_count, window_start FROM rate_limits WHERE ip = ?",
            (ip,)
        ).fetchone()

        if row:
            window_start = row["window_start"]

            # Window expired - reset
            if now - window_start >= RATE_LIMIT_WINDOW:
                conn.execute(
                    "UPDATE rate_limits SET request_count = 1, window_start = ? WHERE ip = ?",
                    (now, ip)
                )
            else:
                conn.execute(
                    "UPDATE rate_limits SET request_count = request_count + 1 WHERE ip = ?",
                    (ip,)
                )
        else:
            conn.execute(
                "INSERT INTO rate_limits (ip, request_count, window_start) VALUES (?, 1, ?)",
                (ip, now)
            )

        conn.commit()
