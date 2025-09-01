import asyncio
import random
from app.core.socket_manager import SocketManager

class TelemetryService:
    """
    Simulates and broadcasts telemetry data.
    """

    def __init__(self, socket_manager: SocketManager):
        self.socket_manager = socket_manager
        self.is_running = False

    async def run(self):
        """
        Starts broadcasting telemetry data periodically.
        """
        self.is_running = True
        while self.is_running:
            telemetry_data = {
                "cpu_usage": random.uniform(10, 90),
                "memory_load": random.uniform(20, 80),
                "network_status": random.choice(["stable", "unstable", "down"]),
                "devices_online": random.randint(100, 1000),
            }
            
            await self.socket_manager.broadcast(
                {"type": "telemetry", "payload": telemetry_data}
            )
            await asyncio.sleep(5)  # Broadcast every 5 seconds

    def stop(self):
        """
        Stops the telemetry broadcast.
        """
        self.is_running = False
