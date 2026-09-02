import unittest, tempfile
from pathlib import Path
from plugins.causal_sim import CausalGraph, TraceStep, CounterfactualResult
from plugins.curiosity_engine import LearningQuest
from plugins.dialectic_council import DialecticCouncil
from plugins.curiosity_engine import CuriosityEngine
from plugins.paradigm_shift import ParadigmShiftMonitor
class T(unittest.TestCase):
 def test_causal(self):
  g=CausalGraph.from_traces([TraceStep('a',{},None,True,10),TraceStep('b',{},None,False,1),TraceStep('c',{},None,True,10)])
  self.assertEqual(len(g.nodes),3); self.assertIn('2:c',g.descendants('0:a')); self.assertNotEqual(g.counterfactual({'0:a'}).outcome_before,g.counterfactual({'0:a'}).outcome_after); self.assertIn('1:b',g.prune(.1))
  before=dict(g.nodes); g.counterfactual(overrides={'0:a': {'ok': False}}); self.assertEqual(g.nodes,before); self.assertIsInstance(g.counterfactual(),CounterfactualResult)
  g2=CausalGraph.from_traces([{'tool':'x','args':None,'duration_ms':'bad'}]); self.assertEqual(g2.nodes['0:x']['args'],{}); self.assertEqual(g2.nodes['0:x']['duration_ms'],0.0)
 def test_debate(self):
  r=DialecticCouncil().run_debate('build system'); self.assertGreaterEqual(len(r.turns),3); self.assertTrue(r.verdict); self.assertIsInstance(r.confidence,float)
 def test_curiosity(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d); (p/'raw_notes').mkdir(); (p/'entities').mkdir(); (p/'raw_notes'/'Gap.md').write_text('hello'); e=CuriosityEngine(p); self.assertEqual(e.run_idle_cycle()[0].topic,'Gap'); self.assertIsNotNone(e.next_quest())
   (p/'raw_notes'/'Cat.md').write_text('# One\nbody\n# Empty\n'); (p/'entities'/'E.md').write_text('[[Caterpillar]]'); self.assertIn('Cat', [x['topic'] for x in e.scan_vault()])
  self.assertEqual(CuriosityEngine('/missing').run_idle_cycle(),[])
  self.assertIsNot(LearningQuest('x','r').sources, LearningQuest('x','r').sources)
 def test_drift(self):
  m=ParadigmShiftMonitor(window_size=10,min_samples=5)
  for x in [1,1,1,1,1,0,0,0,0,0]:m.record('s',x)
  self.assertTrue(m.detect_drift()); self.assertFalse(m.detect_drift()); e=m.events['s'][0]; self.assertEqual((e.baseline_rate,e.recent_rate),(1.0,0.0)); m.reset('s'); self.assertFalse(m.detect_drift()); self.assertEqual(m.failure_count('s'),0)
if __name__=='__main__':unittest.main()
