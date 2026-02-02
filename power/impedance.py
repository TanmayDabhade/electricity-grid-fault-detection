"""
Impedance calculations for power system analysis.
"""

import numpy as np
from typing import Tuple
from config import IMPEDANCE_BASE, ZERO_SEQ_RESISTANCE_RATIO, ZERO_SEQ_REACTANCE_RATIO


def calculate_line_impedance(length_km: float, r_per_km: float, x_per_km: float) -> complex:
    """
    Calculate total line impedance.
    
    Args:
        length_km: Line length in kilometers
        r_per_km: Resistance per kilometer (Ohms/km)
        x_per_km: Reactance per kilometer (Ohms/km)
        
    Returns:
        Complex impedance in Ohms
    """
    return complex(r_per_km * length_km, x_per_km * length_km)


def impedance_to_pu(z_ohm: complex, z_base: float = IMPEDANCE_BASE) -> complex:
    """Convert impedance from Ohms to per-unit."""
    return z_ohm / z_base


def impedance_to_ohm(z_pu: complex, z_base: float = IMPEDANCE_BASE) -> complex:
    """Convert impedance from per-unit to Ohms."""
    return z_pu * z_base


def calculate_sequence_impedances(z1_pu: complex) -> Tuple[complex, complex, complex]:
    """
    Calculate sequence impedances from positive sequence impedance.
    
    For transmission lines:
    - Positive sequence (Z1) = Negative sequence (Z2)
    - Zero sequence (Z0) is typically 2-3x higher
    
    Args:
        z1_pu: Positive sequence impedance in per-unit
        
    Returns:
        Tuple of (Z0, Z1, Z2) in per-unit
    """
    z0_pu = complex(
        z1_pu.real * ZERO_SEQ_RESISTANCE_RATIO,
        z1_pu.imag * ZERO_SEQ_REACTANCE_RATIO
    )
    z2_pu = z1_pu  # Negative sequence equals positive sequence for lines
    
    return (z0_pu, z1_pu, z2_pu)


def build_sequence_networks(grid) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Build sequence impedance matrices for the grid.
    
    Args:
        grid: Grid object
        
    Returns:
        Tuple of (Z0_bus, Z1_bus, Z2_bus) matrices
    """
    # Get positive sequence Z-bus
    z1_bus = grid.build_z_bus()
    
    # For transmission lines, Z2 = Z1
    z2_bus = z1_bus.copy()
    
    # Build Z0 matrix with higher impedances
    n = grid.n_buses
    y0_bus = np.zeros((n, n), dtype=complex)
    
    bus_ids = sorted(grid.buses.keys())
    bus_id_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
    
    for line in grid.lines.values():
        if not line.is_closed:
            continue
            
        i = bus_id_to_idx[line.from_bus.id]
        j = bus_id_to_idx[line.to_bus.id]
        
        # Zero sequence impedance
        z0 = line.z0_pu
        if abs(z0) > 1e-10:
            y0 = 1.0 / z0
        else:
            y0 = complex(0, 0)
            
        y0_bus[i, j] -= y0
        y0_bus[j, i] -= y0
        y0_bus[i, i] += y0
        y0_bus[j, j] += y0
    
    # Invert to get Z0
    try:
        z0_bus = np.linalg.inv(y0_bus)
    except np.linalg.LinAlgError:
        z0_bus = np.linalg.inv(y0_bus + np.eye(n) * 1e-10)
    
    return (z0_bus, z1_bus, z2_bus)


def apparent_impedance(voltage: complex, current: complex) -> complex:
    """
    Calculate apparent impedance seen by a relay.
    
    Z_apparent = V / I
    
    Args:
        voltage: Complex voltage at relay location
        current: Complex current through relay
        
    Returns:
        Apparent impedance in the same units as V/I
    """
    if abs(current) > 1e-10:
        return voltage / current
    return complex(float('inf'), float('inf'))


def distance_to_fault(z_apparent: complex, z_line_per_km: complex) -> float:
    """
    Estimate distance to fault using impedance.
    
    Args:
        z_apparent: Apparent impedance measured by relay
        z_line_per_km: Line impedance per kilometer
        
    Returns:
        Estimated distance to fault in km
    """
    if abs(z_line_per_km) > 1e-10:
        # Use magnitude ratio for distance estimation
        return abs(z_apparent) / abs(z_line_per_km)
    return 0.0
