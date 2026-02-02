"""
Power Flow calculations using Newton-Raphson method.
"""

import numpy as np
from typing import Dict, Tuple, Optional
from config import BusType, POWER_BASE


class PowerFlow:
    """
    Power Flow solver using Newton-Raphson method.
    
    Solves the power flow equations to determine voltage magnitudes
    and angles at all buses given the generation and load.
    """
    
    def __init__(self, grid, max_iterations: int = 50, tolerance: float = 1e-6):
        self.grid = grid
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        
        # Results
        self.converged = False
        self.iterations = 0
        self.mismatch = float('inf')
        
    def solve(self) -> bool:
        """
        Solve power flow using Newton-Raphson method.
        
        Returns:
            True if converged, False otherwise
        """
        # Build Y-bus matrix
        y_bus = self.grid.build_y_bus()
        n = self.grid.n_buses
        
        # Get bus ordering
        bus_ids = sorted(self.grid.buses.keys())
        bus_id_to_idx = {bus_id: idx for idx, bus_id in enumerate(bus_ids)}
        
        # Initialize voltage vector
        v_mag = np.ones(n)
        v_ang = np.zeros(n)
        
        # Set initial values from bus data
        for bus_id, bus in self.grid.buses.items():
            idx = bus_id_to_idx[bus_id]
            v_mag[idx] = bus.voltage_pu
            v_ang[idx] = np.radians(bus.angle_deg)
        
        # Identify bus types
        slack_idx = None
        pv_indices = []
        pq_indices = []
        
        for bus_id, bus in self.grid.buses.items():
            idx = bus_id_to_idx[bus_id]
            if bus.bus_type == BusType.SLACK:
                slack_idx = idx
            elif bus.bus_type == BusType.PV:
                pv_indices.append(idx)
            else:
                pq_indices.append(idx)
        
        # Power injections (per-unit)
        p_spec = np.zeros(n)
        q_spec = np.zeros(n)
        
        for bus_id, bus in self.grid.buses.items():
            idx = bus_id_to_idx[bus_id]
            p_spec[idx] = bus.p_net / POWER_BASE
            q_spec[idx] = bus.q_net / POWER_BASE
        
        # Non-slack bus indices for angle equations
        non_slack = [i for i in range(n) if i != slack_idx]
        
        # Newton-Raphson iteration
        for iteration in range(self.max_iterations):
            # Calculate power injections
            p_calc, q_calc = self._calculate_power(y_bus, v_mag, v_ang)
            
            # Calculate mismatches
            dp = p_spec - p_calc
            dq = q_spec - q_calc
            
            # Build mismatch vector (exclude slack for P, exclude slack and PV for Q)
            mismatch_p = dp[non_slack]
            mismatch_q = dq[pq_indices]
            mismatch = np.concatenate([mismatch_p, mismatch_q])
            
            # Check convergence
            self.mismatch = np.max(np.abs(mismatch))
            if self.mismatch < self.tolerance:
                self.converged = True
                self.iterations = iteration + 1
                break
            
            # Build Jacobian matrix
            j = self._build_jacobian(y_bus, v_mag, v_ang, non_slack, pq_indices)
            
            # Solve for corrections
            try:
                corrections = np.linalg.solve(j, mismatch)
            except np.linalg.LinAlgError:
                # Singular Jacobian - use pseudo-inverse
                corrections = np.linalg.lstsq(j, mismatch, rcond=None)[0]
            
            # Apply corrections
            n_p = len(non_slack)
            d_ang = corrections[:n_p]
            d_mag = corrections[n_p:]
            
            for i, idx in enumerate(non_slack):
                v_ang[idx] += d_ang[i]
            
            for i, idx in enumerate(pq_indices):
                v_mag[idx] += d_mag[i] * v_mag[idx]  # Relative correction
        
        # Store results back to buses
        for bus_id, bus in self.grid.buses.items():
            idx = bus_id_to_idx[bus_id]
            bus.voltage_pu = v_mag[idx]
            bus.angle_deg = np.degrees(v_ang[idx])
        
        # Calculate line flows
        self._calculate_line_flows(y_bus, v_mag, v_ang, bus_id_to_idx)
        
        return self.converged
    
    def _calculate_power(self, y_bus: np.ndarray, v_mag: np.ndarray, 
                         v_ang: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Calculate active and reactive power injections at each bus."""
        n = len(v_mag)
        p = np.zeros(n)
        q = np.zeros(n)
        
        for i in range(n):
            for j in range(n):
                g_ij = y_bus[i, j].real
                b_ij = y_bus[i, j].imag
                angle_diff = v_ang[i] - v_ang[j]
                
                p[i] += v_mag[i] * v_mag[j] * (g_ij * np.cos(angle_diff) + b_ij * np.sin(angle_diff))
                q[i] += v_mag[i] * v_mag[j] * (g_ij * np.sin(angle_diff) - b_ij * np.cos(angle_diff))
        
        return p, q
    
    def _build_jacobian(self, y_bus: np.ndarray, v_mag: np.ndarray, 
                        v_ang: np.ndarray, non_slack: list, pq_indices: list) -> np.ndarray:
        """Build the Jacobian matrix for Newton-Raphson."""
        n = len(v_mag)
        n_p = len(non_slack)
        n_q = len(pq_indices)
        
        # Full Jacobian submatrices
        j11 = np.zeros((n, n))  # dP/dθ
        j12 = np.zeros((n, n))  # dP/dV
        j21 = np.zeros((n, n))  # dQ/dθ
        j22 = np.zeros((n, n))  # dQ/dV
        
        for i in range(n):
            for j in range(n):
                g_ij = y_bus[i, j].real
                b_ij = y_bus[i, j].imag
                angle_diff = v_ang[i] - v_ang[j]
                
                if i == j:
                    # Diagonal elements
                    p_i = sum(v_mag[i] * v_mag[k] * (y_bus[i, k].real * np.cos(v_ang[i] - v_ang[k]) + 
                              y_bus[i, k].imag * np.sin(v_ang[i] - v_ang[k])) for k in range(n))
                    q_i = sum(v_mag[i] * v_mag[k] * (y_bus[i, k].real * np.sin(v_ang[i] - v_ang[k]) - 
                              y_bus[i, k].imag * np.cos(v_ang[i] - v_ang[k])) for k in range(n))
                    
                    j11[i, i] = -q_i - b_ij * v_mag[i]**2
                    j12[i, i] = p_i / v_mag[i] + g_ij * v_mag[i]
                    j21[i, i] = p_i - g_ij * v_mag[i]**2
                    j22[i, i] = q_i / v_mag[i] - b_ij * v_mag[i]
                else:
                    # Off-diagonal elements
                    j11[i, j] = v_mag[i] * v_mag[j] * (g_ij * np.sin(angle_diff) - b_ij * np.cos(angle_diff))
                    j12[i, j] = v_mag[i] * (g_ij * np.cos(angle_diff) + b_ij * np.sin(angle_diff))
                    j21[i, j] = -v_mag[i] * v_mag[j] * (g_ij * np.cos(angle_diff) + b_ij * np.sin(angle_diff))
                    j22[i, j] = v_mag[i] * (g_ij * np.sin(angle_diff) - b_ij * np.cos(angle_diff))
        
        # Extract relevant parts
        j = np.zeros((n_p + n_q, n_p + n_q))
        
        # J11 block
        for i, row in enumerate(non_slack):
            for j_idx, col in enumerate(non_slack):
                j[i, j_idx] = j11[row, col]
        
        # J12 block
        for i, row in enumerate(non_slack):
            for j_idx, col in enumerate(pq_indices):
                j[i, n_p + j_idx] = j12[row, col]
        
        # J21 block
        for i, row in enumerate(pq_indices):
            for j_idx, col in enumerate(non_slack):
                j[n_p + i, j_idx] = j21[row, col]
        
        # J22 block
        for i, row in enumerate(pq_indices):
            for j_idx, col in enumerate(pq_indices):
                j[n_p + i, n_p + j_idx] = j22[row, col]
        
        return j
    
    def _calculate_line_flows(self, y_bus: np.ndarray, v_mag: np.ndarray, 
                              v_ang: np.ndarray, bus_id_to_idx: Dict):
        """Calculate power flow on each line after solving."""
        for line in self.grid.lines.values():
            if not line.is_closed:
                line.update_loading(0, 0)
                continue
                
            i = bus_id_to_idx[line.from_bus.id]
            j = bus_id_to_idx[line.to_bus.id]
            
            # Complex voltages
            v_i = v_mag[i] * np.exp(1j * v_ang[i])
            v_j = v_mag[j] * np.exp(1j * v_ang[j])
            
            # Current from i to j
            y_series = line.y_pu
            i_ij = (v_i - v_j) * y_series
            
            # Power from i to j
            s_ij = v_i * np.conj(i_ij) * POWER_BASE  # Convert to MW
            
            line.update_loading(abs(i_ij), s_ij.real)
