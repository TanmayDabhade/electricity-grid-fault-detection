"""
Fault type definitions and data structures.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class FaultType(Enum):
    """Types of electrical faults."""
    SLG = "slg"       # Single Line to Ground
    LL = "ll"         # Line to Line
    DLG = "dlg"       # Double Line to Ground
    LLL = "lll"       # Three Phase (balanced)
    OPEN = "open"     # Open Circuit
    
    @property
    def display_name(self) -> str:
        """Human-readable name for the fault type."""
        names = {
            FaultType.SLG: "Single Line-to-Ground (SLG)",
            FaultType.LL: "Line-to-Line (LL)",
            FaultType.DLG: "Double Line-to-Ground (DLG)",
            FaultType.LLL: "Three-Phase (LLL)",
            FaultType.OPEN: "Open Circuit"
        }
        return names.get(self, str(self.value))
    
    @property
    def severity(self) -> int:
        """Severity rating (1-5, 5 being most severe)."""
        severity_map = {
            FaultType.OPEN: 2,
            FaultType.SLG: 3,
            FaultType.LL: 4,
            FaultType.DLG: 4,
            FaultType.LLL: 5
        }
        return severity_map.get(self, 3)


@dataclass
class Fault:
    """
    Represents a fault in the power system.
    
    Attributes:
        fault_type: Type of fault
        location_type: 'bus' or 'line'
        element_id: ID of the faulted bus or line
        position: For line faults, position as fraction (0.0 to 1.0)
        resistance: Fault resistance in Ohms
        is_active: Whether the fault is currently active
        detected: Whether the fault has been detected
        detected_location: Estimated fault location by detection algorithm
    """
    fault_type: FaultType
    location_type: str  # 'bus' or 'line'
    element_id: int
    position: float = 0.5  # For line faults
    resistance: float = 0.0  # Fault resistance (Ohms)
    is_active: bool = True
    detected: bool = False
    detected_location: Optional[float] = None  # Estimated position
    
    @property
    def is_bus_fault(self) -> bool:
        return self.location_type == 'bus'
    
    @property
    def is_line_fault(self) -> bool:
        return self.location_type == 'line'
    
    def get_detection_error(self) -> Optional[float]:
        """
        Calculate the error in fault location detection.
        
        Returns:
            Absolute error in position (0.0 to 1.0), or None if not detected
        """
        if not self.detected or self.detected_location is None:
            return None
        if self.is_line_fault:
            return abs(self.detected_location - self.position)
        return 0.0 if self.detected else None
    
    def __repr__(self) -> str:
        loc_str = f"Bus {self.element_id}" if self.is_bus_fault else f"Line {self.element_id} @ {self.position:.0%}"
        status = "ACTIVE" if self.is_active else "CLEARED"
        detected_str = f", DETECTED @ {self.detected_location:.0%}" if self.detected else ""
        return f"Fault({self.fault_type.value}, {loc_str}, R={self.resistance}Ω, {status}{detected_str})"
