
import asyncio
import websockets
import json

EVENT_ID = 1  # Replace with your actual event ID


async def test_live_updates():
    url = f"ws://127.0.0.1:8000/ws/events/{EVENT_ID}"

    async with websockets.connect(url) as websocket:
        print("Connected to SmartEvent live updates!")

        while True:
            message = await websocket.recv()
            print("Live update:", json.loads(message))


asyncio.run(test_live_updates())
