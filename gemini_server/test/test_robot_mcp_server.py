import pytest
import asyncio
import os
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

server_path = os.path.abspath("gemini_server/robot_mcp_server.py")
transport = StdioTransport(command = "python", args = [server_path])

config = { "mcpServers":
    { "robot_mcp_server":
        {"command": "python",
         "args": ["-Xfrozen_modules=off", server_path]
         } }
    }

async def test_turn_robot_camera():
    client = Client(config)
    async with client:
        resp = await client.call_tool("turn_robot_camera", {"amount_to_turn": 30, "current_angle": 0, "direction": "clockwise"})
    assert "current_angle" in resp
    assert "action"in resp
    assert "status"in resp


async def test_detect_object_missing_label():
    client = Client(config)
    async with client:
        resp = await client.call_tool("detect_object", {"label": None})
    assert "status"in resp
    assert "error" in resp["status"]

# Note: A real image test would require a valid PNG and a running Unity/YOLO backend.
# Here we just check the error path for missing/invalid image.

async def test_detect_object_invalid():
    client = Client(config)
    async with client:
        resp = await client.call_tool("detect_object", {"label": "dog"})
    # Should return error or object not found
    assert "status" in resp
    assert "error" in resp["status"]

