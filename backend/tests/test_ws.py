import asyncio
import base64
import json
import cv2
import websockets

async def test():
    async with websockets.connect("ws://localhost:8000/ws/live") as ws:
        # Read one frame from your webcam
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()

        # Encode to base64 JPEG
        _, buffer = cv2.imencode(".jpg", frame)
        b64 = base64.b64encode(buffer).decode("utf-8")

        # Send frame
        await ws.send(json.dumps({
            "type": "frame",
            "data": b64,
            "timestamp": 1000.0
        }))

        # Get response
        response = await ws.recv()
        print(json.loads(response))

asyncio.run(test())
