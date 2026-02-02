"""
Animation handlers for real-time visualization.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from config import COLORS, ANIMATION_INTERVAL


class FlowAnimator:
    """
    Animates power flow along transmission lines.
    
    Uses moving particles to show the direction and magnitude of power flow.
    """
    
    def __init__(self, grid, ax):
        self.grid = grid
        self.ax = ax
        self.particles: Dict[int, List] = {}  # line_id -> list of particle plots
        self.particle_positions: Dict[int, List[float]] = {}  # line_id -> positions
        
    def setup_particles(self, particles_per_line: int = 3):
        """
        Initialize flow particles on all lines.
        
        Args:
            particles_per_line: Number of particles per line
        """
        for line in self.grid.lines.values():
            if not line.is_closed:
                continue
                
            # Initialize particle positions (evenly spaced)
            positions = [i / (particles_per_line + 1) for i in range(1, particles_per_line + 1)]
            self.particle_positions[line.id] = positions
            
            # Create particle plots
            self.particles[line.id] = []
            for pos in positions:
                x = line.from_bus.x + pos * (line.to_bus.x - line.from_bus.x)
                y = line.from_bus.y + pos * (line.to_bus.y - line.from_bus.y)
                
                particle, = self.ax.plot(
                    x, y,
                    marker='o',
                    markersize=4,
                    color=COLORS['flow_particle'],
                    zorder=8
                )
                self.particles[line.id].append(particle)
    
    def update(self, frame: int) -> List:
        """
        Update particle positions for animation frame.
        
        Args:
            frame: Current animation frame number
            
        Returns:
            List of updated artists for blitting
        """
        artists = []
        speed = 0.02  # Base speed
        
        for line in self.grid.lines.values():
            if line.id not in self.particles:
                continue
                
            if not line.is_closed or line.is_faulted:
                # Hide particles on open/faulted lines
                for particle in self.particles[line.id]:
                    particle.set_visible(False)
                continue
            
            # Update positions
            positions = self.particle_positions[line.id]
            flow_direction = 1 if line.power_flow_mw >= 0 else -1
            flow_speed = speed * (1 + min(abs(line.power_flow_mw) / 100, 2))
            
            new_positions = []
            for i, pos in enumerate(positions):
                new_pos = pos + flow_direction * flow_speed
                
                # Wrap around
                if new_pos > 1:
                    new_pos = 0
                elif new_pos < 0:
                    new_pos = 1
                    
                new_positions.append(new_pos)
                
                # Update particle plot
                x = line.from_bus.x + new_pos * (line.to_bus.x - line.from_bus.x)
                y = line.from_bus.y + new_pos * (line.to_bus.y - line.from_bus.y)
                
                particle = self.particles[line.id][i]
                particle.set_data([x], [y])
                particle.set_visible(True)
                
                # Adjust brightness based on loading
                alpha = 0.5 + min(line.loading_percent / 200, 0.5)
                particle.set_alpha(alpha)
                
                artists.append(particle)
            
            self.particle_positions[line.id] = new_positions
        
        return artists
    
    def clear(self):
        """Remove all particles."""
        for particles in self.particles.values():
            for p in particles:
                p.remove()
        self.particles.clear()
        self.particle_positions.clear()


class FaultAnimator:
    """
    Animates fault indicators with pulsing effects.
    """
    
    def __init__(self, ax):
        self.ax = ax
        self.fault_circles = []
        self.pulse_phase = 0
        
    def add_fault_animation(self, x: float, y: float):
        """
        Add animated fault indicator at location.
        
        Args:
            x, y: Fault coordinates
        """
        from matplotlib.patches import Circle
        
        # Create multiple concentric circles for pulse effect
        for radius in [20, 35, 50]:
            circle = Circle(
                (x, y),
                radius=radius,
                facecolor='none',
                edgecolor=COLORS['bus_fault'],
                linewidth=2,
                alpha=0.8,
                zorder=15
            )
            self.ax.add_patch(circle)
            self.fault_circles.append({
                'patch': circle,
                'base_radius': radius,
                'x': x,
                'y': y
            })
    
    def update(self, frame: int) -> List:
        """
        Update fault animation for frame.
        
        Args:
            frame: Current animation frame
            
        Returns:
            List of updated artists
        """
        artists = []
        self.pulse_phase = (frame % 30) / 30  # 0 to 1 cycle
        
        for circle_data in self.fault_circles:
            patch = circle_data['patch']
            base_radius = circle_data['base_radius']
            
            # Pulsing radius
            pulse_amount = 5 * np.sin(2 * np.pi * self.pulse_phase)
            new_radius = base_radius + pulse_amount
            
            # Pulsing alpha
            alpha = 0.3 + 0.5 * (1 - self.pulse_phase)
            
            patch.set_radius(new_radius)
            patch.set_alpha(alpha)
            artists.append(patch)
        
        return artists
    
    def clear(self):
        """Remove all fault animations."""
        for circle_data in self.fault_circles:
            circle_data['patch'].remove()
        self.fault_circles.clear()
        self.pulse_phase = 0


class CombinedAnimator:
    """
    Combines flow and fault animations into a single animation loop.
    """
    
    def __init__(self, grid, ax):
        self.grid = grid
        self.ax = ax
        self.flow_animator = FlowAnimator(grid, ax)
        self.fault_animator = FaultAnimator(ax)
        self.animation = None
        
    def setup(self):
        """Set up all animations."""
        self.flow_animator.setup_particles()
        
    def add_fault_at(self, x: float, y: float):
        """Add fault animation at location."""
        self.fault_animator.add_fault_animation(x, y)
        
    def update(self, frame: int):
        """Update all animations."""
        artists = []
        artists.extend(self.flow_animator.update(frame))
        artists.extend(self.fault_animator.update(frame))
        return artists
    
    def start(self, fig, interval: int = ANIMATION_INTERVAL):
        """Start the animation loop."""
        from matplotlib.animation import FuncAnimation
        
        self.animation = FuncAnimation(
            fig,
            self.update,
            interval=interval,
            blit=True,
            cache_frame_data=False
        )
        return self.animation
    
    def stop(self):
        """Stop the animation."""
        if self.animation:
            self.animation.event_source.stop()
            
    def clear(self):
        """Clear all animations."""
        self.flow_animator.clear()
        self.fault_animator.clear()
