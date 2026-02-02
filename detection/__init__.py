"""
Detection module - Fault detection and localization algorithms.
"""

from .impedance_based import ImpedanceBasedDetector
from .graph_based import GraphBasedDetector

__all__ = ['ImpedanceBasedDetector', 'GraphBasedDetector']
