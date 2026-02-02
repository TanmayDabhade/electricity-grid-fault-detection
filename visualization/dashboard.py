"""
Dashboard with control panel and status display.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from faults.types import FaultType


class Dashboard:
    """
    Control panel and status dashboard for the simulator.
    
    Provides:
    - Fault type selector
    - Fault location selector (bus or line)
    - Injection and detection buttons
    - Status display panel
    """
    
    def __init__(self, parent: tk.Frame, grid):
        self.grid = grid
        self.parent = parent
        
        # Callbacks
        self.on_inject_fault: Optional[Callable] = None
        self.on_run_detection: Optional[Callable] = None
        self.on_clear_faults: Optional[Callable] = None
        self.on_random_fault: Optional[Callable] = None
        
        # Variables
        self.fault_type_var = tk.StringVar(value='SLG')
        self.location_type_var = tk.StringVar(value='line')
        self.element_var = tk.StringVar()
        self.position_var = tk.DoubleVar(value=0.5)
        self.resistance_var = tk.DoubleVar(value=0.0)
        
        # Build UI
        self._build_ui()
        
    def _build_ui(self):
        """Build the dashboard UI."""
        # Configure style
        style = ttk.Style()
        style.configure('Dashboard.TFrame', background='#1a1a2e')
        style.configure('Dashboard.TLabel', background='#1a1a2e', foreground='white')
        style.configure('Dashboard.TButton', padding=5)
        style.configure('Status.TLabel', background='#16213e', foreground='#2ecc71', 
                        font=('Courier', 10))
        
        # Main container
        self.frame = ttk.Frame(self.parent, style='Dashboard.TFrame', padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(
            self.frame, 
            text="⚡ Fault Simulator Control",
            style='Dashboard.TLabel',
            font=('Helvetica', 12, 'bold')
        )
        title.pack(pady=(0, 10))
        
        # Fault Type Section
        self._build_fault_type_section()
        
        # Location Section
        self._build_location_section()
        
        # Parameters Section
        self._build_parameters_section()
        
        # Action Buttons
        self._build_action_buttons()
        
        # Status Panel
        self._build_status_panel()
        
    def _build_fault_type_section(self):
        """Build fault type selector."""
        frame = ttk.LabelFrame(
            self.frame, 
            text="Fault Type",
            padding=5
        )
        frame.pack(fill=tk.X, pady=5)
        
        fault_types = [
            ('SLG', 'Single Line-Ground'),
            ('LL', 'Line-Line'),
            ('DLG', 'Double Line-Ground'),
            ('LLL', 'Three-Phase'),
            ('OPEN', 'Open Circuit')
        ]
        
        for i, (value, text) in enumerate(fault_types):
            rb = ttk.Radiobutton(
                frame,
                text=text,
                value=value,
                variable=self.fault_type_var
            )
            rb.pack(anchor=tk.W)
            
    def _build_location_section(self):
        """Build location selector."""
        frame = ttk.LabelFrame(
            self.frame,
            text="Fault Location",
            padding=5
        )
        frame.pack(fill=tk.X, pady=5)
        
        # Location type (bus or line)
        type_frame = ttk.Frame(frame)
        type_frame.pack(fill=tk.X)
        
        ttk.Radiobutton(
            type_frame,
            text="Line",
            value="line",
            variable=self.location_type_var,
            command=self._update_element_list
        ).pack(side=tk.LEFT)
        
        ttk.Radiobutton(
            type_frame,
            text="Bus",
            value="bus",
            variable=self.location_type_var,
            command=self._update_element_list
        ).pack(side=tk.LEFT)
        
        # Position slider (for line faults)
        self.position_frame = ttk.Frame(frame)
        self.position_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(self.position_frame, text="Position:").pack(side=tk.LEFT)
        self.position_slider = ttk.Scale(
            self.position_frame,
            from_=0.0,
            to=1.0,
            variable=self.position_var,
            orient=tk.HORIZONTAL
        )
        self.position_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.position_label = ttk.Label(self.position_frame, text="50%")
        self.position_label.pack(side=tk.LEFT)

        # Element selector
        ttk.Label(frame, text="Select:").pack(anchor=tk.W, pady=(5, 0))
        self.element_combo = ttk.Combobox(
            frame,
            textvariable=self.element_var,
            state='readonly',
            width=30
        )
        self.element_combo.pack(fill=tk.X)
        self._update_element_list()
        
        # Update position label
        self.position_var.trace_add('write', self._update_position_label)
        
    def _build_parameters_section(self):
        """Build fault parameters section."""
        frame = ttk.LabelFrame(
            self.frame,
            text="Parameters",
            padding=5
        )
        frame.pack(fill=tk.X, pady=5)
        
        # Fault resistance
        res_frame = ttk.Frame(frame)
        res_frame.pack(fill=tk.X)
        
        ttk.Label(res_frame, text="Fault Resistance (Ω):").pack(side=tk.LEFT)
        res_spinbox = ttk.Spinbox(
            res_frame,
            from_=0,
            to=50,
            textvariable=self.resistance_var,
            width=8
        )
        res_spinbox.pack(side=tk.RIGHT)
        
    def _build_action_buttons(self):
        """Build action buttons."""
        frame = ttk.Frame(self.frame)
        frame.pack(fill=tk.X, pady=10)
        
        # Configure button styles
        style = ttk.Style()
        style.configure('Inject.TButton', foreground='red')
        style.configure('Detect.TButton', foreground='green')
        
        # Inject Fault Button
        self.inject_btn = ttk.Button(
            frame,
            text="⚡ INJECT FAULT",
            command=self._on_inject_click,
            style='Inject.TButton'
        )
        self.inject_btn.pack(fill=tk.X, pady=2)
        
        # Random Fault Button
        self.random_btn = ttk.Button(
            frame,
            text="🎲 Random Fault",
            command=self._on_random_click
        )
        self.random_btn.pack(fill=tk.X, pady=2)
        
        # Detect Fault Button
        self.detect_btn = ttk.Button(
            frame,
            text="🔍 RUN DETECTION",
            command=self._on_detect_click,
            style='Detect.TButton'
        )
        self.detect_btn.pack(fill=tk.X, pady=2)
        
        # Clear Button
        self.clear_btn = ttk.Button(
            frame,
            text="✖ Clear All Faults",
            command=self._on_clear_click
        )
        self.clear_btn.pack(fill=tk.X, pady=2)
        
    def _build_status_panel(self):
        """Build status display panel."""
        frame = ttk.LabelFrame(
            self.frame,
            text="Status",
            padding=5
        )
        frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.status_text = tk.Text(
            frame,
            height=10,
            width=35,
            bg='#16213e',
            fg='#2ecc71',
            font=('Courier', 9),
            state=tk.DISABLED
        )
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, command=self.status_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.status_text.config(yscrollcommand=scrollbar.set)
        
        # Initial status
        self.update_status("System ready.\nNo active faults.")
        
    def _update_element_list(self):
        """Update the element combobox based on location type."""
        if self.location_type_var.get() == 'line':
            elements = [
                f"Line {l.id}: {l.from_bus.name} - {l.to_bus.name}"
                for l in self.grid.lines.values()
            ]
            self.position_frame.pack(fill=tk.X, pady=(5, 0))
        else:
            elements = [
                f"Bus {b.id}: {b.name}"
                for b in self.grid.buses.values()
            ]
            self.position_frame.pack_forget()
            
        self.element_combo['values'] = elements
        if elements:
            self.element_combo.set(elements[0])
            
    def _update_position_label(self, *args):
        """Update position percentage label."""
        self.position_label.config(text=f"{self.position_var.get():.0%}")
        
    def _on_inject_click(self):
        """Handle inject button click."""
        if self.on_inject_fault:
            # Parse selected element
            element_str = self.element_var.get()
            try:
                element_id = int(element_str.split(':')[0].split()[-1])
            except (ValueError, IndexError):
                self.update_status("Error: Invalid element selection")
                return
                
            fault_type_map = {
                'SLG': FaultType.SLG,
                'LL': FaultType.LL,
                'DLG': FaultType.DLG,
                'LLL': FaultType.LLL,
                'OPEN': FaultType.OPEN
            }
            
            self.on_inject_fault(
                location_type=self.location_type_var.get(),
                element_id=element_id,
                fault_type=fault_type_map[self.fault_type_var.get()],
                position=self.position_var.get(),
                resistance=self.resistance_var.get()
            )
            
    def _on_detect_click(self):
        """Handle detect button click."""
        if self.on_run_detection:
            self.on_run_detection()
            
    def _on_clear_click(self):
        """Handle clear button click."""
        if self.on_clear_faults:
            self.on_clear_faults()
            
    def _on_random_click(self):
        """Handle random fault button click."""
        if self.on_random_fault:
            self.on_random_fault()
            
    def update_status(self, message: str):
        """Update status display."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, message)
        self.status_text.config(state=tk.DISABLED)
        self.status_text.see(tk.END)
        
    def append_status(self, message: str):
        """Append message to status display."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"\n{message}")
        self.status_text.config(state=tk.DISABLED)
        self.status_text.see(tk.END)
