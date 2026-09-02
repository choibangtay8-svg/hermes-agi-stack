"""Cognitive middleware registry."""
from .causal_sim import CausalGraph
from .curiosity_engine import CuriosityEngine, LearningQuest
from .dialectic_council import DebateRecord, DialecticCouncil
from .paradigm_shift import ParadigmShiftMonitor

REGISTRY = {"causal_sim": CausalGraph, "curiosity_engine": CuriosityEngine,
            "dialectic_council": DialecticCouncil, "paradigm_shift": ParadigmShiftMonitor}
__version__ = "0.1.0"
