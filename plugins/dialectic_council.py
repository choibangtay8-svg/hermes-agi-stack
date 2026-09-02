"""Deterministic thesis/antithesis/synthesis council."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Callable
import logging, re
log=logging.getLogger(__name__)
class Role(Enum): THESIS='thesis'; ANTITHESIS='antithesis'; SYNTHESIS='synthesis'
@dataclass
class DebateTurn: role:Role; claim:str; critique:str; confidence:float
@dataclass
class DebateRecord: topic:str; turns:list[DebateTurn]; verdict:str; confidence:float; verified:bool|None; notes:str=''
DebaterFn=Callable[[Role,str,list[DebateTurn]],str]
class DialecticCouncil:
 def __init__(self,debater:DebaterFn|None=None,max_rounds:int=2):self.debater=debater;self.max_rounds=max_rounds
 def run_debate(self,topic):
  turns=[]
  for _ in range(max(1,self.max_rounds)):
   thesis=self._ask(Role.THESIS,topic,turns); turns.append(DebateTurn(Role.THESIS,thesis,'',.72))
   anti=self._ask(Role.ANTITHESIS,topic,turns); turns.append(DebateTurn(Role.ANTITHESIS,anti,'',.68))
   syn=self._ask(Role.SYNTHESIS,topic,turns); turns.append(DebateTurn(Role.SYNTHESIS,syn,'',.76))
  verified=self._verify_with_z3([t.claim for t in turns if t.role is Role.SYNTHESIS]); conf=sum(t.confidence for t in turns)/len(turns)
  if verified is False:conf=max(0,conf-.2)
  elif verified is True:conf=min(.95,conf+.1)
  return DebateRecord(topic,turns,'Accept with falsifiable checks' if verified is not False else 'Reject pending contradictions',conf,verified,'heuristic offline council')
 def _ask(self,role,topic,turns):
  if self.debater:return self.debater(role,topic,turns)
  if role is Role.THESIS:return f'{topic} is viable under stated constraints.'
  if role is Role.ANTITHESIS:return f'Objection: {topic} may fail under scale, cost, or adversarial stress.'
  return f'Synthesis: adopt {topic} conditionally; verify assumptions with measurable tests.'
 def _verify_with_z3(self,claims):
  try: import z3
  except ImportError:return None
  enc=0
  try:
   s=z3.Solver()
   for c in claims:
    m=re.search(r'(\w+)\s*(==|=|<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)',c)
    if m:
     v=z3.Real(m.group(1)); num=float(m.group(3)); op=m.group(2); expr={'=':v==num,'==':v==num,'<':v<num,'>':v>num,'<=':v<=num,'>=':v>=num}[op];s.add(expr);enc+=1
   return bool(enc and s.check()==z3.sat)
  except Exception:return None
__all__=['Role','DebateTurn','DebateRecord','DebaterFn','DialecticCouncil']
