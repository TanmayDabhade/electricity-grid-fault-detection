"""
Fault models using symmetrical components method.
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple, Optional
from .types import FaultType


class FaultModel(ABC):
    """
    Abstract base class for fault models.
    
    Uses symmetrical components (sequence networks) to calculate fault currents.
    """
    
    @abstractmethod
    def calculate_fault_current(
        self, 
        v_f: complex,
        z0: complex, 
        z1: complex, 
        z2: complex,
        z_f: float = 0.0
    ) -> Tuple[complex, complex, complex]:
        """
        Calculate sequence fault currents.
        
        Args:
            v_f: Pre-fault voltage (per-unit)
            z0: Zero sequence impedance at fault point
            z1: Positive sequence impedance at fault point
            z2: Negative sequence impedance at fault point
            z_f: Fault resistance (per-unit)
            
        Returns:
            Tuple of (I0, I1, I2) sequence currents
        """
        pass
    
    def sequence_to_phase(
        self, 
        i0: complex, 
        i1: complex, 
        i2: complex
    ) -> Tuple[complex, complex, complex]:
        """
        Convert sequence currents to phase currents using symmetrical components.
        
        [Ia]   [1  1  1 ] [I0]
        [Ib] = [1  a² a ] [I1]
        [Ic]   [1  a  a²] [I2]
        
        where a = e^(j2π/3) = -0.5 + j√3/2
        """
        a = np.exp(1j * 2 * np.pi / 3)
        a2 = a * a
        
        ia = i0 + i1 + i2
        ib = i0 + a2 * i1 + a * i2
        ic = i0 + a * i1 + a2 * i2
        
        return (ia, ib, ic)


class SLGFault(FaultModel):
    """
    Single Line-to-Ground (SLG) fault model.
    
    Sequence network connection: Series connection of Z0, Z1, Z2
    I0 = I1 = I2 = V_f / (Z0 + Z1 + Z2 + 3*Z_f)
    """
    
    fault_type = FaultType.SLG
    
    def calculate_fault_current(
        self, 
        v_f: complex,
        z0: complex, 
        z1: complex, 
        z2: complex,
        z_f: float = 0.0
    ) -> Tuple[complex, complex, complex]:
        z_total = z0 + z1 + z2 + 3 * z_f
        if abs(z_total) < 1e-10:
            z_total = 1e-10
            
        i_seq = v_f / z_total
        return (i_seq, i_seq, i_seq)


class LLFault(FaultModel):
    """
    Line-to-Line (LL) fault model.
    
    Sequence network connection: Parallel Z1 and Z2
    I0 = 0
    I1 = -I2 = V_f / (Z1 + Z2 + Z_f)
    """
    
    fault_type = FaultType.LL
    
    def calculate_fault_current(
        self, 
        v_f: complex,
        z0: complex, 
        z1: complex, 
        z2: complex,
        z_f: float = 0.0
    ) -> Tuple[complex, complex, complex]:
        z_total = z1 + z2 + z_f
        if abs(z_total) < 1e-10:
            z_total = 1e-10
            
        i1 = v_f / z_total
        i2 = -i1
        i0 = complex(0, 0)
        
        return (i0, i1, i2)


class DLGFault(FaultModel):
    """
    Double Line-to-Ground (DLG) fault model.
    
    Sequence network connection: Z1 in series with parallel (Z0+3Zf) and Z2
    """
    
    fault_type = FaultType.DLG
    
    def calculate_fault_current(
        self, 
        v_f: complex,
        z0: complex, 
        z1: complex, 
        z2: complex,
        z_f: float = 0.0
    ) -> Tuple[complex, complex, complex]:
        z0_with_fault = z0 + 3 * z_f
        
        # Parallel combination of Z0+3Zf and Z2
        if abs(z0_with_fault + z2) < 1e-10:
            z_parallel = 0
        else:
            z_parallel = (z0_with_fault * z2) / (z0_with_fault + z2)
        
        z_total = z1 + z_parallel
        if abs(z_total) < 1e-10:
            z_total = 1e-10
            
        i1 = v_f / z_total
        
        # Current divider for I0 and I2
        if abs(z0_with_fault + z2) < 1e-10:
            i0 = i1 / 2
            i2 = i1 / 2
        else:
            i0 = -i1 * z2 / (z0_with_fault + z2)
            i2 = -i1 * z0_with_fault / (z0_with_fault + z2)
        
        return (i0, i1, i2)


class ThreePhaseFault(FaultModel):
    """
    Three-Phase (LLL) balanced fault model.
    
    Most severe fault type. Only positive sequence network involved.
    I1 = V_f / (Z1 + Z_f)
    I0 = I2 = 0
    """
    
    fault_type = FaultType.LLL
    
    def calculate_fault_current(
        self, 
        v_f: complex,
        z0: complex, 
        z1: complex, 
        z2: complex,
        z_f: float = 0.0
    ) -> Tuple[complex, complex, complex]:
        z_total = z1 + z_f
        if abs(z_total) < 1e-10:
            z_total = 1e-10
            
        i1 = v_f / z_total
        i0 = complex(0, 0)
        i2 = complex(0, 0)
        
        return (i0, i1, i2)


class OpenCircuitFault(FaultModel):
    """
    Open Circuit fault model.
    
    Represents a broken conductor or open breaker.
    No fault current, but causes power flow redistribution.
    """
    
    fault_type = FaultType.OPEN
    
    def calculate_fault_current(
        self, 
        v_f: complex,
        z0: complex, 
        z1: complex, 
        z2: complex,
        z_f: float = 0.0
    ) -> Tuple[complex, complex, complex]:
        # Open circuit has no fault current
        return (complex(0, 0), complex(0, 0), complex(0, 0))


def get_fault_model(fault_type: FaultType) -> FaultModel:
    """Get the appropriate fault model for a given fault type."""
    models = {
        FaultType.SLG: SLGFault(),
        FaultType.LL: LLFault(),
        FaultType.DLG: DLGFault(),
        FaultType.LLL: ThreePhaseFault(),
        FaultType.OPEN: OpenCircuitFault()
    }
    return models.get(fault_type, SLGFault())
