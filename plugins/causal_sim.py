"""Trace-derived causal graph utilities."""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any, Iterable, Mapping
import json, logging, math
log=logging.getLogger(__name__)
@dataclass
class TraceStep:
 tool:str
 args:dict = field(default_factory=dict)
 result:Any = None
 ok:bool = False
 duration_ms:float = 0.0
@dataclass
class CounterfactualResult: removed:set[str]; outcome_before:float; outcome_after:float; delta:float; kept_nodes:set[str]
class CausalGraph:
 def __init__(self):
  self.graph=None; self.nodes={}; self.edges=set()
  try:
   import networkx as nx; self.graph=nx.DiGraph()
  except ImportError: pass
 @classmethod
 def from_traces(cls,traces:Iterable[TraceStep|dict]):
  o=cls(); prev=None
  for i,r in enumerate(traces):
   if isinstance(r,TraceStep): t=r
   else:
    args=r.get('args',{}); args=dict(args) if isinstance(args,Mapping) else {}
    try: duration=float(r.get('duration_ms',r.get('duration',0)) or 0)
    except (TypeError,ValueError): duration=0.0
    t=TraceStep(str(r.get('tool','unknown')),args,r.get('result'),bool(r.get('ok',False)),duration)
   n=f'{i}:{t.tool}'; o.nodes[n]=asdict(t); o._node(n,o.nodes[n])
   if prev:o._edge(prev,n)
   parents=(r.get('caused_by') or r.get('parents')) if isinstance(r,dict) else None
   if parents:
    if isinstance(parents,str): parents=[parents]
    for p in parents:o._edge(p if p in o.nodes else next((x for x in o.nodes if x.endswith(':'+str(p))),str(p)),n)
   prev=n
  return o
 def _node(self,n,a):
  if self.graph is not None:self.graph.add_node(n,**a)
 def _edge(self,a,b):
  self.edges.add((a,b));
  if self.graph is not None:self.graph.add_edge(a,b)
 def descendants(self,node):
  if self.graph is not None:
   try:
    import networkx as nx; return set(nx.descendants(self.graph,node))
   except Exception: pass
  seen=set(); stack=[node]
  while stack:
   n=stack.pop()
   for a,b in self.edges:
    if a==n and b not in seen:seen.add(b);stack.append(b)
  return seen
 def _outcome(self,kept,fn,nodes=None):
  nodes = self.nodes if nodes is None else nodes
  if fn:
   if nodes is self.nodes:return float(fn(self,kept))
   original=self.nodes
   graph_attrs={n:dict(self.graph.nodes[n]) for n in nodes if self.graph is not None and n in self.graph}
   try:
    self.nodes=nodes
    if self.graph is not None:
     for name, attrs in nodes.items():
      if name in self.graph: self.graph.nodes[name].clear(); self.graph.nodes[name].update(attrs)
    return float(fn(self,kept))
   finally:
    self.nodes=original
    if self.graph is not None:
     for n,attrs in graph_attrs.items(): self.graph.nodes[n].clear(); self.graph.nodes[n].update(attrs)
  return sum((1 if nodes[n].get('ok') else 0)*math.log1p(float(nodes[n].get('duration_ms') or 0)) for n in kept if n in nodes)
 def counterfactual(self,remove=None,overrides=None,outcome_fn=None):
  rem=set(remove or ()); baseline=dict(self.nodes)
  before=self._outcome(set(baseline),outcome_fn,baseline)
  scenario={n:dict(value) for n,value in baseline.items()}
  for n,v in (overrides or {}).items():
   if n in scenario: scenario[n].update(v if isinstance(v,dict) else {'result':v})
  kept=set(baseline)-rem; after=self._outcome(kept,outcome_fn,scenario)
  return CounterfactualResult(rem,before,after,before-after,kept)
 def prune(self,minimum_contribution=.05,outcome_fn=None):
  drop=[n for n in list(self.nodes) if self.counterfactual({n},outcome_fn=outcome_fn).delta<minimum_contribution]
  for n in drop:self.nodes.pop(n,None)
  self.edges={e for e in self.edges if e[0] not in drop and e[1] not in drop}
  if self.graph is not None:self.graph.remove_nodes_from(drop)
  return drop
 def to_dict(self):return {'nodes':self.nodes,'edges':[list(e) for e in self.edges]}
 def dumps(self):return json.dumps(self.to_dict(),default=str)
__all__=['TraceStep','CounterfactualResult','CausalGraph']
