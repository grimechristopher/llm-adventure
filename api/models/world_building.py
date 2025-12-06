"""
Pydantic models for world-building API requests and responses
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


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
    gathered_so_far: Dict[str, Any]
    progress_percentage: int


class WizardFinalizeRequest(BaseModel):
    """Request to finalize world generation from wizard session"""
    session_id: int


class CoordinateAssignmentSummary(BaseModel):
    """Summary of coordinate assignment results"""
    total_locations: int
    locations_with_coordinates: int
    anchor_locations: int
    relative_locations: int


class WizardFinalizeResponse(BaseModel):
    """Response after finalizing world generation"""
    world_id: int
    locations_created: int
    facts_created: int
    myths_created: int
    coordinate_assignment: CoordinateAssignmentSummary


# ========== LLM EXTRACTION MODELS FOR WIZARD ==========

class RelativePositionParse(BaseModel):
    """Parsed relative position from natural language"""
    reference_location_name: str
    direction: str  # north, south, east, west, northeast, etc.
    distance_qualifier: str  # far, close, nearby, very far, etc.
    additional_constraints: List[str] = Field(default_factory=list)  # "near coast", "in mountains"


class WizardQuestionResponse(BaseModel):
    """LLM response for next wizard question"""
    question_text: str
    question_type: str  # world_identity, locations, magic_system, etc.
    context_hint: str  # Why asking this question


class WizardExtractionResult(BaseModel):
    """Result after extracting data from user's wizard response"""
    extracted_data: Dict[str, Any]
    is_sufficient: bool  # Enough info for this question type?
    follow_up_needed: Optional[str] = None  # Ask clarifying question?


class CompletionEvaluation(BaseModel):
    """LLM evaluation of whether wizard has enough information"""
    is_complete: bool
    missing_elements: List[str] = Field(default_factory=list)
    next_question_suggestion: Optional[str] = None
