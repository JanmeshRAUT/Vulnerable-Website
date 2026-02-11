"""
Standalone Executable Launcher for Vulnerable E-Commerce Lab
This script is used by PyInstaller to create a standalone .exe file
Features:
- Simple GUI launcher with status display
- Auto-shutdown when browser is closed
- Manual start/stop controls
"""
import os
import sys
import webbrowser
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, scrolledtext
import socket
from datetime import datetime

# Global variables
flask_thread = None
server_running = False
last_connection_time = None
shutdown_timer = 30  # seconds of inactivity before auto-shutdown
monitoring_active = False

def get_base_path():
    """Get the base path for resources (works for both dev and PyInstaller)"""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return sys._MEIPASS
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))

def check_port_in_use(port=5000):
    """Check if there are active connections to the Flask server"""
    try:
        # This is a simple check - in production you'd use more sophisticated monitoring
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

class VulnerableLabGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Vulnerable E-Commerce Lab")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Set icon (optional - will use default if no icon)
        try:
            self.root.iconbitmap(default='icon.ico')
        except:
            pass
        
        self.setup_ui()
        self.flask_app = None
        self.server_thread = None
        self.monitor_thread = None
        
    def setup_ui(self):
        """Setup the GUI interface with modern, polished design"""
        # Configure root window
        self.root.configure(bg="#f5f6fa")
        # Increased height to ensure everything fits comfortably
        self.root.geometry("600x600")
        
        # ===== LAYOUT STRATEGY =====
        # We pack from the outside in to ensure critical controls are always visible
        
        # 1. CONTROL BUTTONS (Packed at BOTTOM to ensure visibility)
        button_container = tk.Frame(self.root, bg="#f5f6fa")
        button_container.pack(side=tk.BOTTOM, fill=tk.X, padx=25, pady=25)
        
        button_frame = tk.Frame(button_container, bg="#f5f6fa")
        button_frame.pack(fill=tk.X)
        
        # Start button with modern styling
        self.start_button = tk.Button(
            button_frame,
            text="▶  Start Server",
            font=("Segoe UI", 12, "bold"),
            bg="#27ae60",
            fg="white",
            activebackground="#229954",
            activeforeground="white",
            relief=tk.FLAT,
            padx=30,
            pady=15,
            cursor="hand2",
            command=self.start_server,
            borderwidth=0
        )
        self.start_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 8))
        
        # Stop button with modern styling
        self.stop_button = tk.Button(
            button_frame,
            text="■  Stop Server",
            font=("Segoe UI", 12, "bold"),
            bg="#95a5a6",
            fg="white",
            activebackground="#7f8c8d",
            activeforeground="white",
            relief=tk.FLAT,
            padx=30,
            pady=15,
            cursor="hand2",
            command=self.stop_server,
            state=tk.DISABLED,
            borderwidth=0
        )
        self.stop_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(8, 0))
        
        # 2. HEADER SECTION (Packed at TOP)
        header_frame = tk.Frame(self.root, bg="#34495e", height=100)
        header_frame.pack(side=tk.TOP, fill=tk.X)
        header_frame.pack_propagate(False)
        
        # Icon and title container
        title_container = tk.Frame(header_frame, bg="#34495e")
        title_container.pack(expand=True)
        
        title_label = tk.Label(
            title_container, 
            text="🔓 Vulnerable E-Commerce Lab",
            font=("Segoe UI", 22, "bold"),
            bg="#34495e",
            fg="#ffffff"
        )
        title_label.pack(pady=(15, 5))
        
        subtitle_label = tk.Label(
            title_container,
            text="Security Training Platform",
            font=("Segoe UI", 10),
            bg="#34495e",
            fg="#bdc3c7"
        )
        subtitle_label.pack()
        
        # 3. WARNING BANNER (Packed below Header)
        warning_frame = tk.Frame(self.root, bg="#e74c3c", height=45)
        warning_frame.pack(side=tk.TOP, fill=tk.X)
        warning_frame.pack_propagate(False)
        
        warning_label = tk.Label(
            warning_frame,
            text="⚠️  WARNING: Contains intentional vulnerabilities - For educational use only!",
            font=("Segoe UI", 10, "bold"),
            bg="#e74c3c",
            fg="#ffffff"
        )
        warning_label.pack(pady=12)
        
        # 4. MAIN CONTENT AREA (Fills remaining space)
        content_frame = tk.Frame(self.root, bg="#f5f6fa")
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=25, pady=25)
        
        # ===== STATUS CARD =====
        status_card = tk.Frame(content_frame, bg="#ffffff", relief=tk.FLAT, bd=0)
        status_card.pack(fill=tk.X, pady=(0, 15))
        
        # Add subtle shadow effect with border
        status_card.configure(highlightbackground="#dfe6e9", highlightthickness=1)
        
        status_inner = tk.Frame(status_card, bg="#ffffff")
        status_inner.pack(fill=tk.X, padx=20, pady=15)
        
        # Status header
        status_header = tk.Label(
            status_inner,
            text="Server Status",
            font=("Segoe UI", 13, "bold"),
            bg="#ffffff",
            fg="#2c3e50"
        )
        status_header.pack(anchor=tk.W, pady=(0, 10))
        
        # Status indicator with better styling
        status_row = tk.Frame(status_inner, bg="#ffffff")
        status_row.pack(fill=tk.X, pady=5)
        
        self.status_indicator = tk.Label(
            status_row,
            text="● Stopped",
            font=("Segoe UI", 14, "bold"),
            bg="#ffffff",
            fg="#e74c3c"
        )
        self.status_indicator.pack(side=tk.LEFT)
        
        # URL display with copy-friendly styling
        url_row = tk.Frame(status_inner, bg="#ffffff")
        url_row.pack(fill=tk.X, pady=8)
        
        url_icon = tk.Label(
            url_row,
            text="🌐",
            font=("Segoe UI", 12),
            bg="#ffffff"
        )
        url_icon.pack(side=tk.LEFT, padx=(0, 8))
        
        self.url_label = tk.Label(
            url_row,
            text="http://127.0.0.1:5000",
            font=("Segoe UI", 11),
            bg="#ffffff",
            fg="#3498db",
            cursor="hand2"
        )
        self.url_label.pack(side=tk.LEFT)
        
        # Auto-shutdown info with icon
        auto_row = tk.Frame(status_inner, bg="#ffffff")
        auto_row.pack(fill=tk.X, pady=5)
        
        auto_icon = tk.Label(
            auto_row,
            text="⏱️",
            font=("Segoe UI", 11),
            bg="#ffffff"
        )
        auto_icon.pack(side=tk.LEFT, padx=(0, 8))
        
        self.auto_shutdown_label = tk.Label(
            auto_row,
            text="Auto-shutdown: Enabled (30s inactivity)",
            font=("Segoe UI", 10),
            bg="#ffffff",
            fg="#7f8c8d"
        )
        self.auto_shutdown_label.pack(side=tk.LEFT)
        
        # ===== ACTIVITY LOG CARD =====
        log_card = tk.Frame(content_frame, bg="#ffffff", relief=tk.FLAT, bd=0)
        log_card.pack(fill=tk.BOTH, expand=True)
        log_card.configure(highlightbackground="#dfe6e9", highlightthickness=1)
        
        log_inner = tk.Frame(log_card, bg="#ffffff")
        log_inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        
        # Log header
        log_header = tk.Label(
            log_inner,
            text="Activity Log",
            font=("Segoe UI", 13, "bold"),
            bg="#ffffff",
            fg="#2c3e50"
        )
        log_header.pack(anchor=tk.W, pady=(0, 10))
        
        # Log text area with better styling
        log_container = tk.Frame(log_inner, bg="#f8f9fa", relief=tk.FLAT)
        log_container.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_container,
            height=6,  # Reduced height slightly to share space better
            font=("Consolas", 9),
            bg="#f8f9fa",
            fg="#2c3e50",
            wrap=tk.WORD,
            relief=tk.FLAT,
            padx=10,
            pady=10,
            borderwidth=0,
            highlightthickness=0
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Add hover effects
        self._add_button_hover_effects()
        
        self.log("Application initialized. Click 'Start Server' to begin.")
    
    def _add_button_hover_effects(self):
        """Add hover effects to buttons"""
        def on_enter_start(e):
            if self.start_button['state'] != 'disabled':
                self.start_button['bg'] = '#229954'
        
        def on_leave_start(e):
            if self.start_button['state'] != 'disabled':
                self.start_button['bg'] = '#27ae60'
        
        def on_enter_stop(e):
            if self.stop_button['state'] != 'disabled':
                self.stop_button['bg'] = '#e74c3c'
        
        def on_leave_stop(e):
            if self.stop_button['state'] != 'disabled':
                self.stop_button['bg'] = '#95a5a6'
        
        self.start_button.bind('<Enter>', on_enter_start)
        self.start_button.bind('<Leave>', on_leave_start)
        self.stop_button.bind('<Enter>', on_enter_stop)
        self.stop_button.bind('<Leave>', on_leave_stop)
        
    def log(self, message):
        """Add a message to the log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def start_server(self):
        """Start the Flask server"""
        global server_running, monitoring_active, last_connection_time
        
        self.log("Starting server...")
        self.start_button.config(state=tk.DISABLED)
        
        # Update status
        self.status_indicator.config(text="● Starting...", fg="#f39c12")
        
        # Start Flask in a separate thread
        self.server_thread = threading.Thread(target=self.run_flask, daemon=True)
        self.server_thread.start()
        
        # Wait a moment for server to start
        self.root.after(2000, self.on_server_started)
        
    def on_server_started(self):
        """Called after server has started"""
        global server_running, monitoring_active, last_connection_time
        
        server_running = True
        last_connection_time = time.time()
        
        self.status_indicator.config(text="● Running", fg="#27ae60")
        self.stop_button.config(state=tk.NORMAL, bg="#e74c3c")
        self.log("Server started successfully on http://127.0.0.1:5000")
        
        # Open browser
        self.log("Opening browser...")
        webbrowser.open('http://127.0.0.1:5000')
        
        # Start monitoring for auto-shutdown
        monitoring_active = True
        self.monitor_thread = threading.Thread(target=self.monitor_connections, daemon=True)
        self.monitor_thread.start()
        self.log("Auto-shutdown monitoring enabled")
        
    def run_flask(self):
        """Run the Flask application"""
        try:
            base_path = get_base_path()
            os.chdir(base_path)
            
            from app import app, init_db
            
            # Initialize database
            init_db()
            
            # Store reference
            self.flask_app = app
            
            # Run the Flask app
            app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            self.log(f"Error starting server: {e}")
            self.root.after(0, self.on_server_error)
            
    def monitor_connections(self):
        """Monitor for browser connections and auto-shutdown if inactive"""
        global server_running, monitoring_active, last_connection_time
        
        while monitoring_active and server_running:
            time.sleep(5)  # Check every 5 seconds
            
            # Check if server is still accessible (simple check)
            if check_port_in_use():
                last_connection_time = time.time()
            
            # Check if we should auto-shutdown
            if last_connection_time:
                inactive_time = time.time() - last_connection_time
                if inactive_time > shutdown_timer:
                    self.log(f"No activity for {shutdown_timer} seconds. Auto-shutting down...")
                    self.root.after(0, self.stop_server)
                    break
                    
    def stop_server(self):
        """Stop the Flask server"""
        global server_running, monitoring_active
        
        self.log("Stopping server...")
        server_running = False
        monitoring_active = False
        
        self.status_indicator.config(text="● Stopped", fg="#e74c3c")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED, bg="#95a5a6")
        
        self.log("Server stopped successfully")
        
        # Note: Flask's built-in server doesn't have a clean shutdown method
        # In a production app, you'd use a proper WSGI server with shutdown capability
        
    def on_server_error(self):
        """Handle server startup errors"""
        self.status_indicator.config(text="● Error", fg="#e74c3c")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)

def main():
    """Main function to run the GUI application"""
    root = tk.Tk()
    app = VulnerableLabGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
