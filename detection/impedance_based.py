"""
Impedance-based fault detection using distance relay principles.

This module implements fault localization using apparent impedance measurements,
similar to how distance relays work in real power systems.
"""

import numpy as np
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from config import ZONE1_REACH, ZONE2_REACH, ZONE3_REACH, IMPEDANCE_BASE


@dataclass
class RelayMeasurement:
    """Simulated relay measurement data."""
    line_id: int
    voltage: complex  # Measured voltage (pu)
    current: complex  # Measured current (pu)
    apparent_impedance: complex  # Calculated Z = V/I
    
    
@dataclass
class DetectionResult:
    """Result of fault detection."""
    detected: bool
    line_id: Optional[int] = None
    estimated_position: Optional[float] = None  # 0.0 to 1.0
    zone: Optional[int] = None  # 1, 2, or 3
    confidence: float = 0.0  # 0.0 to 1.0
    message: str = ""


class ImpedanceBasedDetector:
    """
    Impedance-based fault detector using distance relay simulation.
    
    Distance relays measure the apparent impedance (Z = V/I) seen from the relay
    location. During a fault, the measured impedance decreases proportionally to
    the distance to the fault.
    
    Zone Settings:
    - Zone 1: 80% of protected line (instantaneous trip)
    - Zone 2: 120% of protected line (time-delayed)
    - Zone 3: 150% of protected line (backup protection)
    """
    
    def __init__(self, grid):
        self.grid = grid
        self.measurements: Dict[int, RelayMeasurement] = {}
        self.results: List[DetectionResult] = []
        
    def simulate_measurements(self, fault=None) -> Dict[int, RelayMeasurement]:
        """
        Simulate relay measurements at each line terminal.
        
        During a fault, the current increases and the apparent impedance
        seen by the relay drops to approximately the impedance between
        the relay and the fault point.
        
        Args:
            fault: Active Fault object (if any)
            
        Returns:
            Dictionary of line_id -> RelayMeasurement
        """
        self.measurements.clear()
        
        for line in self.grid.lines.values():
            if not line.is_closed and not line.is_faulted:
                continue
                
            # Get bus voltages
            v_from = line.from_bus.voltage_complex
            v_to = line.to_bus.voltage_complex
            
            # Normal operating current
            if abs(line.z_pu) > 1e-10:
                i_normal = (v_from - v_to) / line.z_pu
            else:
                i_normal = complex(0, 0)
            
            # If this line is faulted, simulate fault current
            if line.is_faulted and fault and fault.element_id == line.id:
                # During fault, current increases significantly
                # Apparent impedance = impedance to fault point
                fault_pos = line.fault_location
                z_to_fault = line.z_pu * fault_pos
                
                # Fault current (simplified model)
                z_f_pu = getattr(fault, 'resistance', 0) / IMPEDANCE_BASE
                z_total = z_to_fault + z_f_pu
                
                if abs(z_total) > 1e-10:
                    i_fault = v_from / z_total
                else:
                    i_fault = v_from / 1e-6  # Very large current for bolted fault
                
                # Create measurement with fault conditions
                if abs(i_fault) > 1e-10:
                    z_apparent = v_from / i_fault
                else:
                    z_apparent = complex(float('inf'), float('inf'))
                    
                measurement = RelayMeasurement(
                    line_id=line.id,
                    voltage=v_from,
                    current=i_fault,
                    apparent_impedance=z_apparent
                )
            else:
                # Normal operation
                if abs(i_normal) > 1e-10:
                    z_apparent = v_from / i_normal
                else:
                    z_apparent = complex(float('inf'), float('inf'))
                    
                measurement = RelayMeasurement(
                    line_id=line.id,
                    voltage=v_from,
                    current=i_normal,
                    apparent_impedance=z_apparent
                )
            
            self.measurements[line.id] = measurement
            
        return self.measurements
    
    def detect_fault(self, fault=None) -> DetectionResult:
        """
        Run impedance-based fault detection algorithm.
        
        Checks if measured impedance falls within protection zones.
        
        Args:
            fault: Active Fault object (if any, for simulation)
            
        Returns:
            DetectionResult with findings
        """
        # Get fresh measurements
        self.simulate_measurements(fault)
        
        if not fault or not fault.is_active:
            return DetectionResult(
                detected=False,
                message="No active fault in the system"
            )
        
        # Check each line for zone pickup
        for line_id, measurement in self.measurements.items():
            line = self.grid.get_line(line_id)
            if line is None:
                continue
                
            z_line = line.z_pu  # Total line impedance
            z_apparent = measurement.apparent_impedance
            
            # Skip if impedance is very large (no significant current)
            if abs(z_apparent) > abs(z_line) * 2:
                continue
            
            # Calculate reach ratio (how far into the line the fault appears)
            if abs(z_line) > 1e-10:
                reach_ratio = abs(z_apparent) / abs(z_line)
            else:
                reach_ratio = float('inf')
            
            # Check which zone the fault falls in
            zone = None
            if reach_ratio <= ZONE1_REACH:
                zone = 1
            elif reach_ratio <= ZONE2_REACH:
                zone = 2
            elif reach_ratio <= ZONE3_REACH:
                zone = 3
            
            if zone is not None:
                # Fault detected!
                estimated_pos = min(1.0, reach_ratio)
                
                # Calculate confidence based on how clearly within zone
                if zone == 1:
                    confidence = 0.95 - (reach_ratio / ZONE1_REACH) * 0.1
                elif zone == 2:
                    confidence = 0.8 - ((reach_ratio - ZONE1_REACH) / (ZONE2_REACH - ZONE1_REACH)) * 0.1
                else:
                    confidence = 0.6 - ((reach_ratio - ZONE2_REACH) / (ZONE3_REACH - ZONE2_REACH)) * 0.1
                
                result = DetectionResult(
                    detected=True,
                    line_id=line_id,
                    estimated_position=estimated_pos,
                    zone=zone,
                    confidence=max(0.1, confidence),
                    message=f"Fault detected on Line {line_id} ({line.from_bus.name} - {line.to_bus.name}) "
                           f"at {estimated_pos:.1%} from {line.from_bus.name}, Zone {zone}"
                )
                
                # Update the fault with detected location
                if fault and fault.is_line_fault and fault.element_id == line_id:
                    fault.detected = True
                    fault.detected_location = estimated_pos
                    
                self.results.append(result)
                return result
        
        return DetectionResult(
            detected=False,
            message="Fault not detected by impedance-based protection"
        )
    
    def get_mho_characteristic(self, line_id: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get the Mho characteristic circle for visualization.
        
        The Mho relay has a circular characteristic in the R-X plane
        that passes through the origin.
        
        Args:
            line_id: ID of the line
            
        Returns:
            Tuple of (R_values, X_values) for plotting the circle
        """
        line = self.grid.get_line(line_id)
        if line is None:
            return np.array([]), np.array([])
        
        # Zone 1 reach
        z_reach = line.z_pu * ZONE1_REACH
        
        # Mho circle passes through origin and reaches z_reach
        # Circle center is at z_reach/2, radius is |z_reach|/2
        center = z_reach / 2
        radius = abs(z_reach) / 2
        
        # Generate circle points
        theta = np.linspace(0, 2 * np.pi, 100)
        r_values = center.real + radius * np.cos(theta)
        x_values = center.imag + radius * np.sin(theta)
        
        return r_values, x_values
    
    def reset(self):
        """Reset detector state."""
        self.measurements.clear()
        self.results.clear()
