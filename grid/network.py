"""
Grid class managing the entire electrical network.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from .bus import Bus
from .line import TransmissionLine


class Grid:
    """
    Represents the entire electrical grid network.
    
    Manages buses, transmission lines, and provides network analysis methods.
    
    Attributes:
        name: Name of the grid
        buses: Dictionary of buses keyed by bus ID
        lines: Dictionary of lines keyed by line ID
        adjacency: Adjacency list for graph-based algorithms
    """
    
    def __init__(self, name: str = "220kV Regional Grid"):
        self.name = name
        self.buses: Dict[int, Bus] = {}
        self.lines: Dict[int, TransmissionLine] = {}
        self.adjacency: Dict[int, List[int]] = {}  # bus_id -> [connected_bus_ids]
        
        # Cached matrices (rebuilt when topology changes)
        self._y_bus = None
        self._y_bus_valid = False
        
    def add_bus(self, bus: Bus) -> Bus:
        """Add a bus to the grid."""
        self.buses[bus.id] = bus
        self.adjacency[bus.id] = []
        self._y_bus_valid = False
        return bus
        
    def add_line(self, line: TransmissionLine) -> TransmissionLine:
        """Add a transmission line to the grid."""
        self.lines[line.id] = line
        
        # Update adjacency list (bidirectional)
        from_id = line.from_bus.id
        to_id = line.to_bus.id
        
        if to_id not in self.adjacency[from_id]:
            self.adjacency[from_id].append(to_id)
        if from_id not in self.adjacency[to_id]:
            self.adjacency[to_id].append(from_id)
            
        self._y_bus_valid = False
        return line
    
    def get_bus(self, bus_id: int) -> Optional[Bus]:
        """Get a bus by ID."""
        return self.buses.get(bus_id)
    
    def get_line(self, line_id: int) -> Optional[TransmissionLine]:
        """Get a line by ID."""
        return self.lines.get(line_id)
    
    def get_line_between(self, bus1_id: int, bus2_id: int) -> Optional[TransmissionLine]:
        """Get the transmission line connecting two buses."""
        for line in self.lines.values():
            if ((line.from_bus.id == bus1_id and line.to_bus.id == bus2_id) or
                (line.from_bus.id == bus2_id and line.to_bus.id == bus1_id)):
                return line
        return None
    
    def get_neighbors(self, bus_id: int) -> List[int]:
        """Get IDs of buses directly connected to the given bus."""
        return self.adjacency.get(bus_id, [])
    
    def get_connected_lines(self, bus_id: int) -> List[TransmissionLine]:
        """Get all lines connected to a bus."""
        connected = []
        for line in self.lines.values():
            if line.from_bus.id == bus_id or line.to_bus.id == bus_id:
                connected.append(line)
        return connected
    
    @property
    def n_buses(self) -> int:
        """Number of buses in the grid."""
        return len(self.buses)
    
    @property
    def n_lines(self) -> int:
        """Number of lines in the grid."""
        return len(self.lines)
    
    @property
    def slack_bus(self) -> Optional[Bus]:
        """Get the slack (reference) bus."""
        from config import BusType
        for bus in self.buses.values():
            if bus.bus_type == BusType.SLACK:
                return bus
        return None
    
    def build_y_bus(self) -> np.ndarray:
        """
        Build the bus admittance matrix (Y-bus).
        
        The Y-bus matrix is fundamental for power flow and fault analysis.
        Y_ii = sum of admittances connected to bus i
        Y_ij = -admittance between bus i and j
        
        Returns:
            Complex numpy array of shape (n_buses, n_buses)
        """
        if self._y_bus_valid and self._y_bus is not None:
            return self._y_bus
            
        n = self.n_buses
        y_bus = np.zeros((n, n), dtype=complex)
        
        # Create bus index mapping (bus_id -> matrix index)
        bus_ids = sorted(self.buses.keys())
        self._bus_id_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
        self._idx_to_bus_id = {idx: bus_id for idx, bus_id in enumerate(bus_ids)}
        
        for line in self.lines.values():
            if not line.is_closed:
                continue  # Skip open lines
                
            i = self._bus_id_to_idx[line.from_bus.id]
            j = self._bus_id_to_idx[line.to_bus.id]
            
            y_series = line.y_pu  # Series admittance
            y_shunt = complex(0, line.b_pu / 2)  # Half of shunt admittance at each end
            
            # Off-diagonal elements
            y_bus[i, j] -= y_series
            y_bus[j, i] -= y_series
            
            # Diagonal elements (self-admittance)
            y_bus[i, i] += y_series + y_shunt
            y_bus[j, j] += y_series + y_shunt
            
        self._y_bus = y_bus
        self._y_bus_valid = True
        return y_bus
    
    def build_z_bus(self) -> np.ndarray:
        """
        Build the bus impedance matrix (Z-bus).
        
        Z-bus = inverse of Y-bus, used for fault analysis.
        
        Returns:
            Complex numpy array of shape (n_buses, n_buses)
        """
        y_bus = self.build_y_bus()
        try:
            z_bus = np.linalg.inv(y_bus)
        except np.linalg.LinAlgError:
            # Singular matrix - add small regularization
            z_bus = np.linalg.inv(y_bus + np.eye(self.n_buses) * 1e-10)
        return z_bus
    
    def get_faulted_elements(self) -> Tuple[List[Bus], List[TransmissionLine]]:
        """Get all currently faulted buses and lines."""
        faulted_buses = [b for b in self.buses.values() if b.is_faulted]
        faulted_lines = [l for l in self.lines.values() if l.is_faulted]
        return faulted_buses, faulted_lines
    
    def clear_all_faults(self):
        """Clear all faults in the grid."""
        for bus in self.buses.values():
            bus.clear_fault()
        for line in self.lines.values():
            line.clear_fault()
            if not line.is_closed:
                line.close_line()
                
    def invalidate_matrices(self):
        """Mark cached matrices as invalid (call after topology changes)."""
        self._y_bus_valid = False
        
    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Get the bounding box of bus positions (for visualization)."""
        if not self.buses:
            return (0, 0, 1, 1)
            
        xs = [b.x for b in self.buses.values()]
        ys = [b.y for b in self.buses.values()]
        margin = 50
        return (min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin)
    
    def __repr__(self) -> str:
        return f"Grid('{self.name}', buses={self.n_buses}, lines={self.n_lines})"
