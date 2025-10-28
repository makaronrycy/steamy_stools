from pydantic import BaseModel,Field

class Message(BaseModel):
    content: str = Field(
        ..., 
        description="The content of the message"
    )

class NameEntity(BaseModel):
    first_name: str = Field(
        ..., 
        description="First name of the person"
    )
    last_name: str = Field(
        ...,
        description="Last name of the person"
    )

class GetProjectGradesRequest(BaseModel):
    project_id: str = Field(
        ...,
        description="ID projektu, dla którego pobierane są oceny"
    )

class SetSelfGradeRequest(BaseModel):
    grading_person_index: str = Field(
        ...,
        description="Indeks osoby wystawiającej sobie ocenę"
    )
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
    