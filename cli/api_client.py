"""
HTTP client for all API interactions
"""
import httpx
from typing import AsyncIterator
from models import (
    WorldCreate,
    WorldResponse,
    WorldBuildingRequest,
    WorldBuildingResponse,
    LocationsResponse,
    FactsResponse,
)
from config import Config


class APIClient:
    """Client for interacting with the LLM Adventure API"""

    def __init__(self, config: Config):
        self.base_url = config.api_base_url.rstrip("/")
        self.timeout = config.api_timeout

    async def create_world(self, world_data: WorldCreate) -> WorldResponse:
        """Create a new world"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/world-building/worlds", json=world_data.model_dump()
            )
            response.raise_for_status()
            return WorldResponse(**response.json())

    async def describe_world(
        self, request: WorldBuildingRequest
    ) -> WorldBuildingResponse:
        """Add world description (LLM extraction)"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/world-building/describe", json=request.model_dump()
            )
            response.raise_for_status()
            return WorldBuildingResponse(**response.json())

    async def get_locations(self, world_id: int) -> LocationsResponse:
        """Get all locations for a world"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/world-building/worlds/{world_id}/locations"
            )
            response.raise_for_status()
            return LocationsResponse(**response.json())

    async def get_facts(self, world_id: int) -> FactsResponse:
        """Get all facts for a world"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/world-building/worlds/{world_id}/facts"
            )
            response.raise_for_status()
            return FactsResponse(**response.json())


