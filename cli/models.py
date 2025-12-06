"""
Pydantic models mirroring API contracts
"""
from pydantic import BaseModel, Field
from typing import Optional, List


# Request models
class WorldCreate(BaseModel):
    """Request model for creating a new world"""

    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    created_by_user: Optional[str] = None


class WorldBuildingRequest(BaseModel):
    """Request model for world-building describe endpoint"""

    world_id: int
    description: str = Field(min_length=1, max_length=5000)



# Response models
class WorldResponse(BaseModel):
    """Response model for world data"""

    id: int
    name: str
    description: Optional[str]
    created_by_user: Optional[str]


class LocationData(BaseModel):
    """Location data model"""

    id: int
    name: str
    description: Optional[str]
    location_type: Optional[str]
    relative_position: Optional[str]
    elevation_meters: Optional[int]


class FactData(BaseModel):
    """Fact data model"""

    id: int
    content: str
    fact_category: str
    what_type: Optional[str]
    location_id: Optional[int]


class WorldBuildingResponse(BaseModel):
    """Response model for world-building describe endpoint"""

    world_id: int
    locations_created: int
    facts_created: int
    locations: List[LocationData]
    facts: List[FactData]


class LocationsResponse(BaseModel):
    """Response model for locations list"""

    world_id: int
    count: int
    locations: List[LocationData]


class FactsResponse(BaseModel):
    """Response model for facts list"""

    world_id: int
    count: int
    facts: List[FactData]


# ========== WIZARD MODELS ==========

class WizardStartRequest(BaseModel):
    """Request to start a wizard session"""
    world_id: int


class WizardStartResponse(BaseModel):
    """Response when starting a wizard session"""
    session_id: int
    first_question: str
    stage: str


class WizardResponseRequest(BaseModel):
    """Request to respond to a wizard question"""
    session_id: int
    response: str = Field(min_length=1, max_length=10000)


class WizardResponseResponse(BaseModel):
    """Response after answering a wizard question"""
    next_question: Optional[str]
    is_complete: bool
    current_stage: str
    gathered_so_far: dict
    progress_percentage: int


class WizardFinalizeRequest(BaseModel):
    """Request to finalize world generation from wizard session"""
    session_id: int


class WizardFinalizeResponse(BaseModel):
    """Response after finalizing wizard session"""
    world_id: int
    locations_created: int
    facts_created: int
    message: str
