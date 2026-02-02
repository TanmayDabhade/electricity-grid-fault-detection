"""
Grid visualization canvas using Matplotlib.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle
from matplotlib.collections import LineCollection
from matplotlib.animation import FuncAnimation
from typing import Optional, Dict, Tuple
from config import COLORS, BusType


class GridCanvas:
    """
    Main grid visualization using Matplotlib.
    
    Displays the power grid with:
    - Buses as colored circles
    - Transmission lines as edges
    - Power flow indicators
    - Fault locations
    """
    
    def __init__(self, grid, figsize=(12, 8)):
        self.grid = grid
        self.figsize = figsize
        
        # Matplotlib elements
        self.fig = None
        self.ax = None
        
        # Drawing elements
        self.bus_patches: Dict[int, Circle] = {}
        self.bus_labels: Dict[int, plt.Text] = {}
        self.line_plots: Dict[int, plt.Line2D] = {}
        self.fault_markers: list = []
        self.flow_particles: list = []
        
        # Animation
        self.animation = None
        self.frame_count = 0
        
    def setup(self, ax=None):
        """
        Set up the visualization canvas.
        
        Args:
            ax: Optional matplotlib axes to draw on
        """
        if ax is None:
            self.fig, self.ax = plt.subplots(figsize=self.figsize)
        else:
            self.ax = ax
            self.fig = ax.figure
            
        self.ax.set_facecolor(COLORS['background'])
        self.ax.set_aspect('equal')
        
        # Set bounds
        x_min, y_min, x_max, y_max = self.grid.get_bounds()
        self.ax.set_xlim(x_min, x_max)
        self.ax.set_ylim(y_max, y_min)  # Flip y for conventional layout
        
        # Remove axes
        self.ax.set_xticks([])
        self.ax.set_yticks([])
        
        # Title
        self.ax.set_title(self.grid.name, color='white', fontsize=14, fontweight='bold')
        
    def draw_grid(self):
        """Draw the complete grid (buses and lines)."""
        self.clear_drawings()
        self.draw_lines()
        self.draw_buses()
        
    def draw_buses(self):
        """Draw all buses as circles."""
        for bus in self.grid.buses.values():
            # Determine color based on bus type
            if bus.is_faulted:
                color = COLORS['bus_fault']
            elif bus.bus_type == BusType.SLACK:
                color = COLORS['bus_slack']
            elif bus.bus_type == BusType.PV:
                color = COLORS['bus_generation']
            else:
                color = COLORS['bus_load']
            
            # Draw bus circle
            radius = 15 if bus.bus_type != BusType.PQ else 12
            circle = Circle(
                (bus.x, bus.y), 
                radius=radius,
                facecolor=color,
                edgecolor='white',
                linewidth=2,
                zorder=10
            )
            self.ax.add_patch(circle)
            self.bus_patches[bus.id] = circle
            
            # Add bus label
            label = self.ax.text(
                bus.x, bus.y + radius + 10,
                bus.name,
                ha='center', va='bottom',
                color='white',
                fontsize=8,
                fontweight='bold',
                zorder=11
            )
            self.bus_labels[bus.id] = label
            
            # Add voltage annotation
            voltage_text = f'{bus.voltage_pu:.3f} pu'
            self.ax.text(
                bus.x, bus.y - radius - 8,
                voltage_text,
                ha='center', va='top',
                color='#95a5a6',
                fontsize=7,
                zorder=11
            )
    
    def draw_lines(self):
        """Draw all transmission lines."""
        for line in self.grid.lines.values():
            # Determine line style and color
            if line.is_faulted:
                color = COLORS['line_fault']
                linewidth = 3
                linestyle = '-'
            elif not line.is_closed:
                color = COLORS['line_open']
                linewidth = 1
                linestyle = '--'
            elif line.loading_percent > 80:
                color = COLORS['line_overload']
                linewidth = 2.5
                linestyle = '-'
            else:
                color = COLORS['line_normal']
                linewidth = 2
                linestyle = '-'
            
            # Draw line
            x = [line.from_bus.x, line.to_bus.x]
            y = [line.from_bus.y, line.to_bus.y]
            
            line_plot, = self.ax.plot(
                x, y,
                color=color,
                linewidth=linewidth,
                linestyle=linestyle,
                zorder=5
            )
            self.line_plots[line.id] = line_plot
            
            # Add line ID label (at midpoint)
            mid_x = (line.from_bus.x + line.to_bus.x) / 2
            mid_y = (line.from_bus.y + line.to_bus.y) / 2
            self.ax.text(
                mid_x + 5, mid_y + 5,
                f'L{line.id}',
                color='#7f8c8d',
                fontsize=6,
                zorder=6
            )
    
    def draw_fault_marker(self, x: float, y: float, fault_type: str):
        """
        Draw a fault indicator at the specified location.
        
        Args:
            x, y: Coordinates of the fault
            fault_type: Type of fault for label
        """
        # Pulsing fault marker
        marker = self.ax.plot(
            x, y, 
            marker='X',
            markersize=20,
            color=COLORS['bus_fault'],
            markeredgecolor='white',
            markeredgewidth=2,
            zorder=20
        )[0]
        self.fault_markers.append(marker)
        
        # Fault label
        label = self.ax.text(
            x + 15, y,
            f'FAULT\n({fault_type.upper()})',
            color=COLORS['bus_fault'],
            fontsize=8,
            fontweight='bold',
            zorder=21
        )
        self.fault_markers.append(label)
        
        # Add ripple effect circles
        for i, r in enumerate([25, 40, 55]):
            ripple = Circle(
                (x, y),
                radius=r,
                facecolor='none',
                edgecolor=COLORS['bus_fault'],
                linewidth=1,
                alpha=0.5 - i * 0.15,
                zorder=15
            )
            self.ax.add_patch(ripple)
            self.fault_markers.append(ripple)
    
    def draw_detection_marker(self, x: float, y: float, label: str = "DETECTED"):
        """Draw a detection indicator."""
        marker = self.ax.plot(
            x, y,
            marker='o',
            markersize=25,
            markerfacecolor='none',
            markeredgecolor='#2ecc71',
            markeredgewidth=3,
            zorder=19
        )[0]
        self.fault_markers.append(marker)
        
        text = self.ax.text(
            x, y - 30,
            label,
            ha='center',
            color='#2ecc71',
            fontsize=9,
            fontweight='bold',
            zorder=21
        )
        self.fault_markers.append(text)
    
    def update_bus(self, bus_id: int):
        """Update a single bus visualization."""
        bus = self.grid.get_bus(bus_id)
        if bus is None or bus_id not in self.bus_patches:
            return
            
        circle = self.bus_patches[bus_id]
        
        # Update color
        if bus.is_faulted:
            circle.set_facecolor(COLORS['bus_fault'])
        elif bus.bus_type == BusType.SLACK:
            circle.set_facecolor(COLORS['bus_slack'])
        elif bus.bus_type == BusType.PV:
            circle.set_facecolor(COLORS['bus_generation'])
        else:
            circle.set_facecolor(COLORS['bus_load'])
    
    def update_line(self, line_id: int):
        """Update a single line visualization."""
        line = self.grid.get_line(line_id)
        if line is None or line_id not in self.line_plots:
            return
            
        line_plot = self.line_plots[line_id]
        
        # Update color
        if line.is_faulted:
            line_plot.set_color(COLORS['line_fault'])
            line_plot.set_linewidth(3)
        elif not line.is_closed:
            line_plot.set_color(COLORS['line_open'])
            line_plot.set_linestyle('--')
        elif line.loading_percent > 80:
            line_plot.set_color(COLORS['line_overload'])
        else:
            line_plot.set_color(COLORS['line_normal'])
    
    def clear_fault_markers(self):
        """Remove all fault markers."""
        for marker in self.fault_markers:
            if hasattr(marker, 'remove'):
                marker.remove()
        self.fault_markers.clear()
    
    def clear_drawings(self):
        """Clear all drawings."""
        for patch in self.bus_patches.values():
            patch.remove()
        self.bus_patches.clear()
        
        for label in self.bus_labels.values():
            label.remove()
        self.bus_labels.clear()
        
        for line in self.line_plots.values():
            line.remove()
        self.line_plots.clear()
        
        self.clear_fault_markers()
    
    def refresh(self):
        """Redraw the entire grid."""
        self.draw_grid()
        if self.fig:
            self.fig.canvas.draw_idle()
    
    def get_figure(self):
        """Get the matplotlib figure."""
        return self.fig
