"""
TransmissionLine class representing 220kV transmission lines.
"""

import numpy as np
from config import (
    LINE_RESISTANCE_PER_KM,
    LINE_REACTANCE_PER_KM,
    LINE_SUSCEPTANCE_PER_KM,
    ZERO_SEQ_RESISTANCE_RATIO,
    ZERO_SEQ_REACTANCE_RATIO,
    IMPEDANCE_BASE
)


class TransmissionLine:
    """
    Represents a transmission line connecting two buses.
    
    Uses the PI-model for transmission line representation:
    
        From Bus ----[Z]---- To Bus
                  |       |
                 [Y/2]   [Y/2]
                  |       |
                 GND     GND
    
    Attributes:
        id: Unique identifier for the line
        from_bus: Starting bus object
        to_bus: Ending bus object
        length_km: Line length in kilometers
        r_pu: Series resistance in per-unit
        x_pu: Series reactance in per-unit
        b_pu: Shunt susceptance in per-unit (total, both ends)
        rating_mva: Thermal rating in MVA
        is_closed: Whether the line breaker is closed (in service)
        is_faulted: Flag indicating if line has an active fault
        fault_location: Location of fault as fraction (0.0 to 1.0) from from_bus
    """
    
    def __init__(
        self,
        line_id: int,
        from_bus,
        to_bus,
        length_km: float,
        r_per_km: float = LINE_RESISTANCE_PER_KM,
        x_per_km: float = LINE_REACTANCE_PER_KM,
        b_per_km: float = LINE_SUSCEPTANCE_PER_KM,
        rating_mva: float = 400.0
    ):
        self.id = line_id
        self.from_bus = from_bus
        self.to_bus = to_bus
        self.length_km = length_km
        
        # Calculate line parameters
        self.r_ohm = r_per_km * length_km
        self.x_ohm = x_per_km * length_km
        self.b_siemens = b_per_km * length_km  # Total shunt susceptance
        
        # Convert to per-unit
        self.r_pu = self.r_ohm / IMPEDANCE_BASE
        self.x_pu = self.x_ohm / IMPEDANCE_BASE
        self.b_pu = self.b_siemens * IMPEDANCE_BASE
        
        # Zero sequence parameters (for ground faults)
        self.r0_pu = self.r_pu * ZERO_SEQ_RESISTANCE_RATIO
        self.x0_pu = self.x_pu * ZERO_SEQ_REACTANCE_RATIO
        
        self.rating_mva = rating_mva
        
        # Line status
        self.is_closed = True  # Breaker status
        self.is_faulted = False
        self.fault_type = None
        self.fault_location = 0.5  # Default: middle of line
        
        # Current flow (for visualization)
        self.current_pu = 0.0
        self.power_flow_mw = 0.0
        self.loading_percent = 0.0
        
    @property
    def z_pu(self) -> complex:
        """Series impedance in per-unit."""
        return complex(self.r_pu, self.x_pu)
    
    @property
    def z_ohm(self) -> complex:
        """Series impedance in Ohms."""
        return complex(self.r_ohm, self.x_ohm)
    
    @property
    def y_pu(self) -> complex:
        """Series admittance in per-unit."""
        if abs(self.z_pu) > 1e-10:
            return 1.0 / self.z_pu
        return complex(0, 0)
    
    @property
    def z0_pu(self) -> complex:
        """Zero sequence impedance in per-unit."""
        return complex(self.r0_pu, self.x0_pu)
    
    @property
    def z_per_km_pu(self) -> complex:
        """Impedance per kilometer in per-unit."""
        if self.length_km > 0:
            return self.z_pu / self.length_km
        return complex(0, 0)
    
    def get_impedance_to_point(self, distance_fraction: float) -> complex:
        """
        Get impedance from from_bus to a point along the line.
        
        Args:
            distance_fraction: Fraction of line length (0.0 = from_bus, 1.0 = to_bus)
            
        Returns:
            Impedance in per-unit
        """
        distance_fraction = max(0.0, min(1.0, distance_fraction))
        return self.z_pu * distance_fraction
    
    def open_line(self):
        """Open the line (trip breakers)."""
        self.is_closed = False
        
    def close_line(self):
        """Close the line (close breakers)."""
        self.is_closed = True
        self.is_faulted = False
        self.fault_type = None
        
    def apply_fault(self, fault_type: str, location: float = 0.5):
        """
        Apply a fault on this line.
        
        Args:
            fault_type: Type of fault (SLG, LL, DLG, LLL, OPEN)
            location: Fault location as fraction (0.0 to 1.0) from from_bus
        """
        self.is_faulted = True
        self.fault_type = fault_type
        self.fault_location = max(0.0, min(1.0, location))
        
    def clear_fault(self):
        """Clear any fault on this line."""
        self.is_faulted = False
        self.fault_type = None
        
    def get_fault_position_xy(self) -> tuple:
        """Get the (x, y) coordinates of the fault location for visualization."""
        x = self.from_bus.x + self.fault_location * (self.to_bus.x - self.from_bus.x)
        y = self.from_bus.y + self.fault_location * (self.to_bus.y - self.from_bus.y)
        return (x, y)
    
    def update_loading(self, current_pu: float, power_mw: float):
        """Update the current flow and loading percentage."""
        self.current_pu = current_pu
        self.power_flow_mw = power_mw
        self.loading_percent = (abs(power_mw) / self.rating_mva) * 100 if self.rating_mva > 0 else 0
        
    def __repr__(self) -> str:
        status = "CLOSED" if self.is_closed else "OPEN"
        fault_str = f", FAULT@{self.fault_location:.0%}" if self.is_faulted else ""
        return (f"Line({self.id}, {self.from_bus.name} -> {self.to_bus.name}, "
                f"{self.length_km:.1f}km, Z={self.z_pu:.4f}pu, {status}{fault_str})")
