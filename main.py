"""
Kivy WebView wrapper for Vulnerable E-Commerce Lab Flask application
"""

import os
import sys
import threading
import time
import socket
from functools import partial

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.webview import WebView
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock
from kivy.logger import Logger

# Flask imports
from threading import Thread

# Set window properties
Window.size = (540, 960)


class VulnerableEcommerceApp(App):
    """Main application class"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.webview = None
        self.server_thread = None
        self.server_ready = False
        self.port = 5000
        
    def find_available_port(self, start_port=5000):
        """Find an available port"""
        port = start_port
        while True:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('127.0.0.1', port))
                sock.close()
                return port
            except OSError:
                port += 1
                if port > start_port + 100:
                    raise Exception("Could not find available port")
    
    def start_flask_server(self):
        """Start Flask server in background thread"""
        try:
            self.port = self.find_available_port()
            Logger.info('VulnEcommerce', f'Starting Flask server on port {self.port}')
            
            # Import and run Flask app
            from app import app
            
            # Run Flask in debug mode with threading
            app.run(
                host='127.0.0.1',
                port=self.port,
                debug=False,
                threaded=True,
                use_reloader=False
            )
            
        except Exception as e:
            Logger.error('VulnEcommerce', f'Failed to start Flask server: {e}')
            self.show_error_popup(f"Could not start server: {str(e)}")
    
    def build(self):
        """Build the Kivy app"""
        Logger.info('VulnEcommerce', 'Building app...')
        
        # Create main layout
        layout = BoxLayout(orientation='vertical')
        
        # Start Flask server in background thread
        self.server_thread = Thread(target=self.start_flask_server, daemon=True)
        self.server_thread.start()
        
        # Wait for server to start, then load WebView
        Clock.schedule_once(self.load_webview, 2)
        
        # Create WebView
        self.webview = WebView()
        layout.add_widget(self.webview)
        
        return layout
    
    def load_webview(self, dt):
        """Load the Flask app in WebView"""
        try:
            url = f'http://127.0.0.1:{self.port}/'
            Logger.info('VulnEcommerce', f'Loading URL: {url}')
            
            if self.webview:
                self.webview.url = url
            else:
                Logger.error('VulnEcommerce', 'WebView not initialized')
                
        except Exception as e:
            Logger.error('VulnEcommerce', f'Failed to load WebView: {e}')
            self.show_error_popup(f"Could not load app: {str(e)}")
    
    def show_error_popup(self, message):
        """Show an error popup"""
        content = GridLayout(cols=1, padding=10, spacing=10)
        content.add_widget(Label(text=message))
        
        close_btn = Button(text='Close', size_hint_y=0.3)
        content.add_widget(close_btn)
        
        popup = Popup(
            title='Error',
            content=content,
            size_hint=(0.9, 0.6)
        )
        
        close_btn.bind(on_press=popup.dismiss)
        popup.open()
    
    def on_stop(self):
        """Handle app closing"""
        Logger.info('VulnEcommerce', 'Shutting down...')
        return True


if __name__ == '__main__':
    app = VulnerableEcommerceApp()
    app.run()
