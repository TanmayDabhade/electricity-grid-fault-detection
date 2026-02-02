"""
Electricity Grid Fault Detection Simulator
==========================================

A real-time interactive simulator for 220kV Indian regional power grid
with fault injection and detection capabilities.

Usage:
    python main.py

Controls:
    - Select fault type (SLG, LL, DLG, LLL, Open Circuit)
    - Select location (bus or line)
    - Click "Inject Fault" to simulate a fault
    - Click "Run Detection" to run detection algorithms
    - Click "Clear All" to reset

Author: Power Systems Simulation Team
"""

import sys
import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.animation import FuncAnimation

# Import our modules
from grid import create_demo_grid, Grid
from power import PowerFlow
from faults import FaultSimulator, FaultType
from detection import ImpedanceBasedDetector, GraphBasedDetector
from visualization import GridCanvas, Dashboard
from visualization.animations import CombinedAnimator
from config import ANIMATION_INTERVAL


class ElectricityGridSimulator:
    """
    Main application class for the grid fault simulator.
    """
    
    def __init__(self):
        # Create the grid
        self.grid = create_demo_grid()
        
        # Initialize components
        self.power_flow = PowerFlow(self.grid)
        self.fault_simulator = FaultSimulator(self.grid)
        self.impedance_detector = ImpedanceBasedDetector(self.grid)
        self.graph_detector = GraphBasedDetector(self.grid)
        
        # UI components
        self.root = None
        self.canvas = None
        self.dashboard = None
        self.animator = None
        self.animation = None
        
        # State
        self.current_fault = None
        
    def run(self):
        """Start the application."""
        # Run initial power flow
        print("Running initial power flow...")
        if self.power_flow.solve():
            print(f"Power flow converged in {self.power_flow.iterations} iterations")
        else:
            print("Warning: Power flow did not converge")
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("⚡ 220kV Grid Fault Detection Simulator - India Regional Grid")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1a1a2e')
        
        # Create layout
        self._create_layout()
        
        # Set up dashboard callbacks
        self._setup_callbacks()
        
        # Start animation
        self._start_animation()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Start main loop
        print("Starting simulator...")
        self.root.mainloop()
        
    def _create_layout(self):
        """Create the main application layout."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel: Grid visualization
        viz_frame = ttk.Frame(main_frame)
        viz_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create matplotlib figure
        self.fig, self.ax = plt.subplots(figsize=(10, 8))
        self.fig.patch.set_facecolor('#1a1a2e')
        
        # Create grid canvas
        self.grid_canvas = GridCanvas(self.grid)
        self.grid_canvas.setup(self.ax)
        self.grid_canvas.draw_grid()
        
        # Embed in Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Right panel: Dashboard
        dashboard_frame = ttk.Frame(main_frame, width=300)
        dashboard_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        dashboard_frame.pack_propagate(False)
        
        self.dashboard = Dashboard(dashboard_frame, self.grid)
        
        # Set up animator
        self.animator = CombinedAnimator(self.grid, self.ax)
        self.animator.setup()
        
    def _setup_callbacks(self):
        """Set up dashboard callbacks."""
        self.dashboard.on_inject_fault = self._handle_inject_fault
        self.dashboard.on_run_detection = self._handle_run_detection
        self.dashboard.on_clear_faults = self._handle_clear_faults
        self.dashboard.on_random_fault = self._handle_random_fault
        
    def _start_animation(self):
        """Start the animation loop."""
        def animate(frame):
            artists = self.animator.update(frame)
            return artists
        
        self.animation = FuncAnimation(
            self.fig,
            animate,
            interval=ANIMATION_INTERVAL,
            blit=True,
            cache_frame_data=False
        )
        
    def _handle_inject_fault(self, location_type: str, element_id: int, 
                             fault_type: FaultType, position: float, 
                             resistance: float):
        """Handle fault injection from dashboard."""
        # Clear any existing faults first
        self._handle_clear_faults()
        
        status_msg = f"Injecting {fault_type.value.upper()} fault...\n"
        
        if location_type == 'line':
            fault = self.fault_simulator.inject_line_fault(
                element_id, fault_type, position, resistance
            )
            if fault:
                line = self.grid.get_line(element_id)
                status_msg += f"Location: Line {element_id}\n"
                status_msg += f"  {line.from_bus.name} → {line.to_bus.name}\n"
                status_msg += f"  Position: {position:.0%} from start\n"
                
                # Add fault marker
                fx, fy = line.get_fault_position_xy()
                self.grid_canvas.draw_fault_marker(fx, fy, fault_type.value)
                self.animator.add_fault_at(fx, fy)
        else:
            fault = self.fault_simulator.inject_bus_fault(
                element_id, fault_type, resistance
            )
            if fault:
                bus = self.grid.get_bus(element_id)
                status_msg += f"Location: Bus {element_id} ({bus.name})\n"
                
                # Add fault marker
                self.grid_canvas.draw_fault_marker(bus.x, bus.y, fault_type.value)
                self.animator.add_fault_at(bus.x, bus.y)
        
        self.current_fault = fault
        
        if fault:
            # Get fault currents
            currents = self.fault_simulator.get_fault_current(fault)
            if currents:
                ia, ib, ic = currents
                status_msg += f"\nFault Currents:\n"
                status_msg += f"  Ia = {ia:.1f} A\n"
                status_msg += f"  Ib = {ib:.1f} A\n"
                status_msg += f"  Ic = {ic:.1f} A\n"
            
            status_msg += f"\n✓ Fault injected successfully"
        else:
            status_msg += "\n✗ Failed to inject fault"
        
        self.dashboard.update_status(status_msg)
        self._refresh_display()
        
    def _handle_run_detection(self):
        """Handle detection algorithm execution."""
        if not self.current_fault or not self.current_fault.is_active:
            self.dashboard.update_status("No active fault to detect.\nInject a fault first.")
            return
        
        status_msg = "Running detection algorithms...\n"
        status_msg += "=" * 30 + "\n\n"
        
        # Run impedance-based detection
        status_msg += "【 Impedance-Based Detection 】\n"
        imp_result = self.impedance_detector.detect_fault(self.current_fault)
        
        if imp_result.detected:
            status_msg += f"✓ DETECTED\n"
            status_msg += f"  {imp_result.message}\n"
            status_msg += f"  Confidence: {imp_result.confidence:.0%}\n"
            
            # Show detection accuracy for line faults
            if self.current_fault.is_line_fault and imp_result.estimated_position:
                actual = self.current_fault.position
                estimated = imp_result.estimated_position
                error = abs(actual - estimated) * 100
                status_msg += f"  Actual position: {actual:.1%}\n"
                status_msg += f"  Estimated: {estimated:.1%}\n"
                status_msg += f"  Error: {error:.1f}%\n"
        else:
            status_msg += f"✗ Not detected\n"
            status_msg += f"  {imp_result.message}\n"
        
        status_msg += "\n"
        
        # Run graph-based detection
        status_msg += "【 Graph-Based Detection 】\n"
        graph_result = self.graph_detector.detect_fault(self.current_fault)
        
        if graph_result.detected:
            status_msg += f"✓ DETECTED\n"
            status_msg += f"  {graph_result.message}\n"
            
            if graph_result.fault_sections:
                section = graph_result.fault_sections[0]
                status_msg += f"  Probability: {section.probability:.0%}\n"
                
            # Draw detection marker
            if graph_result.faulted_line_id:
                line = self.grid.get_line(graph_result.faulted_line_id)
                if line and graph_result.estimated_position:
                    pos = graph_result.estimated_position
                    dx = line.from_bus.x + pos * (line.to_bus.x - line.from_bus.x)
                    dy = line.from_bus.y + pos * (line.to_bus.y - line.from_bus.y)
                    self.grid_canvas.draw_detection_marker(dx, dy, "DETECTED")
        else:
            status_msg += f"✗ Not detected\n"
            status_msg += f"  {graph_result.message}\n"
        
        self.dashboard.update_status(status_msg)
        self._refresh_display()
        
    def _handle_clear_faults(self):
        """Handle clearing all faults."""
        self.fault_simulator.clear_all_faults()
        self.impedance_detector.reset()
        self.graph_detector.reset()
        self.current_fault = None
        
        # Clear visual markers
        self.grid_canvas.clear_fault_markers()
        self.animator.fault_animator.clear()
        
        # Re-run power flow
        self.power_flow.solve()
        
        self.dashboard.update_status("All faults cleared.\nSystem restored to normal.")
        self._refresh_display()
        
    def _handle_random_fault(self):
        """Handle random fault injection."""
        self._handle_clear_faults()
        
        fault = self.fault_simulator.inject_random_fault()
        self.current_fault = fault
        
        if fault:
            status_msg = f"Random fault generated!\n\n"
            status_msg += f"Type: {fault.fault_type.display_name}\n"
            
            if fault.is_line_fault:
                line = self.grid.get_line(fault.element_id)
                status_msg += f"Location: Line {fault.element_id}\n"
                status_msg += f"  {line.from_bus.name} → {line.to_bus.name}\n"
                status_msg += f"  Position: {fault.position:.0%}\n"
                
                fx, fy = line.get_fault_position_xy()
                self.grid_canvas.draw_fault_marker(fx, fy, fault.fault_type.value)
                self.animator.add_fault_at(fx, fy)
            else:
                bus = self.grid.get_bus(fault.element_id)
                status_msg += f"Location: Bus {fault.element_id} ({bus.name})\n"
                
                self.grid_canvas.draw_fault_marker(bus.x, bus.y, fault.fault_type.value)
                self.animator.add_fault_at(bus.x, bus.y)
            
            status_msg += f"Resistance: {fault.resistance:.1f} Ω\n"
            status_msg += f"\n✓ Click 'Run Detection' to test algorithms"
            
            self.dashboard.update_status(status_msg)
        else:
            self.dashboard.update_status("Failed to generate random fault")
        
        self._refresh_display()
        
    def _refresh_display(self):
        """Refresh the grid display."""
        self.grid_canvas.draw_grid()
        self.canvas.draw_idle()
        
    def _on_close(self):
        """Handle window close."""
        if self.animation:
            self.animation.event_source.stop()
        plt.close(self.fig)
        self.root.destroy()


def main():
    """Main entry point."""
    print("=" * 50)
    print("  220kV Grid Fault Detection Simulator")
    print("  India Regional Power Grid")
    print("=" * 50)
    print()
    
    app = ElectricityGridSimulator()
    app.run()


if __name__ == "__main__":
    main()
