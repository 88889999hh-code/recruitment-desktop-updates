import tempfile
import unittest
from pathlib import Path

from conversation_store import ConversationStore, conversation_key
from safety import PlatformPermission, require_active_outreach, require_live_send, require_paid_model_call


class ConversationStoreTests(unittest.TestCase):
    def test_same_name_different_stable_ids_never_merge(self):
        first = conversation_key('boss:conversation:1001')
        second = conversation_key('boss:conversation:1002')
        self.assertNotEqual(first, second)
        with self.assertRaisesRegex(ValueError, '稳定会话 ID'):
            conversation_key('')

    def test_history_persists_across_restart_and_unknown_send_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / 'history.db'
            key = conversation_key('boss:conversation:1001')
            store = ConversationStore(database)
            self.assertTrue(store.record_inbound(key, 'message:1', '请问每天直播多久？'))
            self.assertFalse(store.record_inbound(key, 'message:1', '请问每天直播多久？'))
            send_key, state = store.reserve_send(key, 'message:1', '每天直播 3 小时。')
            self.assertEqual(state, 'pending')
            store.mark_unknown(send_key)
            self.assertEqual(store.send_state(send_key), 'unknown')
            self.assertEqual(store.reserve_send(key, 'message:1', '每天直播 3 小时。')[1], 'unknown')
            self.assertFalse(store.confirm_send(send_key, 'outbound:1'))
            store.close()

            reopened = ConversationStore(database)
            self.assertEqual(reopened.history(key), [{'role': 'user', 'content': '请问每天直播多久？'}])
            self.assertEqual(reopened.send_state(send_key), 'unknown')
            other_key = conversation_key('boss:conversation:1002')
            self.assertEqual(reopened.history(other_key), [])
            reopened.close()

    def test_confirmed_send_requires_observed_platform_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ConversationStore(Path(tmp) / 'history.db')
            key = conversation_key('boss:conversation:1001')
            send_key, _ = store.reserve_send(key, 'message:2', '可以继续聊具体安排。')
            with self.assertRaisesRegex(ValueError, '平台发送回执'):
                store.confirm_send(send_key, '')
            self.assertEqual(store.send_state(send_key), 'pending')
            self.assertTrue(store.confirm_send(send_key, 'outbound:2'))
            self.assertFalse(store.confirm_send(send_key, 'outbound:2'))
            self.assertEqual(store.history(key), [{'role': 'assistant', 'content': '可以继续聊具体安排。'}])
            store.close()

    def test_twelve_rounds_continue_after_wechat_exchange_and_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / 'history.db'
            key = conversation_key('boss:conversation:1001')
            store = ConversationStore(database)
            for turn in range(1, 7):
                inbound = f'in:{turn}'
                text = '可以交换微信吗？' if turn == 3 else f'第 {turn} 轮问题'
                store.record_inbound(key, inbound, text)
                send_key, state = store.reserve_send(key, inbound, f'第 {turn} 轮答复')
                self.assertEqual(state, 'pending')
                self.assertTrue(store.confirm_send(send_key, f'out:{turn}'))
            store.close()

            store = ConversationStore(database)
            for turn in range(7, 13):
                inbound = f'in:{turn}'
                store.record_inbound(key, inbound, f'第 {turn} 轮问题')
                send_key, state = store.reserve_send(key, inbound, f'第 {turn} 轮答复')
                self.assertEqual(state, 'pending')
                self.assertTrue(store.confirm_send(send_key, f'out:{turn}'))
            history = store.history(key, limit=30)
            self.assertEqual(len(history), 24)
            self.assertIn('交换微信', history[4]['content'])
            self.assertEqual(history[-1], {'role': 'assistant', 'content': '第 12 轮答复'})
            store.close()


class SafetyTests(unittest.TestCase):
    def test_external_actions_are_closed_by_default(self):
        for action in (require_live_send, require_active_outreach, require_paid_model_call):
            with self.assertRaises(PermissionError):
                action()
        with self.assertRaises(PermissionError):
            require_live_send(PlatformPermission(platform_approved=True, adapter_verified=True))


if __name__ == '__main__':
    unittest.main()
