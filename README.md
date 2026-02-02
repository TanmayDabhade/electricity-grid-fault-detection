# 220kV Electricity Grid Fault Detection Simulator

A Python-based real-time simulator for Indian regional power grid with fault detection and localization capabilities.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **220kV Regional Grid Simulation**: 12-bus demonstration grid based on Northern India topology
- **All Fault Types**: Single Line-to-Ground (SLG), Line-to-Line (LL), Double Line-to-Ground (DLG), Three-Phase (LLL), Open Circuit
- **Detection Algorithms**:
  - Impedance-based detection (distance relay simulation)
  - Graph-based fault localization (network topology analysis)
- **Real-time Visualization**: Animated power flow, fault markers, and detection results
- **Interactive GUI**: Tkinter-based control panel for fault injection and testing

## Installation

1. Clone or navigate to the project directory:
```bash
cd /Users/tanmay/Desktop/electricity-fault
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

## Usage

Run the simulator:
```bash
python3 main.py
```

### Controls

1. **Select Fault Type**: Choose from SLG, LL, DLG, LLL, or Open Circuit
2. **Select Location**: Choose bus or line, and specific element
3. **Set Position**: For line faults, set the fault position (0-100% along line)
4. **Inject Fault**: Click to simulate the fault
5. **Run Detection**: Execute both detection algorithms
6. **Clear All**: Reset the system to normal state

## Project Structure

```
electricity-fault/
├── main.py                 # Main application entry point
├── config.py               # System configuration and constants
├── requirements.txt        # Python dependencies
├── grid/                   # Grid network module
│   ├── bus.py              # Bus (substation) class
│   ├── line.py             # Transmission line class
│   ├── network.py          # Grid network class
│   └── demo_grid.py        # Demo 220kV Indian grid
├── power/                  # Power system calculations
│   ├── flow.py             # Newton-Raphson power flow
│   └── impedance.py        # Impedance calculations
├── faults/                 # Fault simulation module
│   ├── types.py            # Fault type definitions
│   ├── models.py           # Symmetrical components models
│   └── simulator.py        # Fault injection engine
├── detection/              # Fault detection algorithms
│   ├── impedance_based.py  # Distance relay simulation
│   └── graph_based.py      # Network topology analysis
└── visualization/          # GUI and visualization
    ├── grid_canvas.py      # Grid drawing
    ├── animations.py       # Real-time animations
    └── dashboard.py        # Control panel
```

## Detection Algorithms

### Impedance-Based Detection
Simulates distance relay operation using apparent impedance measurement:
- Zone 1: 80% reach (instantaneous)
- Zone 2: 120% reach (time-delayed)
- Zone 3: 150% reach (backup)

### Graph-Based Detection
Uses network topology analysis:
- Voltage deviation analysis
- Current flow anomaly detection
- Two-terminal fault location method
- BFS-based affected section identification

## Demo Grid

The simulator includes a 12-bus 220kV regional grid representing a simplified Northern India topology:

| Bus | Name | Type | Description |
|-----|------|------|-------------|
| 1 | Delhi | Slack | Main hub, reference bus |
| 2 | Gurugram | Load | Industrial load center |
| 3 | Noida | Generator | Thermal generation |
| 4 | Ghaziabad | Load | Urban load |
| 5 | Jaipur | Generator | State capital, generation |
| 6 | Agra | Load | Historical city load |
| 7 | Meerut | Load | Industrial area |
| 8 | Ajmer | Load | Regional load |
| 9 | Mathura | Load | Refinery load |
| 10 | Saharanpur | Load | Agricultural load |
| 11 | Udaipur | Generator | Hydro generation |
| 12 | Lucknow | Generator | State capital, generation |

## Future Enhancements

- [ ] Machine Learning-based fault classification
- [ ] Protection coordination simulation
- [ ] Historical fault data recording
- [ ] More detailed grid models
- [ ] SCADA-like interface

## License

MIT License
# electricity-grid-fault-detection
