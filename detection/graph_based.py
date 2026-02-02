"""
Graph-based fault detection and localization.

Uses network topology analysis to identify faulted sections
based on protection device signals and power flow anomalies.
"""

import numpy as np
from typing import Optional, List, Dict, Set, Tuple
from dataclasses import dataclass
from collections import deque


@dataclass
class FaultSection:
    """Represents a suspected fault section in the grid."""
    bus_ids: Set[int]
    line_ids: Set[int]
    probability: float
    evidence: List[str]


@dataclass
class GraphDetectionResult:
    """Result of graph-based fault detection."""
    detected: bool
    fault_sections: List[FaultSection]
    faulted_line_id: Optional[int] = None
    faulted_bus_id: Optional[int] = None
    estimated_position: Optional[float] = None
    message: str = ""


class GraphBasedDetector:
    """
    Graph-based fault localization using network topology analysis.
    
    This approach uses:
    1. Current flow direction analysis
    2. Voltage profile analysis  
    3. Topology connectivity to narrow down fault location
    4. Multi-terminal fault location using synchronized measurements
    """
    
    def __init__(self, grid):
        self.grid = grid
        self.voltage_deviations: Dict[int, float] = {}
        self.current_anomalies: Dict[int, float] = {}
        
    def detect_fault(self, fault=None) -> GraphDetectionResult:
        """
        Run graph-based fault detection algorithm.
        
        Uses network analysis to identify the faulted section.
        
        Args:
            fault: Active Fault object (for simulation)
            
        Returns:
            GraphDetectionResult with findings
        """
        if not fault or not fault.is_active:
            return GraphDetectionResult(
                detected=False,
                fault_sections=[],
                message="No active fault in the system"
            )
        
        # Step 1: Analyze voltage deviations
        self._analyze_voltages()
        
        # Step 2: Analyze current flows
        self._analyze_currents()
        
        # Step 3: Find affected section using graph traversal
        affected_buses = self._find_affected_buses()
        
        # Step 4: Narrow down to specific element
        result = self._localize_fault(fault, affected_buses)
        
        return result
    
    def _analyze_voltages(self):
        """
        Analyze voltage deviations from nominal at each bus.
        
        Large voltage drops indicate proximity to fault.
        """
        self.voltage_deviations.clear()
        
        for bus in self.grid.buses.values():
            # Deviation from nominal (1.0 pu)
            deviation = abs(1.0 - bus.voltage_pu)
            self.voltage_deviations[bus.id] = deviation
    
    def _analyze_currents(self):
        """
        Analyze current flow anomalies on each line.
        
        Lines with abnormally high currents are likely near the fault.
        """
        self.current_anomalies.clear()
        
        for line in self.grid.lines.values():
            # Anomaly score based on loading
            if line.is_closed:
                anomaly = line.loading_percent / 100.0
                if line.is_faulted:
                    anomaly = 5.0  # Very high anomaly for faulted line
            else:
                anomaly = 0.0
            self.current_anomalies[line.id] = anomaly
    
    def _find_affected_buses(self, threshold: float = 0.05) -> Set[int]:
        """
        Find buses with significant voltage deviation.
        
        Uses BFS from the most affected bus to find the affected region.
        
        Args:
            threshold: Minimum voltage deviation to consider affected
            
        Returns:
            Set of affected bus IDs
        """
        affected = set()
        
        # Start from buses with largest deviations
        sorted_buses = sorted(
            self.voltage_deviations.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        for bus_id, deviation in sorted_buses:
            if deviation >= threshold:
                affected.add(bus_id)
        
        return affected
    
    def _localize_fault(self, fault, affected_buses: Set[int]) -> GraphDetectionResult:
        """
        Narrow down fault location using graph analysis.
        
        Args:
            fault: Active Fault object
            affected_buses: Set of affected bus IDs
            
        Returns:
            GraphDetectionResult
        """
        fault_sections = []
        
        # Check for faulted lines first
        for line in self.grid.lines.values():
            if line.is_faulted:
                # Found the faulted line directly
                section = FaultSection(
                    bus_ids={line.from_bus.id, line.to_bus.id},
                    line_ids={line.id},
                    probability=0.95,
                    evidence=[
                        f"Line {line.id} has fault indicator",
                        f"Current anomaly: {self.current_anomalies.get(line.id, 0):.2f}",
                        f"Voltage deviation at {line.from_bus.name}: "
                        f"{self.voltage_deviations.get(line.from_bus.id, 0):.3f}"
                    ]
                )
                fault_sections.append(section)
                
                # Estimate position using two-terminal method
                estimated_pos = self._two_terminal_location(line)
                
                # Update fault with detection
                if fault.is_line_fault and fault.element_id == line.id:
                    fault.detected = True
                    fault.detected_location = estimated_pos
                
                return GraphDetectionResult(
                    detected=True,
                    fault_sections=fault_sections,
                    faulted_line_id=line.id,
                    estimated_position=estimated_pos,
                    message=f"Fault localized to Line {line.id} "
                           f"({line.from_bus.name} - {line.to_bus.name}) "
                           f"at estimated position {estimated_pos:.1%}"
                )
        
        # Check for faulted buses
        for bus in self.grid.buses.values():
            if bus.is_faulted:
                connected_lines = self.grid.get_connected_lines(bus.id)
                
                section = FaultSection(
                    bus_ids={bus.id},
                    line_ids={l.id for l in connected_lines},
                    probability=0.9,
                    evidence=[
                        f"Bus {bus.id} ({bus.name}) has fault indicator",
                        f"Voltage deviation: {self.voltage_deviations.get(bus.id, 0):.3f}"
                    ]
                )
                fault_sections.append(section)
                
                if fault.is_bus_fault and fault.element_id == bus.id:
                    fault.detected = True
                
                return GraphDetectionResult(
                    detected=True,
                    fault_sections=fault_sections,
                    faulted_bus_id=bus.id,
                    message=f"Fault localized to Bus {bus.id} ({bus.name})"
                )
        
        # If no direct indicators, use voltage drop analysis
        if affected_buses:
            # Find the bus with maximum voltage drop
            max_drop_bus = max(
                affected_buses,
                key=lambda b: self.voltage_deviations.get(b, 0)
            )
            
            section = FaultSection(
                bus_ids=affected_buses,
                line_ids=set(),
                probability=0.5,
                evidence=[
                    f"Region centered on Bus {max_drop_bus} shows voltage anomalies",
                    f"Affected buses: {len(affected_buses)}"
                ]
            )
            fault_sections.append(section)
            
            return GraphDetectionResult(
                detected=True,
                fault_sections=fault_sections,
                faulted_bus_id=max_drop_bus,
                message=f"Possible fault in region around Bus {max_drop_bus}"
            )
        
        return GraphDetectionResult(
            detected=False,
            fault_sections=[],
            message="Could not localize fault using graph analysis"
        )
    
    def _two_terminal_location(self, line) -> float:
        """
        Estimate fault position using two-terminal method.
        
        Uses voltage measurements at both ends to estimate fault location.
        
        Args:
            line: Faulted TransmissionLine
            
        Returns:
            Estimated position (0.0 to 1.0)
        """
        v_from = abs(line.from_bus.voltage_complex)
        v_to = abs(line.to_bus.voltage_complex)
        
        # The bus with lower voltage is closer to the fault
        if v_from + v_to < 1e-10:
            return 0.5
        
        # Linear interpolation based on voltage drops
        drop_from = 1.0 - v_from
        drop_to = 1.0 - v_to
        
        total_drop = drop_from + drop_to
        if total_drop < 1e-10:
            return 0.5
        
        # Position estimate: higher drop at from_bus means fault is closer to from_bus
        position = drop_from / total_drop
        
        return max(0.0, min(1.0, position))
    
    def find_shortest_path(self, from_bus_id: int, to_bus_id: int) -> List[int]:
        """
        Find shortest path between two buses using BFS.
        
        Args:
            from_bus_id: Starting bus ID
            to_bus_id: Ending bus ID
            
        Returns:
            List of bus IDs forming the path
        """
        if from_bus_id == to_bus_id:
            return [from_bus_id]
        
        visited = {from_bus_id}
        queue = deque([(from_bus_id, [from_bus_id])])
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in self.grid.get_neighbors(current):
                if neighbor == to_bus_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # No path found
    
    def get_network_sections(self) -> List[Set[int]]:
        """
        Identify connected sections (islands) in the network.
        
        Useful for detecting if a fault has split the network.
        
        Returns:
            List of sets, each containing bus IDs in a connected section
        """
        visited = set()
        sections = []
        
        for bus_id in self.grid.buses:
            if bus_id not in visited:
                # BFS to find all connected buses
                section = set()
                queue = deque([bus_id])
                
                while queue:
                    current = queue.popleft()
                    if current in visited:
                        continue
                    
                    visited.add(current)
                    section.add(current)
                    
                    for neighbor in self.grid.get_neighbors(current):
                        # Only traverse if connecting line is closed
                        line = self.grid.get_line_between(current, neighbor)
                        if line and line.is_closed and neighbor not in visited:
                            queue.append(neighbor)
                
                if section:
                    sections.append(section)
        
        return sections
    
    def reset(self):
        """Reset detector state."""
        self.voltage_deviations.clear()
        self.current_anomalies.clear()
