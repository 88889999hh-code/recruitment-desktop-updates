import tempfile
import unittest
from pathlib import Path

from chat_ai_engine import ChatAIEngine
from conversation_store import ConversationStore, conversation_key
from knowledge_base import KnowledgeBase


class FakeItem:
    def __init__(self, attributes=None, text=''):
        self.attributes = attributes or {}
        self.text = text

    def attr(self, name):
        return self.attributes.get(name)

    def ele(self, selector, timeout=0):
        return None


class FakePage:
    def __init__(self, bubbles):
        self.bubbles = bubbles

    def eles(self, selector, timeout=0):
        return self.bubbles


class HRBOSSSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ConversationStore(Path(self.temp.name) / 'conversations.db')
        self.kb = KnowledgeBase(Path(self.temp.name) / 'knowledge')
        self.logs = []
        self.engine = ChatAIEngine(
            get_page=lambda: None,
            log=lambda message, level='info': self.logs.append((level, message)),
            job_title_getter=lambda: '抖音服装鞋帽兼职带货主播',
            knowledge_base=self.kb,
            deepseek_client=type('NoModel', (), {'available': lambda self: False})(),
            reply_limiter=None,
            reengage_limiter=None,
            cfg_getter=lambda: {},
            store=self.store,
        )

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_stable_conversation_id_required_name_never_identity(self):
        self.assertIsNone(self.engine._stable_conversation_id(FakeItem({'data-geek-id': '42'})))
        first = self.engine._stable_conversation_id(FakeItem({'data-conversation-id': '101'}))
        second = self.engine._stable_conversation_id(FakeItem({'data-conversation-id': '102'}))
        self.assertNotEqual(self.engine._conv_fingerprint('同名', first),
                            self.engine._conv_fingerprint('同名', second))
        with self.assertRaisesRegex(ValueError, '稳定会话 ID'):
            self.engine._conv_fingerprint('同名')

    def test_only_candidate_bubble_with_stable_message_id_is_read(self):
        self.assertIsNone(self.engine._read_last_candidate_message(FakePage([
            FakeItem({'class': 'item-myself', 'data-message-id': 'self:1'}, '我方消息')
        ])))
        self.assertIsNone(self.engine._read_last_candidate_message(FakePage([
            FakeItem({'class': 'item-friend'}, '没有消息 ID')
        ])))
        self.assertEqual(self.engine._read_last_candidate_message(FakePage([
            FakeItem({'class': 'item-friend', 'data-message-id': 'incoming:1'}, '每天直播多久？')
        ])), ('incoming:1', '每天直播多久？'))

    def test_safe_rules_and_wechat_does_not_pause_followup(self):
        key = conversation_key('data-conversation-id:101')
        self.store.record_inbound(key, 'in:1', '每天直播多久？')
        self.assertEqual(self.engine._decide_reply('同名', '每天直播多久？', conversation_id=key)[0],
                         '每天直播 3 小时。')
        self.store.record_inbound(key, 'in:2', '交换微信后还能继续问吗？')
        self.assertNotIn(key, self.engine._paused_conversations)
        self.assertEqual(len(self.store.history(key)), 2)
        self.assertIn('没核实', self.kb.match_rule('薪资怎么算？'))
        prompt = self.kb.build_system_prompt('抖音服装鞋帽兼职带货主播', '性别要求：女', 'unverified-id')
        self.assertNotIn('性别要求：女', prompt)
        self.assertNotIn('unverified-id', prompt)
        self.assertIn('交换后继续回答问题', prompt)
        self.assertIn('自动助手', prompt)

    def test_all_live_entrypoints_fail_closed(self):
        for action in (lambda: self.engine.start_reply_loop(),
                       lambda: self.engine.reply_once(),
                       lambda: self.engine._scan_and_reply_once(FakePage([])),
                       lambda: self.engine._send_message(FakePage([]), 'test'),
                       lambda: self.engine._click_send(FakePage([])),
                       lambda: self.engine.start_reengage_loop()):
            with self.assertRaises(PermissionError):
                action()


if __name__ == '__main__':
    unittest.main()
