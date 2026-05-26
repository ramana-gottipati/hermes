"""Conversation CRUD — small wrapper over SQLite for chat history."""

from src.core.db import get_conn


def create_conversation(title: str | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute("INSERT INTO conversations (title) VALUES (?)", (title,))
        return int(cur.lastrowid)


def conversation_exists(conversation_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return row is not None


def list_messages(conversation_id: int) -> list[dict]:
    """Return prior messages for a conversation in chronological order."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id ASC",
            (conversation_id,),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]


def append_message(conversation_id: int, role: str, content: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
            (conversation_id, role, content),
        )


def list_conversations(limit: int = 20) -> list[dict]:
    """List recent conversations with message counts and a snippet of the first message."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT  c.id,
                    c.created_at,
                    c.title,
                    (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id)        AS message_count,
                    (SELECT substr(content, 1, 80) FROM messages
                     WHERE conversation_id = c.id ORDER BY id ASC LIMIT 1)              AS first_message_snippet
            FROM    conversations c
            ORDER BY c.id DESC
            LIMIT   ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_conversation(conversation_id: int) -> bool:
    """Delete a conversation and all its messages. Returns True if it existed."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        return cur.rowcount > 0
