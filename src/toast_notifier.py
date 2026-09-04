#!/usr/bin/env python3
"""
Toast Box implementation using Rich for terminal notifications.
Displays a panel when text is selected and copies content to ./src/heybro.py
"""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
import pyperclip
import os
import sys

class ToastNotifier:
    def __init__(self, output_file=None):
        self.console = Console()
        self.output_file = output_file
        if self.output_file:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
    
    async def show_toast(self, message, duration=3):
        """Display a toast notification for specified duration"""
        panel = Panel(
            Text(message, style="bold white"),
            title="📝 Copied to Clipboard",
            border_style="bright_blue",
            expand=False
        )
        
        with Live(panel, refresh_per_second=4, console=self.console) as live:
            # Update panel style to show progression
            for i in range(duration * 4):
                progress = "█" * (i // 2) + "░" * (duration * 2 - i // 2)
                panel = Panel(
                    Text(message, style="bold white"),
                    title="📝 Copied to Clipboard",
                    subtitle=f"[{progress}]",
                    border_style="bright_green" if i < duration*2 else "bright_blue",
                    expand=False
                )
                live.update(panel)
                await asyncio.sleep(0.25)
    
    def copy_to_file(self, content):
        """Copy content to the specified output file"""
        if not self.output_file:
            return False
        try:
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(content + '\n')
            return True
        except Exception as e:
            print(f"Error writing to file: {e}")
            return False
    
    def process_selection(self, selected_text):
        """Process selected text: copy to clipboard and file, then show toast"""
        try:
            # Copy to clipboard
            pyperclip.copy(selected_text)
            
            # Append to file if specified
            if self.output_file and self.copy_to_file(selected_text):
                # Show toast notification
                asyncio.run(self.show_toast(f"Copied {len(selected_text)} characters"))
                return True
            elif not self.output_file:
                # Just clipboard copy
                asyncio.run(self.show_toast(f"Copied {len(selected_text)} characters"))
                return True
            else:
                asyncio.run(self.show_toast("Failed to save to file!", duration=2))
                return False
        except Exception as e:
            print(f"Error processing selection: {e}")
            asyncio.run(self.show_toast("Error occurred!", duration=2))
            return False

def main():
    notifier = ToastNotifier()
    
    # If text provided as argument, use it
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        notifier.process_selection(text)
        return
    
    # Otherwise read from stdin
    if not sys.stdin.isatty():
        selected_text = sys.stdin.read().strip()
        if selected_text:
            notifier.process_selection(selected_text)
        else:
            asyncio.run(notifier.show_toast("No text selected", duration=1))
    else:
        # Demo mode
        demo_text = "Hello, this is a demo of the toast notification system!"
        notifier.process_selection(demo_text)

if __name__ == "__main__":
    main()
