"""
Pydantic models for MCP tool request/response validation.

This module defines all request models used by MCP tools for:
- GET operations: Retrieving grades, user info, completion status
- SET operations: Saving grades, assessments, and open answers

All models use Pydantic Field for validation and description.
"""

from pydantic import BaseModel,Field
from typing import Optional


class Message(BaseModel):
    """
    Generic message model for simple text content.
    
    Attributes:
        content (str): The message content.
    """
    content: str = Field(
        ..., 
        description="The content of the message"
    )


class NameEntity(BaseModel):
    """
    Model representing a person's name.
    
    Attributes:
        first_name (str): First name of the person.
        last_name (str): Last name of the person.
    """
    first_name: str = Field(
        ..., 
        description="First name of the person"
    )
    last_name: str = Field(
        ...,
        description="Last name of the person"
    )

#     _   __ ______ ____   __ __   _                          __       __     
#    / | / // ____// __ \ / // /  (_)  ____ ___   ____   ____/ /___   / /_____
#   /  |/ // __/  / / / // // /_ / /  / __ `__ \ / __ \ / __  // _ \ / // ___/
#  / /|  // /___ / /_/ //__  __// /  / / / / / // /_/ // /_/ //  __// /(__  ) 
# /_/ |_//_____/ \____/   /_/__/ /  /_/ /_/ /_/ \____/ \__,_/ \___//_//____/  
#                           /___/                        
                     
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------GET METHOD MODELS---------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class GetProjectGradesRequest(BaseModel):
    project_id: str = Field(
        ...,
        description="ID projektu, dla którego pobierane są oceny"
    )
class GetMemberGradesRequest(BaseModel):
    name: str = Field(..., description="Imię ocenianego członka")

class IsLeaderRequest(BaseModel):
    name: str = Field(..., description="Imię studenta")

class GetProjectMembersRequest(BaseModel):
    project_id: str = Field(..., description="ID projektu")

class GetUserInfoRequest(BaseModel):
    name: str = Field(..., description="Imię studenta")

class HasGradedAllMembersRequest(BaseModel):
    name: str = Field(..., description="Imię oceniającego")

class GetUngradedMembersRequest(BaseModel):
    name: str = Field(..., description="Imię oceniającego")

class HasGradedAllProjectsRequest(BaseModel):
    name: str = Field(..., description="Imię oceniającego")

class GetUngradedProjectsRequest(BaseModel):
    name: str = Field(..., description="Imię oceniającego")

class GetStudentCompletionStatusRequest(BaseModel):
    name: str = Field(..., description="Imię studenta")

class IdentifyTeammateByNameRequest(BaseModel):
    name: str = Field(..., description="Imię (case-insensitive)")
    surname: Optional[str] = Field(None, description="Nazwisko (opcjonalne, case-insensitive)")


#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
#----------------SET METHOD MODELS---------------------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

class SetSelfGradeRequest(BaseModel):
    grade: float = Field(
        ...,
        description="Ocena w skali 2.0-5.0",
        ge=2.0,
        le=5.0
    )
    description: str = Field(
        ...,
        description="Uzasadnienie samooceny"
    )
class SetTeammateGradeRequest(BaseModel):
    graded_person_index: str = Field(..., description="Index ocenianego")
    grade: float = Field(..., ge=2.0, le=5.0, description="Ocena 2.0–5.0")
    description: str = Field(..., description="Uzasadnienie oceny")

class SetLeaderGradeRequest(BaseModel):
    project_id: str = Field(..., description="ID projektu")
    grade: float = Field(..., ge=2.0, le=5.0, description="Ocena 2.0–5.0")
    description: str = Field(..., description="Uzasadnienie oceny")

class SetProjectGradeRequest(BaseModel):
    project_id: str = Field(..., description="ID projektu")
    grade: float = Field(..., ge=2.0, le=5.0, description="Ocena 2.0–5.0")
    description: str = Field(..., description="Uzasadnienie oceny")

class SetProjectObjectivesGradeRequest(BaseModel):
    grade: float = Field(..., ge=2.0, le=5.0, description="Ocena 2.0–5.0")
    description: str = Field(..., description="Uzasadnienie oceny")


class SetOpenAnswerRequest(BaseModel):
    answer: str = Field(
        ..., 
        min_length=20,
        description="Odpowiedź użytkownika z uzasadnieniem (min. 20 znaków)"
    )
