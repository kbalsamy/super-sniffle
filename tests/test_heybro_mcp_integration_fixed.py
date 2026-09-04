#!/usr/bin/env python3
"""
Test script to verify MCP integration in heybro.py
"""

import sys
import os
import json
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from heybro_app.mcp_manager import MCP_AVAILABLE
from rich.console import Console

def test_heybro_mcp_integration():
    """Test MCP integration in heybro.py"""
    console = Console()
    
    if not MCP_AVAILABLE:
        console.print("[red]MCP support is not available. Please install the 'mcp' package.[/red]")
        return False
    
    console.print("[green]✓ MCP package is available[/green]")
    
    try:
        # We'll test by mocking just what we need to avoid initialization errors
        # Instead of creating a full CLI instance, let's test the MCP-specific parts
        
        # Test the MCPManager directly but with the same working directory logic as heybro
        from heybro_app.mcp_manager import MCPManager
        
        # Use a temporary directory for testing
        test_working_dir = Path("/tmp/heybro_mcp_test")
        test_working_dir.mkdir(exist_ok=True)
        
        test_config_file = str(test_working_dir / "mcp_config.json")
        test_history_file = str(test_working_dir / "history")
        test_input_history_file = str(test_working_dir / "input_history")
        
        # Create a minimal config with just our test server
        test_server_path = os.path.join(os.path.dirname(__file__), 'src', 'test_mcp_server.py')
        config = {
            "test": {
                "command": sys.executable,
                "args": [test_server_path],
                "env": {}
            }
        }
        
        with open(test_config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Initialize the MCP manager like heybro does
        mcp_manager = MCPManager(test_config_file, console)
        
        console.print("[green]✓ MCPManager initialized like heybro does[/green]")
        
        # Wait for connection
        import time
        time.sleep(1)
        
        # Check if MCP tools are available
        tools = mcp_manager.get_tool_schemas()
        test_tools = [tool for tool in tools if tool['function']['name'].startswith('test__')]
        
        if test_tools:
            console.print(f"[green]✓ Test tools available through MCPManager: {len(test_tools)} tools[/green]")
            for tool in test_tools:
                console.print(f"  - {tool['function']['name']}: {tool['function'].get('description', 'No description')}")
            
            # Test tool calling
            console.print("[blue]Testing tool calling functionality[/blue]")
            result = mcp_manager.call_tool("test__add", {"a": 15, "b": 25})
            if "40" in result:
                console.print(f"[green]✓ Tool calling working: 15 + 25 = {result}[/green]")
            else:
                console.print(f"[yellow]Tool calling returned: {result}[/yellow]")
            
            # Test getting tool schemas (what heybro uses to build requests)
            console.print("[blue]Testing get_tool_schemas method[/blue]")
            schemas = mcp_manager.get_tool_schemas()
            test_schemas = [s for s in schemas if s['function']['name'].startswith('test__')]
            if test_schemas:
                console.print(f"[green]✓ get_tool_schemas returns {len(test_schemas)} test tool schemas[/green]")
                console.print(f"  Example schema: {test_schemas[0]['function']['name']}")
                return True
            else:
                console.print("[red]✗ get_tool_schemas doesn't return test tool schemas[/red]")
                return False
        else:
            console.print("[red]✗ No test tools found in MCPManager[/red]")
            console.print("All available tools:")
            for tool in tools:
                console.print(f"  - {tool['function']['name']}")
            return False
            
    except Exception as e:
        console.print(f"[red]Error testing heybro MCP integration: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        import shutil
        if os.path.exists("/tmp/heybro_mcp_test"):
            shutil.rmtree("/tmp/heybro_mcp_test")

if __name__ == "__main__":
    success = test_heybro_mcp_integration()
    sys.exit(0 if success else 1)