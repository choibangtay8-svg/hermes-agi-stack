"""Offline epistemic gap discovery."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Any
import json, logging, re
log=logging.getLogger(__name__)
@dataclass
class LearningQuest:
 topic:str
 reason:str
 priority:float = 0.5
 sources:list[str] = field(default_factory=list)
class GBrainClient(Protocol):
 def search(self,query:str)->list[dict]:...
 def list_pages(self)->list[dict]:...
class NoopGBrainClient:
 def search(self,query):return []
 def list_pages(self):return []
class CuriosityEngine:
 def __init__(self,vault_path,client=None,max_quests=5):self.vault_path=Path(vault_path).expanduser();self.client=client or NoopGBrainClient();self.max_quests=max_quests;self._queue=[]
 def scan_vault(self):
  raw=self.vault_path/'raw_notes'; ent=self.vault_path/'entities'; refs='\n'.join(p.read_text(errors='ignore') for p in ent.rglob('*.md')) if ent.exists() else '' ; gaps=[]
  for p in raw.rglob('*.md') if raw.exists() else []:
   txt=p.read_text(errors='ignore'); reasons=[]
   links={m.group(1).split('|',1)[0].split('#',1)[0] for m in re.finditer(r'\[\[([^\]]+)\]\]',refs)}
   if p.stem not in links and p.name not in links:reasons.append('unlinked note')
   headings=list(re.finditer(r'(?m)^\s*#{1,6}\s*[^\n]+\s*$',txt))
   if headings and any(not txt[m.end(): (headings[i+1].start() if i+1<len(headings) else len(txt))].strip() for i,m in enumerate(headings)):reasons.append('empty section')
   if re.search(r'\b(TODO|FIXME)\b',txt):reasons.append('TODO/FIXME')
   if reasons:gaps.append({'topic':p.stem,'reason':', '.join(reasons),'priority':.7,'sources':[str(p)]})
  return gaps
 def failed_runs(self,logs_dir=None):
  d=Path(logs_dir or self.vault_path/'agent_logs'); out=[]
  for p in d.glob('*.jsonl') if d.exists() else []:
   for line in p.read_text(errors='ignore').splitlines():
    try:
     x=json.loads(line)
     if x.get('ok') is False:out.append({'topic':x.get('tool','agent failure'),'reason':x.get('error','failed run'),'priority':.8,'sources':[str(p)]})
    except Exception:continue
  return out
 def propose_quests(self):
  items=self.scan_vault()+self.failed_runs();
  try: items += [{'topic':x.get('title',x.get('name','external')), 'reason':'client result','priority':.5,'sources':[str(x)]} for x in self.client.search('knowledge gaps')]
  except Exception: pass
  merged={}
  for x in items:
   q=merged.setdefault(x['topic'],LearningQuest(x['topic'],x['reason'],x.get('priority',.5),list(x.get('sources',[]))));q.priority=max(q.priority,x.get('priority',.5));q.sources.extend(s for s in x.get('sources',[]) if s not in q.sources)
  self._queue=sorted(merged.values(),key=lambda q:q.priority,reverse=True)[:self.max_quests];return self._queue
 def run_idle_cycle(self):
  try:return self.propose_quests()
  except Exception:return []
 def next_quest(self):
  if not self._queue:self.propose_quests()
  return self._queue.pop(0) if self._queue else None
__all__=['LearningQuest','GBrainClient','NoopGBrainClient','CuriosityEngine']
