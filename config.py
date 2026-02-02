"""
Configuration constants for the 220kV Indian Regional Grid Simulator.
"""

# Voltage levels (kV)
NOMINAL_VOLTAGE = 220  # kV
VOLTAGE_BASE = 220  # kV for per-unit calculations

# Power base for per-unit system
POWER_BASE = 100  # MVA

# Impedance base (Z_base = V_base^2 / S_base)
IMPEDANCE_BASE = (VOLTAGE_BASE ** 2) / POWER_BASE  # Ohms = 484 Ohms

# Typical 220kV transmission line parameters (per km)
# ACSR Moose conductor (typical for 220kV in India)
LINE_RESISTANCE_PER_KM = 0.035  # Ohms/km
LINE_REACTANCE_PER_KM = 0.37   # Ohms/km
LINE_SUSCEPTANCE_PER_KM = 4.0e-6  # Siemens/km (shunt capacitance)

# Sequence impedance ratios (for fault calculations)
ZERO_SEQ_RESISTANCE_RATIO = 3.0  # Z0/Z1 ratio for resistance
ZERO_SEQ_REACTANCE_RATIO = 3.0   # Z0/Z1 ratio for reactance

# Protection settings
ZONE1_REACH = 0.80  # 80% of line impedance
ZONE2_REACH = 1.20  # 120% of line impedance
ZONE3_REACH = 1.50  # 150% of line impedance (backup)

# Fault settings
FAULT_RESISTANCE_MIN = 0.0   # Ohms (bolted fault)
FAULT_RESISTANCE_MAX = 50.0  # Ohms (high resistance ground fault)

# Visualization settings
ANIMATION_INTERVAL = 50  # milliseconds per frame
GRID_UPDATE_RATE = 20    # Hz

# Color scheme for visualization
COLORS = {
    'bus_generation': '#2ecc71',    # Green - generation bus
    'bus_load': '#3498db',          # Blue - load bus
    'bus_slack': '#9b59b6',         # Purple - slack/reference bus
    'bus_fault': '#e74c3c',         # Red - faulted bus
    'line_normal': '#7f8c8d',       # Gray - normal line
    'line_overload': '#e67e22',     # Orange - overloaded line
    'line_fault': '#e74c3c',        # Red - faulted line
    'line_open': '#95a5a6',         # Light gray - open/disconnected
    'flow_particle': '#f1c40f',     # Yellow - power flow particle
    'background': '#1a1a2e',        # Dark blue - background
    'grid_lines': '#16213e',        # Darker blue - grid lines
}

# Bus types
class BusType:
    SLACK = 'slack'      # Reference bus (voltage angle = 0)
    PV = 'pv'            # Generator bus (P and V specified)
    PQ = 'pq'            # Load bus (P and Q specified)

# Fault types
class FaultType:
    SLG = 'slg'          # Single Line to Ground
    LL = 'll'            # Line to Line
    DLG = 'dlg'          # Double Line to Ground
    LLL = 'lll'          # Three Phase (balanced)
    OPEN = 'open'        # Open circuit
