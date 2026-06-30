"""Conversation CRUD — small wrapper over SQLite for chat history."""

from src.core.db import get_conn


def create_conversation(title: str | None = None, telegram_user_id: int | None = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (title, telegram_user_id) VALUES (?, ?)",
            (title, telegram_user_id),
        )
        return int(cur.lastrowid)


def get_or_create_for_telegram(telegram_user_id: int) -> int:
    """Return the most recent conversation for this Telegram user, creating one if needed.

    One ongoing conversation per Telegram user. To start a fresh one, call
    create_conversation(telegram_user_id=...) explicitly (e.g. on a /reset command).
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM conversations WHERE telegram_user_id = ? ORDER BY id DESC LIMIT 1",
            (telegram_user_id,),
        ).fetchone()
        if row:
            return int(row["id"])
        cur = conn.execute(
            "INSERT INTO conversations (telegram_user_id, title) VALUES (?, ?)",
            (telegram_user_id, f"telegram:{telegram_user_id}"),
        )
        return int(cur.lastrowid)


def conversation_exists(conversation_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        return row is not None


def list_messages(conversation_id: int, limit: int | None = None) -> list[dict]:
    """Return prior messages for a conversation in chronological order.

    When `limit` is given, only the most recent `limit` messages are loaded from
    SQLite (newest-first LIMIT, then reversed to chronological) — so a long thread
    never pulls its full history into memory just to slice it down to the LLM
    window (CL-SYS-12). With no limit, the full thread is returned (the
    /conversations endpoint shows the complete transcript)."""
    with get_conn() as conn:
        if limit is not None and limit > 0:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE conversation_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (conversation_id, int(limit)),
            ).fetchall()
            rows = list(reversed(rows))
        else:
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
