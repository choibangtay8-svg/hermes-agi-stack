"""Offline epistemic gap discovery."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
from typing import Protocol, Any
import json, logging, os, re
from urllib.request import Request, urlopen
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
class ScanState:
 def __init__(self,path=None):self.path=Path(path or '~/knowledge-vault/agent_logs/.curiosity_state.json').expanduser();self._items=self._load()
 def _load(self):
  try:
   data=json.loads(self.path.read_text());return data if isinstance(data,dict) else {}
  except Exception:return {}
 def _key(self,topic):return sha1(topic.encode()).hexdigest()[:12]
 def seen(self,topic:str)->bool:
  try:return self._key(topic) in self._items
  except Exception:return False
 def mark(self,topic:str):
  try:
   self._items[self._key(topic)]=datetime.now(timezone.utc).isoformat();self.path.parent.mkdir(parents=True,exist_ok=True)
   tmp=self.path.with_name(self.path.name+'.tmp');tmp.write_text(json.dumps(self._items,indent=2,sort_keys=True)+'\n');os.replace(tmp,self.path)
  except Exception:log.warning('Could not persist curiosity scan state',exc_info=True)
 def count(self)->int:
  try:return len(self._items)
  except Exception:return 0
class GBrainSync:
 def __init__(self,base_url='http://127.0.0.1:8765',token=None):
  self.base_url=base_url.rstrip('/');self.endpoint=self.base_url if self.base_url.endswith('/mcp') else self.base_url+'/mcp';self.token=token if token is not None else self._token();self._session=None;self._initialized=False;self._request_id=0
 def _token(self):
  if os.environ.get('GBRAIN_MCP_TOKEN'):return os.environ['GBRAIN_MCP_TOKEN']
  try:
   root=Path(__file__).resolve().parent.parent
   for directory in (root,*root.parents):
    path=directory/'config/gbrain.config.local.json'
    if path.exists():return json.loads(path.read_text()).get('mcp',{}).get('token','')
  except Exception:pass
  return ''
 def _post(self,method,params=None,notification=False):
  self._request_id+=1;payload={'jsonrpc':'2.0','method':method}
  if not notification:payload['id']=self._request_id
  if params is not None:payload['params']=params
  headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'}
  if self.token:headers['Authorization']='Bearer '+self.token
  if self._session:headers['Mcp-Session-Id']=self._session
  with urlopen(Request(self.endpoint,data=json.dumps(payload).encode(),headers=headers,method='POST'),timeout=10) as response:
   self._session=response.headers.get('Mcp-Session-Id') or self._session;body=response.read().decode()
  if notification:return {}
  if 'data:' in body:
   messages=[line[5:].strip() for line in body.splitlines() if line.startswith('data:') and line[5:].strip() not in ('','[DONE]')]
   return json.loads(messages[-1]) if messages else {}
  return json.loads(body)
 def _initialize(self):
  response=self._post('initialize',{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'curiosity-daemon','version':'2'}})
  if response.get('error'):raise RuntimeError(str(response['error']))
  self._post('notifications/initialized',notification=True);self._initialized=True
 def sync_page(self,title:str,md_body:str)->bool:
  try:
   if not self._initialized:self._initialize()
   frontmatter=f"---\ntitle: {title}\nsource: curiosity-daemon\n---\n"
   response=self._post('tools/call',{'name':'put_page','arguments':{'slug':f'agent_logs/{title}','content':frontmatter+md_body}})
   if response.get('error'):raise RuntimeError(str(response['error']))
   result=response.get('result',{});items=result.get('content') or []
   return not any(i.get('isError') for i in items if isinstance(i,dict))
  except Exception as exc:log.warning('GBrain sync failed: %s',exc);return False
class CuriosityEngine:
 def __init__(self,vault_path,client=None,max_quests=5,state=None):self.vault_path=Path(vault_path).expanduser();self.client=client or NoopGBrainClient();self.max_quests=max_quests;self.state=state or ScanState(self.vault_path/'agent_logs/.curiosity_state.json');self._queue=[]
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
  self._queue=[q for q in sorted(merged.values(),key=lambda q:q.priority,reverse=True)[:self.max_quests] if not self.state.seen(q.topic)];return self._queue
 def mark_processed(self,topic):self.state.mark(topic)
 def write_artifact(self,quests,log_dir=None)->Path:
  try:
   directory=Path(log_dir or self.vault_path)/'agent_logs';directory.mkdir(parents=True,exist_ok=True);now=datetime.now(timezone.utc);path=directory/f"curiosity_{now.strftime('%Y%m%dT%H%M%SZ')}.md"
   lines=['---',f'generated_at: {now.isoformat()}',f'quest_count: {len(quests)}','source: curiosity-daemon','---','','## Quests','']
   for quest in quests:
    lines += [f'### {quest.topic}','','status: open','',f'Reason: {quest.reason}','','Priority: {quest.priority}','','Sources:']
    lines += [f'- {source}' for source in quest.sources] or ['- none'];lines.append('')
   path.write_text('\n'.join(lines)+'\n');return path
  except Exception as exc:log.warning('Could not write curiosity artifact: %s',exc);return Path('')
 def run_idle_cycle(self):
  try:return self.propose_quests()
  except Exception:return []
 def next_quest(self):
  if not self._queue:self.propose_quests()
  return self._queue.pop(0) if self._queue else None
__all__=['LearningQuest','GBrainClient','NoopGBrainClient','ScanState','GBrainSync','CuriosityEngine']
