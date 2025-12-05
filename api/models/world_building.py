"""
Pydantic models for world-building API requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class WorldCreate(BaseModel):
    """Request model for creating a new world"""
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    created_by_user: Optional[str] = None


class WorldResponse(BaseModel):
    """Response model for world data"""
    id: int
    name: str
    description: Optional[str]
    created_by_user: Optional[str]


class LocationCreate(BaseModel):
    """Model for creating a location extracted from description"""
    name: str = Field(min_length=1, max_length=255)
    description: str
    location_type: Optional[str] = None
    relative_position: Optional[str] = None  # "north of Millbrook, 2 days travel"
    elevation_meters: Optional[int] = None


class FactCreate(BaseModel):
    """Model for creating a fact extracted from description"""
    content: str = Field(min_length=1, max_length=2000)
    fact_category: str  # observed, historical, current_state, deduction, measurement
    what_type: Optional[str] = None  # demographic, structural, political, social, geographic, etc.
    location_name: Optional[str] = None  # Reference location by name, will be resolved to location_id


class WorldBuildingExtraction(BaseModel):
    """Structured output from LLM when parsing world descriptions"""
    locations: List[LocationCreate]
    facts: List[FactCreate]


class WorldBuildingRequest(BaseModel):
    """Request model for world-building describe endpoint"""
    world_id: int
    description: str = Field(min_length=1, max_length=5000)


class WorldBuildingResponse(BaseModel):
    """Response model for world-building describe endpoint"""
    world_id: int
    locations_created: int
    facts_created: int
    locations: List[dict]
    facts: List[dict]
