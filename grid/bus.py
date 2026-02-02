"""
Bus class representing substations/nodes in the power grid.
"""

import numpy as np
from config import BusType, NOMINAL_VOLTAGE


class Bus:
    """
    Represents a bus (substation/node) in the power grid.
    
    Attributes:
        id: Unique identifier for the bus
        name: Human-readable name (e.g., "Delhi Substation")
        bus_type: Type of bus (SLACK, PV, PQ)
        voltage_kv: Nominal voltage level in kV
        voltage_pu: Voltage magnitude in per-unit
        angle_deg: Voltage angle in degrees
        p_gen: Active power generation in MW
        q_gen: Reactive power generation in MVAR
        p_load: Active power load in MW
        q_load: Reactive power load in MVAR
        x, y: Position coordinates for visualization
        is_faulted: Flag indicating if bus has an active fault
    """
    
    def __init__(
        self,
        bus_id: int,
        name: str,
        bus_type: str = BusType.PQ,
        voltage_kv: float = NOMINAL_VOLTAGE,
        x: float = 0.0,
        y: float = 0.0
    ):
        self.id = bus_id
        self.name = name
        self.bus_type = bus_type
        self.voltage_kv = voltage_kv
        
        # Electrical state (per-unit values)
        self.voltage_pu = 1.0  # Initial voltage magnitude
        self.angle_deg = 0.0   # Initial voltage angle
        
        # Power injection (positive = generation, negative = load)
        self.p_gen = 0.0  # MW
        self.q_gen = 0.0  # MVAR
        self.p_load = 0.0  # MW
        self.q_load = 0.0  # MVAR
        
        # Visualization position
        self.x = x
        self.y = y
        
        # Fault status
        self.is_faulted = False
        self.fault_type = None
        
    @property
    def p_net(self) -> float:
        """Net active power injection (generation - load) in MW."""
        return self.p_gen - self.p_load
    
    @property
    def q_net(self) -> float:
        """Net reactive power injection in MVAR."""
        return self.q_gen - self.q_load
    
    @property
    def s_net(self) -> complex:
        """Net complex power injection in MVA."""
        return complex(self.p_net, self.q_net)
    
    @property
    def voltage_complex(self) -> complex:
        """Complex voltage in per-unit (magnitude * e^(j*angle))."""
        angle_rad = np.radians(self.angle_deg)
        return self.voltage_pu * np.exp(1j * angle_rad)
    
    def set_as_generator(self, p_gen: float, q_gen: float = 0.0, v_setpoint: float = 1.0):
        """Configure bus as a generator (PV bus)."""
        self.bus_type = BusType.PV
        self.p_gen = p_gen
        self.q_gen = q_gen
        self.voltage_pu = v_setpoint
        
    def set_as_load(self, p_load: float, q_load: float = 0.0):
        """Configure bus as a load (PQ bus)."""
        self.bus_type = BusType.PQ
        self.p_load = p_load
        self.q_load = q_load
        
    def set_as_slack(self, voltage_pu: float = 1.0, angle_deg: float = 0.0):
        """Configure bus as slack/reference bus."""
        self.bus_type = BusType.SLACK
        self.voltage_pu = voltage_pu
        self.angle_deg = angle_deg
        
    def apply_fault(self, fault_type: str):
        """Apply a fault at this bus."""
        self.is_faulted = True
        self.fault_type = fault_type
        
    def clear_fault(self):
        """Clear any fault at this bus."""
        self.is_faulted = False
        self.fault_type = None
        
    def __repr__(self) -> str:
        return (f"Bus({self.id}, '{self.name}', type={self.bus_type}, "
                f"V={self.voltage_pu:.3f}∠{self.angle_deg:.1f}°)")
