#!/usr/bin/env python3
"""
Test script to verify MCP functionality in heybro.py
"""

import sys
import os
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from heybro_app.mcp_manager import MCP_AVAILABLE, MCPManager
from rich.console import Console

def test_mcp_basic_functionality():
    """Test basic MCP functionality"""
    console = Console()
    
    if not MCP_AVAILABLE:
        console.print("[red]MCP support is not available. Please install the 'mcp' package.[/red]")
        return False
    
    console.print("[green]✓ MCP package is available[/green]")
    
    # Create a temporary config file for testing
    test_config_file = "/tmp/test_mcp_config.json"
    
    # Initialize MCP Manager
    try:
        mcp_manager = MCPManager(test_config_file, console)
        console.print("[green]✓ MCPManager initialized successfully[/green]")
        
        # Test adding our test server
        test_server_path = os.path.join(os.path.dirname(__file__), 'src', 'test_mcp_server.py')
        if os.path.exists(test_server_path):
            console.print(f"[blue]Adding test server from {test_server_path}[/blue]")
            mcp_manager.add_server("test", sys.executable, [test_server_path], {})
            
            # Check if tools are available
            tools = mcp_manager.get_tool_schemas()
            if tools:
                console.print(f"[green]✓ MCP tools detected: {len(tools)} tools available[/green]")
                for tool in tools:
                    console.print(f"  - {tool['function']['name']}: {tool['function'].get('description', 'No description')}")
                
                # Try calling a simple tool
                if tools:
                    tool_name = tools[0]['function']['name']
                    console.print(f"[blue]Testing tool call: {tool_name}[/blue]")
                    result = mcp_manager.call_tool(tool_name, {"a": 10, "b": 5})
                    console.print(f"[green]✓ Tool call result: {result}[/green]")
                    return True
            else:
                console.print("[yellow]No MCP tools detected[/yellow]")
                return False
        else:
            console.print(f"[red]Test server not found at {test_server_path}[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]Error testing MCP functionality: {e}[/red]")
        return False
    finally:
        # Clean up
        if os.path.exists(test_config_file):
            os.remove(test_config_file)

if __name__ == "__main__":
    success = test_mcp_basic_functionality()
    sys.exit(0 if success else 1)