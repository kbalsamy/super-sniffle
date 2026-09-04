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

from heybro import UniversalAICli
from heybro_app.mcp_manager import MCP_AVAILABLE
from heybro_app.providers import PROVIDERS
from rich.console import Console

def test_heybro_mcp_integration():
    """Test MCP integration in heybro.py"""
    console = Console()
    
    if not MCP_AVAILABLE:
        console.print("[red]MCP support is not available. Please install the 'mcp' package.[/red]")
        return False
    
    console.print("[green]✓ MCP package is available[/green]")
    
    try:
        # Create a test instance with custom provider (no API key needed for this test)
        test_config_file = "/tmp/test_heybro_mcp_config.json"
        test_history_file = "/tmp/test_heybro_history"
        test_input_history_file = "/tmp/test_heybro_input_history"
        
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
        
        # Mock the provider config for testing
        mock_provider = type('MockProvider', (), {
            'model': 'test-model',
            'api_key_env': 'TEST_API_KEY',
            'supports_reasoning': False,
            'reasoning_param': None,
            'is_bedrock': False,
            'system_role': 'system'
        })
        PROVIDERS['test'] = mock_provider
        
        # Initialize the CLI
        cli = UniversalAICli(
            provider='test',
            working_dir=Path('/tmp')
        )
        
        console.print("[green]✓ UniversalAICli initialized successfully[/green]")
        
        # Override the MCP config file to use our test config
        cli.mcp_config_file = test_config_file
        # Re-initialize MCP manager with our test config
        cli.mcp = cli.__class__.__dict__['mcp'].__get__(cli, cli.__class__)
        
        # Wait for connection
        import time
        time.sleep(1)
        
        # Check if MCP tools are available
        tools = cli.mcp.get_tool_schemas()
        test_tools = [tool for tool in tools if tool['function']['name'].startswith('test__')]
        
        if test_tools:
            console.print(f"[green]✓ Test tools integrated with heybro: {len(test_tools)} tools[/green]")
            for tool in test_tools:
                console.print(f"  - {tool['function']['name']}: {tool['function'].get('description', 'No description')}")
            
            # Test the _execute_tool_call method
            console.print("[blue]Testing _execute_tool_call method[/blue]")
            result = cli._execute_tool_call("test__add", {"a": 10, "b": 32}, is_json_str=True)
            if "42" in result:
                console.print(f"[green]✓ _execute_tool_call working: {result}[/green]")
            else:
                console.print(f"[yellow]_execute_tool_call returned: {result}[/yellow]")
            
            # Test building request with tools
            console.print("[blue]Testing _build_request method with tools[/blue]")
            request = cli._build_request([{"role": "user", "content": "test"}], stream=False)
            if "tools" in request:
                console.print(f"[green]✓ Request built with {len(request['tools'])} tools[/green]")
                # Check if our test tools are included
                test_req_tools = [tool for tool in request['tools'] if tool['function']['name'].startswith('test__')]
                console.print(f"[green]✓ Request includes {len(test_req_tools)} test tools[/green]")
            else:
                console.print("[red]✗ No tools in request[/red]")
                return False
            
            return True
        else:
            console.print("[red]✗ No test tools found in heybro integration[/red]")
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
        for file in ["/tmp/test_heybro_mcp_config.json", "/tmp/test_heybro_history", "/tmp/test_heybro_input_history"]:
            if os.path.exists(file):
                os.remove(file)

if __name__ == "__main__":
    success = test_heybro_mcp_integration()
    sys.exit(0 if success else 1)