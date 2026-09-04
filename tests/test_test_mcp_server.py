#!/usr/bin/env python3
"""
Focused test script to verify the test MCP server functionality
"""

import sys
import os
import json
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from heybro_app.mcp_manager import MCP_AVAILABLE, MCPManager
from rich.console import Console

def test_test_mcp_server():
    """Test our test MCP server specifically"""
    console = Console()
    
    if not MCP_AVAILABLE:
        console.print("[red]MCP support is not available. Please install the 'mcp' package.[/red]")
        return False
    
    console.print("[green]✓ MCP package is available[/green]")
    
    # Create a temporary config file for testing
    test_config_file = "/tmp/test_mcp_config.json"
    
    # Initialize MCP Manager
    try:
        # Create a clean config with just our test server
        test_server_path = os.path.join(os.path.dirname(__file__), 'src', 'test_mcp_server.py')
        
        # Write a minimal config with just our test server
        config = {
            "test": {
                "command": sys.executable,
                "args": [test_server_path],
                "env": {}
            }
        }
        
        with open(test_config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        mcp_manager = MCPManager(test_config_file, console)
        console.print("[green]✓ MCPManager initialized with test config[/green]")
        
        # Wait a moment for connection
        import time
        time.sleep(1)
        
        # Check if our test tools are available
        test_tools = [name for name in mcp_manager.tools.keys() if name.startswith('test__')]
        if test_tools:
            console.print(f"[green]✓ Test MCP tools detected: {test_tools}[/green]")
            
            # Test the add function
            console.print("[blue]Testing add function with arguments {'a': 17, 'b': 25}[/blue]")
            result = mcp_manager.call_tool("test__add", {"a": 17, "b": 25})
            expected = "42"
            if expected in result:
                console.print(f"[green]✓ Add function working correctly: 17 + 25 = {result}[/green]")
            else:
                console.print(f"[yellow]Add function returned: {result} (expected something containing '{expected}')[/yellow]")
            
            # Test the echo function
            console.print("[blue]Testing echo function with arguments {'text': 'Hello MCP!'}[/blue]")
            result = mcp_manager.call_tool("test__echo", {"text": "Hello MCP!"})
            if "Hello MCP!" in result:
                console.print(f"[green]✓ Echo function working correctly: {result}[/green]")
            else:
                console.print(f"[yellow]Echo function returned: {result}[/yellow]")
            
            return True
        else:
            console.print("[red]No test MCP tools detected[/red]")
            console.print("Available tools:", list(mcp_manager.tools.keys()))
            return False
            
    except Exception as e:
        console.print(f"[red]Error testing MCP functionality: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        if os.path.exists(test_config_file):
            os.remove(test_config_file)

if __name__ == "__main__":
    success = test_test_mcp_server()
    sys.exit(0 if success else 1)