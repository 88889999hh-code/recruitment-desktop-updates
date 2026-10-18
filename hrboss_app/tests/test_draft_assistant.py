import tempfile
import unittest
from pathlib import Path
from draft_assistant import OfflineDraftAssistant


class DryRunReplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.worker = OfflineDraftAssistant(self.path / "demo.db", self.path / "kb")

    def tearDown(self):
        self.worker.close()
        self.tmp.cleanup()

    def test_only_demo_identifiers(self):
        with self.assertRaises(ValueError):
            self.worker.accept("real-candidate-id", "1", "你好")
        with self.assertRaises(ValueError):
            self.worker.accept("demo:a", "", "你好")

    def test_fact_checked_multiple_rounds(self):
        for i in range(12):
            out = self.worker.accept("demo:alice", f"in:{i}", "每天直播多久？")
            self.assertEqual(out.state, "awaiting_review")
            self.assertIn("3 小时", out.text)
        self.assertEqual(len(self.worker.history("demo:alice")), 12)
        self.assertFalse(self.worker.db.execute("SELECT COUNT(*) FROM sends").fetchone()[0])

    def test_newbie_and_no_claimed_salary(self):
        self.assertIn("新人", self.worker.accept("demo:alice", "1", "没有经验可以吗？").text)
        self.assertIn("核实", self.worker.accept("demo:alice", "2", "工资多少？").text)

    def test_duplicate_synthetic_event_is_idempotent(self):
        first = self.worker.accept("demo:alice", "in1", "哪里上班？")
        second = self.worker.accept("demo:alice", "in1", "哪里上班？")
        self.assertEqual(first.text, second.text)
        self.assertFalse(second.is_new)
        self.assertEqual(len(self.worker.history("demo:alice")), 1)

    def test_two_conversations_are_isolated(self):
        self.worker.accept("demo:alice", "id1", "每天直播多久？")
        self.worker.accept("demo:bob", "id1", "工资多少？")
        self.assertEqual(self.worker.history("demo:alice")[0]["content"], "每天直播多久？")
        self.assertEqual(self.worker.history("demo:bob")[0]["content"], "工资多少？")

    def test_optout_survives_restart(self):
        self.assertEqual(self.worker.accept("demo:alice", "stop", "不要联系我了").state, "stopped")
        self.worker.close()
        self.worker = OfflineDraftAssistant(self.path / "demo.db", self.path / "kb")
        self.assertEqual(self.worker.accept("demo:alice", "next", "还在吗").state, "stopped")
        self.assertEqual(self.worker.accept("demo:bob", "next", "每天直播多久").state, "awaiting_review")

    def test_copied_is_never_reported_sent(self):
        self.worker.accept("demo:alice", "in1", "每天直播多久？")
        body = self.worker.copy_prepared("demo:alice", "in1")
        self.assertIn("3 小时", body)
        self.assertEqual(self.worker.accept("demo:alice", "in1", "每天直播多久？").state, "copied")
        self.assertEqual(self.worker.db.execute("SELECT count(*) FROM sends").fetchone()[0], 0)

    def test_human_request_discloses_bot(self):
        self.assertIn("自动助手", self.worker.accept("demo:alice", "1", "我想找真人").text)


if __name__ == "__main__":
    unittest.main()
