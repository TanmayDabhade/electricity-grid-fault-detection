"""
Demo 220kV Indian Regional Grid.

Creates a realistic regional grid topology loosely inspired by 
the Northern Indian power grid structure.
"""

from .bus import Bus
from .line import TransmissionLine
from .network import Grid
from config import BusType


def create_demo_grid() -> Grid:
    r"""
    Create a demo 220kV regional grid for India.
    
    This creates a 12-bus system representing a simplified regional grid
    with generation, load, and interconnection buses.
    
    Grid Topology (approximate layout)::
    
                    [1-DELHI]
                   /    |    \
           [2-GURG]  [3-NOIDA]  [4-GHAZ]
              |         |          |
           [5-JAI]   [6-AGRA]   [7-MEER]
              |    \    |    /     |
           [8-AJMER] [9-MATHURA] [10-SAHARAN]
              |         |          |
           [11-UDAI]  [12-LUCKNOW]--+
    
    Returns:
        Configured Grid object
    """
    grid = Grid("220kV Northern India Regional Grid")
    
    # Create buses (substations)
    # Position coordinates are for visualization (x, y in pixels)
    
    # Main hub
    b1 = grid.add_bus(Bus(1, "Delhi", BusType.SLACK, x=400, y=100))
    b1.set_as_slack(voltage_pu=1.0, angle_deg=0.0)
    b1.p_gen = 500  # MW
    
    # Ring 1 - Around Delhi
    b2 = grid.add_bus(Bus(2, "Gurugram", BusType.PQ, x=250, y=200))
    b2.set_as_load(p_load=150, q_load=50)
    
    b3 = grid.add_bus(Bus(3, "Noida", BusType.PV, x=400, y=220))
    b3.set_as_generator(p_gen=200, q_gen=50, v_setpoint=1.02)
    
    b4 = grid.add_bus(Bus(4, "Ghaziabad", BusType.PQ, x=550, y=200))
    b4.set_as_load(p_load=180, q_load=60)
    
    # Ring 2 - State capitals / major cities
    b5 = grid.add_bus(Bus(5, "Jaipur", BusType.PV, x=150, y=350))
    b5.set_as_generator(p_gen=300, q_gen=100, v_setpoint=1.01)
    
    b6 = grid.add_bus(Bus(6, "Agra", BusType.PQ, x=400, y=350))
    b6.set_as_load(p_load=200, q_load=70)
    
    b7 = grid.add_bus(Bus(7, "Meerut", BusType.PQ, x=600, y=350))
    b7.set_as_load(p_load=120, q_load=40)
    
    # Ring 3 - Outer ring
    b8 = grid.add_bus(Bus(8, "Ajmer", BusType.PQ, x=100, y=500))
    b8.set_as_load(p_load=80, q_load=25)
    
    b9 = grid.add_bus(Bus(9, "Mathura", BusType.PQ, x=350, y=480))
    b9.set_as_load(p_load=90, q_load=30)
    
    b10 = grid.add_bus(Bus(10, "Saharanpur", BusType.PQ, x=650, y=480))
    b10.set_as_load(p_load=100, q_load=35)
    
    # Outer nodes
    b11 = grid.add_bus(Bus(11, "Udaipur", BusType.PV, x=50, y=650))
    b11.set_as_generator(p_gen=250, q_gen=80, v_setpoint=1.0)
    
    b12 = grid.add_bus(Bus(12, "Lucknow", BusType.PV, x=550, y=620))
    b12.set_as_generator(p_gen=350, q_gen=120, v_setpoint=1.02)
    
    # Create transmission lines
    # Line lengths are approximate distances in km
    
    # From Delhi hub
    grid.add_line(TransmissionLine(1, b1, b2, length_km=30))   # Delhi-Gurugram
    grid.add_line(TransmissionLine(2, b1, b3, length_km=25))   # Delhi-Noida
    grid.add_line(TransmissionLine(3, b1, b4, length_km=35))   # Delhi-Ghaziabad
    
    # Ring 1 to Ring 2
    grid.add_line(TransmissionLine(4, b2, b5, length_km=250))  # Gurugram-Jaipur
    grid.add_line(TransmissionLine(5, b3, b6, length_km=200))  # Noida-Agra
    grid.add_line(TransmissionLine(6, b4, b7, length_km=70))   # Ghaziabad-Meerut
    
    # Ring 2 interconnections
    grid.add_line(TransmissionLine(7, b5, b6, length_km=240))  # Jaipur-Agra
    grid.add_line(TransmissionLine(8, b6, b7, length_km=180))  # Agra-Meerut
    
    # Ring 2 to Ring 3
    grid.add_line(TransmissionLine(9, b5, b8, length_km=140))   # Jaipur-Ajmer
    grid.add_line(TransmissionLine(10, b5, b9, length_km=260))  # Jaipur-Mathura
    grid.add_line(TransmissionLine(11, b6, b9, length_km=60))   # Agra-Mathura
    grid.add_line(TransmissionLine(12, b7, b10, length_km=170)) # Meerut-Saharanpur
    
    # Ring 3 to outer nodes
    grid.add_line(TransmissionLine(13, b8, b11, length_km=280))  # Ajmer-Udaipur
    grid.add_line(TransmissionLine(14, b9, b12, length_km=400))  # Mathura-Lucknow
    grid.add_line(TransmissionLine(15, b10, b12, length_km=350)) # Saharanpur-Lucknow
    
    # Additional cross-connections for redundancy
    grid.add_line(TransmissionLine(16, b2, b3, length_km=40))    # Gurugram-Noida
    grid.add_line(TransmissionLine(17, b3, b4, length_km=30))    # Noida-Ghaziabad
    
    return grid


def create_simple_grid() -> Grid:
    """
    Create a simple 5-bus test grid for algorithm testing.
    
    Topology:
        [1]---[2]---[3]
         |     |     |
        [4]---[5]---+
    
    Returns:
        Simple Grid object
    """
    grid = Grid("Simple 5-Bus Test Grid")
    
    # Create buses
    b1 = grid.add_bus(Bus(1, "Gen-1", BusType.SLACK, x=100, y=100))
    b1.set_as_slack(voltage_pu=1.0)
    b1.p_gen = 100
    
    b2 = grid.add_bus(Bus(2, "Bus-2", BusType.PQ, x=300, y=100))
    b2.set_as_load(p_load=40, q_load=10)
    
    b3 = grid.add_bus(Bus(3, "Gen-2", BusType.PV, x=500, y=100))
    b3.set_as_generator(p_gen=60, v_setpoint=1.02)
    
    b4 = grid.add_bus(Bus(4, "Load-1", BusType.PQ, x=100, y=300))
    b4.set_as_load(p_load=50, q_load=20)
    
    b5 = grid.add_bus(Bus(5, "Load-2", BusType.PQ, x=300, y=300))
    b5.set_as_load(p_load=60, q_load=15)
    
    # Create lines
    grid.add_line(TransmissionLine(1, b1, b2, length_km=80))
    grid.add_line(TransmissionLine(2, b2, b3, length_km=100))
    grid.add_line(TransmissionLine(3, b1, b4, length_km=60))
    grid.add_line(TransmissionLine(4, b2, b5, length_km=70))
    grid.add_line(TransmissionLine(5, b3, b5, length_km=90))
    grid.add_line(TransmissionLine(6, b4, b5, length_km=50))
    
    return grid
