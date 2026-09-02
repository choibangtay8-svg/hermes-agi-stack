import tempfile
import unittest
from pathlib import Path

from plugins.curiosity_engine import CuriosityEngine, GBrainSync, ScanState


class CuriosityDaemonTests(unittest.TestCase):
    def test_scan_state_roundtrip_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            state = ScanState(path)
            self.assertFalse(state.seen('gap'))
            state.mark('gap')
            self.assertTrue(state.seen('gap'))
            restored = ScanState(path)
            self.assertTrue(restored.seen('gap'))
            self.assertEqual(restored.count(), 1)

    def test_seen_quests_are_filtered(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / 'raw_notes').mkdir()
            (vault / 'raw_notes/gap.md').write_text('TODO learn')
            engine = CuriosityEngine(vault)
            quests = engine.propose_quests()
            self.assertEqual([quest.topic for quest in quests], ['gap'])
            engine.mark_processed('gap')
            self.assertEqual(engine.propose_quests(), [])

    def test_write_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            engine = CuriosityEngine(vault)
            quests = engine.scan_vault()
            from plugins.curiosity_engine import LearningQuest
            path = engine.write_artifact([LearningQuest('missing topic', 'unknown', .8, ['note.md'])])
            self.assertTrue(path.is_file())
            body = path.read_text()
            self.assertIn('source: curiosity-daemon', body)
            self.assertIn('quest_count: 1', body)
            self.assertIn('### missing topic', body)
            self.assertIn('status: open', body)

    def test_gbrain_offline_does_not_raise(self):
        client = GBrainSync('http://127.0.0.1:1', token='test')
        self.assertFalse(client.sync_page('page', 'body'))


if __name__ == '__main__':
    unittest.main()
