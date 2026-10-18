"""Stable, restart-safe conversation history and send ledger.

This module never connects to BOSS or sends a message. All callers must use a
verified platform conversation ID and message ID; candidate names are not IDs.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path


def conversation_key(stable_id: str) -> str:
    if not isinstance(stable_id, str) or not stable_id.strip():
        raise ValueError('缺少稳定会话 ID，不能按姓名合并会话')
    return hashlib.sha256(stable_id.strip().encode('utf-8')).hexdigest()


class ConversationStore:
    def __init__(self, database: Path):
        database = Path(database)
        database.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(database)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS messages (
            conversation_key TEXT NOT NULL,
            message_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL,
            PRIMARY KEY(conversation_key, message_id)
        )''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS sends (
            send_key TEXT PRIMARY KEY,
            conversation_key TEXT NOT NULL,
            inbound_version TEXT NOT NULL,
            body TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('pending','confirmed','unknown'))
        )''')
        self.db.commit()

    def record_inbound(self, key: str, message_id: str, content: str) -> bool:
        if not key or not message_id or not isinstance(content, str):
            raise ValueError('消息缺少稳定身份或正文')
        with self.db:
            result = self.db.execute(
                'INSERT OR IGNORE INTO messages VALUES (?,?,?,?)',
                (key, message_id, 'user', content),
            )
        return result.rowcount == 1

    def history(self, key: str, limit: int = 20) -> list[dict[str, str]]:
        if not key or not 1 <= limit <= 100:
            raise ValueError('会话或历史长度无效')
        rows = self.db.execute(
            'SELECT role, content FROM (SELECT rowid, role, content FROM messages '
            'WHERE conversation_key=? ORDER BY rowid DESC LIMIT ?) ORDER BY rowid',
            (key, limit),
        ).fetchall()
        return [{'role': role, 'content': content} for role, content in rows]

    @staticmethod
    def send_key(key: str, inbound_version: str, body: str) -> str:
        if not key or not inbound_version or not body:
            raise ValueError('发送去重身份无效')
        return hashlib.sha256(f'{key}\n{inbound_version}\n{body}'.encode('utf-8')).hexdigest()

    def reserve_send(self, key: str, inbound_version: str, body: str) -> tuple[str, str]:
        send_key = self.send_key(key, inbound_version, body)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO sends VALUES (?,?,?,?,?)',
                            (send_key, key, inbound_version, body, 'pending'))
        state = self.db.execute('SELECT state FROM sends WHERE send_key=?', (send_key,)).fetchone()[0]
        return send_key, state

    def mark_unknown(self, send_key: str) -> None:
        with self.db:
            self.db.execute("UPDATE sends SET state='unknown' WHERE send_key=? AND state='pending'", (send_key,))

    def confirm_send(self, send_key: str, observed_message_id: str) -> bool:
        if not observed_message_id:
            raise ValueError('缺少平台发送回执，不能标记成功')
        with self.db:
            row = self.db.execute('SELECT conversation_key, body, state FROM sends WHERE send_key=?', (send_key,)).fetchone()
            if not row or row[2] != 'pending':
                return False
            self.db.execute("UPDATE sends SET state='confirmed' WHERE send_key=?", (send_key,))
            self.db.execute('INSERT OR IGNORE INTO messages VALUES (?,?,?,?)',
                            (row[0], observed_message_id, 'assistant', row[1]))
        return True

    def send_state(self, send_key: str) -> str | None:
        row = self.db.execute('SELECT state FROM sends WHERE send_key=?', (send_key,)).fetchone()
        return row[0] if row else None

    def close(self) -> None:
        self.db.close()
