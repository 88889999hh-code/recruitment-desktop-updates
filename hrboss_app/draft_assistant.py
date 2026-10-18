"""Offline review-only sample-message workflow: never reads BOSS or sends."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from conversation_store import ConversationStore, conversation_key
from knowledge_base import KnowledgeBase

STOP_RE = re.compile(r"(停止联系|别再联系|不要联系|请勿联系|不想聊了|不感兴趣|别发了|不再联系)")
HUMAN_RE = re.compile(r"(转人工|人工客服|真人|找负责人)")
EXPERIENCE_RE = re.compile(r"(没经验|没有经验|不会直播|新手|零基础)")


@dataclass(frozen=True)
class DraftOutcome:
    state: str
    text: str = ""
    is_new: bool = False


class OfflineDraftAssistant:
    """Accepts only synthetic IDs. Creates reviewable drafts without delivery."""

    def __init__(self, db_path: Path, knowledge_dir: Path):
        self.store = ConversationStore(db_path)
        self.kb = KnowledgeBase(knowledge_dir)
        self.db = self.store.db
        with self.db:
            self.db.execute("""CREATE TABLE IF NOT EXISTS draft_previews (
                conversation_key TEXT NOT NULL,
                inbound_message_id TEXT NOT NULL,
                body TEXT NOT NULL,
                review_state TEXT NOT NULL CHECK(review_state IN ('awaiting_review','copied')),
                PRIMARY KEY(conversation_key,inbound_message_id)
            )""")
            self.db.execute("CREATE TABLE IF NOT EXISTS optouts (conversation_key TEXT PRIMARY KEY)")

    def accept(self, synthetic_conversation_id: str, message_id: str, text: str) -> DraftOutcome:
        if not isinstance(synthetic_conversation_id, str) or not synthetic_conversation_id.startswith("demo:"):
            raise ValueError("只接受 demo: 开头的虚拟测试会话，不读取真实求职者")
        if not isinstance(message_id, str) or not message_id.strip() or not isinstance(text, str) or not text.strip():
            raise ValueError("请输入有效消息 ID 和模拟问题")
        key = conversation_key(synthetic_conversation_id)
        text = text.strip()
        is_new = self.store.record_inbound(key, message_id, text)
        if STOP_RE.search(text):
            with self.db:
                self.db.execute("INSERT OR IGNORE INTO optouts VALUES (?)", (key,))
            return DraftOutcome("stopped", "", is_new)
        if self.db.execute("SELECT 1 FROM optouts WHERE conversation_key=?", (key,)).fetchone():
            return DraftOutcome("stopped", "", is_new)
        existing = self.db.execute(
            "SELECT body, review_state FROM draft_previews WHERE conversation_key=? AND inbound_message_id=?",
            (key, message_id),
        ).fetchone()
        if existing:
            return DraftOutcome(existing[1], existing[0], False)
        reply = self._prepare(text)
        with self.db:
            self.db.execute("INSERT INTO draft_previews VALUES (?,?,?,?)",
                            (key, message_id, reply, "awaiting_review"))
        return DraftOutcome("awaiting_review", reply, is_new)

    def _prepare(self, message: str) -> str:
        if HUMAN_RE.search(message):
            return "我是招聘自动助手。你可以联系招聘负责人进一步确认，我会先记录你的问题。"
        if EXPERIENCE_RE.search(message):
            return "新人也可以了解这个兼职带货主播岗位。每天直播 3 小时，你想先了解哪些具体要求？"
        rule = self.kb.match_rule(message)
        if rule:
            return rule
        return "这个问题目前没有经过核实，我先记录，确认后再答复。你也可以提出其他岗位相关问题。"

    def copy_prepared(self, synthetic_conversation_id: str, message_id: str) -> Optional[str]:
        if not synthetic_conversation_id.startswith("demo:"):
            raise ValueError("仅允许模拟会话")
        key = conversation_key(synthetic_conversation_id)
        row = self.db.execute(
            "SELECT body FROM draft_previews WHERE conversation_key=? AND inbound_message_id=?",
            (key, message_id),
        ).fetchone()
        if not row:
            return None
        with self.db:
            self.db.execute("UPDATE draft_previews SET review_state='copied' "
                            "WHERE conversation_key=? AND inbound_message_id=?", (key, message_id))
        return row[0]  # Copied != sent or confirmed.

    def history(self, synthetic_conversation_id: str):
        return self.store.history(conversation_key(synthetic_conversation_id), 100)

    def close(self):
        self.store.close()
