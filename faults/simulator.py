"""
Fault simulator for injecting and managing faults in the grid.
"""

import numpy as np
import random
from typing import Optional, List, Tuple
from .types import FaultType, Fault
from .models import get_fault_model
from power.impedance import build_sequence_networks
from config import POWER_BASE, IMPEDANCE_BASE


class FaultSimulator:
    """
    Simulates faults in the power grid and calculates fault currents.
    
    Provides methods to:
    - Inject faults at buses or along lines
    - Calculate fault currents using symmetrical components
    - Generate random faults for testing
    """
    
    def __init__(self, grid):
        self.grid = grid
        self.active_faults: List[Fault] = []
        self.fault_currents: dict = {}  # fault_id -> (Ia, Ib, Ic)
        
    def inject_bus_fault(
        self, 
        bus_id: int, 
        fault_type: FaultType,
        resistance: float = 0.0
    ) -> Optional[Fault]:
        """
        Inject a fault at a bus.
        
        Args:
            bus_id: ID of the bus to fault
            fault_type: Type of fault
            resistance: Fault resistance in Ohms
            
        Returns:
            Fault object if successful, None otherwise
        """
        bus = self.grid.get_bus(bus_id)
        if bus is None:
            return None
            
        # Create fault object
        fault = Fault(
            fault_type=fault_type,
            location_type='bus',
            element_id=bus_id,
            resistance=resistance
        )
        
        # Mark bus as faulted
        bus.apply_fault(fault_type.value)
        
        # Calculate fault current
        self._calculate_bus_fault_current(fault)
        
        self.active_faults.append(fault)
        return fault
    
    def inject_line_fault(
        self, 
        line_id: int, 
        fault_type: FaultType,
        position: float = 0.5,
        resistance: float = 0.0
    ) -> Optional[Fault]:
        """
        Inject a fault on a transmission line.
        
        Args:
            line_id: ID of the line to fault
            fault_type: Type of fault
            position: Position along line (0.0 = from_bus, 1.0 = to_bus)
            resistance: Fault resistance in Ohms
            
        Returns:
            Fault object if successful, None otherwise
        """
        line = self.grid.get_line(line_id)
        if line is None:
            return None
            
        position = max(0.0, min(1.0, position))
        
        # Create fault object
        fault = Fault(
            fault_type=fault_type,
            location_type='line',
            element_id=line_id,
            position=position,
            resistance=resistance
        )
        
        # Mark line as faulted
        if fault_type == FaultType.OPEN:
            line.open_line()
        line.apply_fault(fault_type.value, position)
        
        # Calculate fault current
        self._calculate_line_fault_current(fault)
        
        self.active_faults.append(fault)
        return fault
    
    def inject_random_fault(self) -> Optional[Fault]:
        """
        Inject a random fault somewhere in the grid.
        
        Returns:
            Generated Fault object
        """
        # Choose random fault type (weighted towards more common types)
        fault_types = [
            (FaultType.SLG, 0.7),   # Most common
            (FaultType.LL, 0.1),
            (FaultType.DLG, 0.1),
            (FaultType.LLL, 0.05),  # Rare
            (FaultType.OPEN, 0.05)
        ]
        
        rand = random.random()
        cumulative = 0
        fault_type = FaultType.SLG
        for ft, prob in fault_types:
            cumulative += prob
            if rand < cumulative:
                fault_type = ft
                break
        
        # Choose random location (80% line faults, 20% bus faults)
        if random.random() < 0.8 and self.grid.lines:
            # Line fault
            line = random.choice(list(self.grid.lines.values()))
            position = random.uniform(0.1, 0.9)
            resistance = random.uniform(0, 10)  # 0-10 Ohms
            return self.inject_line_fault(line.id, fault_type, position, resistance)
        elif self.grid.buses:
            # Bus fault
            bus = random.choice(list(self.grid.buses.values()))
            resistance = random.uniform(0, 5)
            return self.inject_bus_fault(bus.id, fault_type, resistance)
        
        return None
    
    def clear_fault(self, fault: Fault):
        """Clear a specific fault."""
        fault.is_active = False
        
        if fault.is_bus_fault:
            bus = self.grid.get_bus(fault.element_id)
            if bus:
                bus.clear_fault()
        else:
            line = self.grid.get_line(fault.element_id)
            if line:
                line.clear_fault()
                if fault.fault_type == FaultType.OPEN:
                    line.close_line()
        
        if fault in self.active_faults:
            self.active_faults.remove(fault)
    
    def clear_all_faults(self):
        """Clear all active faults."""
        for fault in self.active_faults.copy():
            self.clear_fault(fault)
        self.active_faults.clear()
        self.fault_currents.clear()
        self.grid.clear_all_faults()
    
    def _calculate_bus_fault_current(self, fault: Fault):
        """Calculate fault current for a bus fault."""
        # Get sequence impedance matrices
        z0_bus, z1_bus, z2_bus = build_sequence_networks(self.grid)
        
        # Get bus index
        bus_ids = sorted(self.grid.buses.keys())
        bus_id_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
        idx = bus_id_to_idx.get(fault.element_id)
        
        if idx is None:
            return
        
        # Pre-fault voltage (assume 1.0 pu)
        v_f = complex(1.0, 0)
        
        # Thevenin impedances at fault point
        z0 = z0_bus[idx, idx]
        z1 = z1_bus[idx, idx]
        z2 = z2_bus[idx, idx]
        
        # Fault resistance in per-unit
        z_f = fault.resistance / IMPEDANCE_BASE
        
        # Get fault model and calculate sequence currents
        model = get_fault_model(fault.fault_type)
        i0, i1, i2 = model.calculate_fault_current(v_f, z0, z1, z2, z_f)
        
        # Convert to phase currents
        ia, ib, ic = model.sequence_to_phase(i0, i1, i2)
        
        # Store results (convert to Amperes)
        i_base = POWER_BASE * 1e6 / (np.sqrt(3) * 220e3)  # Base current in A
        self.fault_currents[id(fault)] = (
            abs(ia) * i_base,
            abs(ib) * i_base,
            abs(ic) * i_base
        )
    
    def _calculate_line_fault_current(self, fault: Fault):
        """Calculate fault current for a line fault."""
        line = self.grid.get_line(fault.element_id)
        if line is None:
            return
        
        # Get sequence impedance matrices
        z0_bus, z1_bus, z2_bus = build_sequence_networks(self.grid)
        
        # For line fault, we use Thevenin equivalent at the from_bus
        # and add the line impedance up to the fault point
        bus_ids = sorted(self.grid.buses.keys())
        bus_id_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
        
        from_idx = bus_id_to_idx.get(line.from_bus.id)
        if from_idx is None:
            return
        
        # Pre-fault voltage
        v_f = complex(1.0, 0)
        
        # Thevenin impedances at from_bus plus line impedance to fault
        z_line_to_fault = line.get_impedance_to_point(fault.position)
        z0_line = line.z0_pu * fault.position
        
        z0 = z0_bus[from_idx, from_idx] + z0_line
        z1 = z1_bus[from_idx, from_idx] + z_line_to_fault
        z2 = z2_bus[from_idx, from_idx] + z_line_to_fault
        
        # Fault resistance in per-unit
        z_f = fault.resistance / IMPEDANCE_BASE
        
        # Get fault model and calculate
        model = get_fault_model(fault.fault_type)
        i0, i1, i2 = model.calculate_fault_current(v_f, z0, z1, z2, z_f)
        
        # Convert to phase currents
        ia, ib, ic = model.sequence_to_phase(i0, i1, i2)
        
        # Store results
        i_base = POWER_BASE * 1e6 / (np.sqrt(3) * 220e3)
        self.fault_currents[id(fault)] = (
            abs(ia) * i_base,
            abs(ib) * i_base,
            abs(ic) * i_base
        )
    
    def get_fault_current(self, fault: Fault) -> Optional[Tuple[float, float, float]]:
        """Get the calculated fault currents (Ia, Ib, Ic) in Amperes."""
        return self.fault_currents.get(id(fault))
    
    def get_active_fault(self) -> Optional[Fault]:
        """Get the first active fault."""
        return self.active_faults[0] if self.active_faults else None
