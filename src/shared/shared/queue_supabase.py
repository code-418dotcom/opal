import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy import text
from .db import SessionLocal
from .config import settings

LOG = logging.getLogger(__name__)


class QueueMessage:
    """Represents a queue message"""

    def __init__(self, id: int, queue_name: str, payload: dict, attempts: int = 0):
        self.id = id
        self.queue_name = queue_name
        self.payload = payload
        self.attempts = attempts

    def __str__(self) -> str:
        return json.dumps(self.payload)


def send_message(queue_name: str, payload: Dict[str, Any]) -> int:
    """
    Send a message to the queue

    Args:
        queue_name: Queue identifier (e.g., 'jobs', 'exports')
        payload: Message data as dictionary

    Returns:
        Message ID
    """
    with SessionLocal() as session:
        result = session.execute(
            text("""
                INSERT INTO job_queue (queue_name, payload, status, attempts, max_attempts)
                VALUES (:queue_name, :payload, 'pending', 0, :max_attempts)
                RETURNING id
            """),
            {
                'queue_name': queue_name,
                'payload': json.dumps(payload),
                'max_attempts': 3
            }
        )
        session.commit()
        message_id = result.scalar()
        LOG.info(f"Sent message to queue '{queue_name}': {message_id}")
        return message_id


def receive_messages(queue_name: str, max_count: int = 10, visibility_timeout: int = 300) -> List[QueueMessage]:
    """
    Receive messages from the queue

    Args:
        queue_name: Queue identifier
        max_count: Maximum number of messages to receive
        visibility_timeout: Time in seconds to lock messages

    Returns:
        List of QueueMessage objects
    """
    with SessionLocal() as session:
        # Lock messages for processing
        result = session.execute(
            text("""
                UPDATE job_queue
                SET status = 'processing',
                    processed_at = now(),
                    attempts = attempts + 1
                WHERE id IN (
                    SELECT id
                    FROM job_queue
                    WHERE queue_name = :queue_name
                      AND status = 'pending'
                      AND attempts < max_attempts
                    ORDER BY created_at ASC
                    LIMIT :max_count
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, queue_name, payload, attempts
            """),
            {
                'queue_name': queue_name,
                'max_count': max_count
            }
        )
        session.commit()

        messages = []
        for row in result:
            try:
                payload = json.loads(row.payload) if isinstance(row.payload, str) else row.payload
                messages.append(QueueMessage(
                    id=row.id,
                    queue_name=row.queue_name,
                    payload=payload,
                    attempts=row.attempts
                ))
            except Exception as e:
                LOG.error(f"Failed to parse message {row.id}: {e}")

        LOG.info(f"Received {len(messages)} messages from queue '{queue_name}'")
        return messages


def complete_message(message: QueueMessage) -> None:
    """
    Mark a message as completed and remove it from the queue

    Args:
        message: QueueMessage object
    """
    with SessionLocal() as session:
        session.execute(
            text("""
                UPDATE job_queue
                SET status = 'completed',
                    processed_at = now()
                WHERE id = :message_id
            """),
            {'message_id': message.id}
        )
        session.commit()
        LOG.info(f"Completed message {message.id} from queue '{message.queue_name}'")


def abandon_message(message: QueueMessage, error: Optional[str] = None) -> None:
    """
    Abandon a message and return it to the queue or mark as failed

    Args:
        message: QueueMessage object
        error: Error message (optional)
    """
    with SessionLocal() as session:
        # Check if max attempts reached
        result = session.execute(
            text("SELECT attempts, max_attempts FROM job_queue WHERE id = :message_id"),
            {'message_id': message.id}
        )
        row = result.fetchone()

        if row and row.attempts >= row.max_attempts:
            # Max attempts reached, mark as failed
            session.execute(
                text("""
                    UPDATE job_queue
                    SET status = 'failed',
                        error = :error,
                        processed_at = now()
                    WHERE id = :message_id
                """),
                {
                    'message_id': message.id,
                    'error': error or 'Max attempts reached'
                }
            )
            LOG.warning(f"Message {message.id} failed after {row.attempts} attempts")
        else:
            # Return to queue
            session.execute(
                text("""
                    UPDATE job_queue
                    SET status = 'pending',
                        error = :error
                    WHERE id = :message_id
                """),
                {
                    'message_id': message.id,
                    'error': error
                }
            )
            LOG.info(f"Abandoned message {message.id}, will retry")

        session.commit()


def dead_letter_message(message: QueueMessage, reason: str, error_description: str = '') -> None:
    """
    Move a message to dead letter (mark as permanently failed)

    Args:
        message: QueueMessage object
        reason: Failure reason
        error_description: Detailed error description
    """
    with SessionLocal() as session:
        error_msg = f"{reason}: {error_description}" if error_description else reason
        session.execute(
            text("""
                UPDATE job_queue
                SET status = 'failed',
                    error = :error,
                    processed_at = now()
                WHERE id = :message_id
            """),
            {
                'message_id': message.id,
                'error': error_msg
            }
        )
        session.commit()
        LOG.error(f"Dead-lettered message {message.id}: {error_msg}")


def purge_completed_messages(queue_name: str, older_than_hours: int = 24) -> int:
    """
    Remove completed messages older than specified hours

    Args:
        queue_name: Queue identifier
        older_than_hours: Age threshold in hours

    Returns:
        Number of messages deleted
    """
    with SessionLocal() as session:
        result = session.execute(
            text("""
                DELETE FROM job_queue
                WHERE queue_name = :queue_name
                  AND status = 'completed'
                  AND processed_at < now() - interval ':hours hours'
                RETURNING id
            """),
            {
                'queue_name': queue_name,
                'hours': older_than_hours
            }
        )
        session.commit()
        count = result.rowcount
        LOG.info(f"Purged {count} completed messages from queue '{queue_name}'")
        return count


def get_queue_stats(queue_name: str) -> Dict[str, int]:
    """
    Get queue statistics

    Args:
        queue_name: Queue identifier

    Returns:
        Dictionary with pending, processing, completed, failed counts
    """
    with SessionLocal() as session:
        result = session.execute(
            text("""
                SELECT
                    status,
                    COUNT(*) as count
                FROM job_queue
                WHERE queue_name = :queue_name
                GROUP BY status
            """),
            {'queue_name': queue_name}
        )

        stats = {
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0
        }

        for row in result:
            stats[row.status] = row.count

        return stats


# Convenience functions for specific queues
def send_job_message(payload: Dict[str, Any]) -> int:
    """Send a message to the jobs queue"""
    return send_message('jobs', payload)


def send_export_message(payload: Dict[str, Any]) -> int:
    """Send a message to the exports queue"""
    return send_message('exports', payload)
