"""Failure-rate drift monitor."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from pathlib import Path
from datetime import datetime, timezone
import json, logging
log=logging.getLogger(__name__)
@dataclass
class DriftEvent: skill:str; baseline_rate:float; recent_rate:float; delta:float; window:int; at:str
class ParadigmShiftMonitor:
 def __init__(self,window_size=20,drift_threshold=.25,min_samples=5,ontology_reset_after=2):self.window_size=window_size;self.drift_threshold=drift_threshold;self.min_samples=min_samples;self.ontology_reset_after=ontology_reset_after;self.history=defaultdict(lambda:deque(maxlen=window_size));self.events=defaultdict(list);self._last_windows={}
 def record(self,skill,ok):self.history[skill].append(bool(ok))
 def failure_count(self,skill):return sum(not x for x in self.history[skill])
 def success_rate(self,skill):
  h=self.history[skill];return sum(h)/len(h) if h else 0.0
 def baseline_rate(self,skill):
  h=list(self.history[skill]); n=max(1,len(h)//2);return sum(h[:n])/n if h else 0.0
 def detect_drift(self):
  out=[]
  for s,h in self.history.items():
   if len(h)<self.min_samples:continue
   a=list(h); half=len(a)//2; a=a[:half*2]; mid=half
   b=sum(a[:mid])/mid; r=sum(a[mid:])/mid; d=b-r
   if d>self.drift_threshold:
    key=(len(a), tuple(a))
    if getattr(self,'_last_windows',{}).get(s)!=key:
     e=DriftEvent(s,b,r,d,len(a),datetime.now(timezone.utc).isoformat());out.append(e);self.events[s].append(e)
     self._last_windows[s]=key
  return out
 def should_reset(self,skill):return len(self.events[skill])>=self.ontology_reset_after
 def emit_event(self,event,log_dir=None):
  try:
   d=Path(log_dir or 'agent_logs');d.mkdir(parents=True,exist_ok=True)
   with (d/'ontology_events.jsonl').open('a') as f:f.write(json.dumps(asdict(event) if hasattr(event,'__dataclass_fields__') else event,default=str)+'\n')
  except Exception:pass
 def emit_ontology_reset(self,skill,log_dir=None):self.emit_event({'type':'ontology_reset','skill':skill,'at':datetime.now(timezone.utc).isoformat()},log_dir)
 def reset(self,skill):self.history[skill].clear();self.events[skill].clear();self._last_windows.pop(skill,None)
__all__=['DriftEvent','ParadigmShiftMonitor']
