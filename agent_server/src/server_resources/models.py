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

class SelfGrade(BaseModel):
    grading_person_index: int = Field(
        ...,
        description="Index of the person assigning the grade"
    )
    grade: int = Field(
        ..., 
        description="The grade assigned by the user"
    )
    description: str = Field(
        ..., 
        description="Justification for the assigned grade"
    )
class TeammateGrade(BaseModel):
    grading_person_index: int = Field(
        ...,
        description="Index of the person assigning the grade"
    )
    graded_person_index: int = Field(
        ...,
        description="Index of the teammate being graded"
    )
    grade: int = Field(
        ..., 
        description="The grade assigned to the teammate"
    )
    description: str = Field(
        ..., 
        description="Justification for the assigned grade"
    )
class ProjectGrade(BaseModel):
    grading_person_index: int = Field(
        ...,
        description="Index of the person assigning the grade"
    )
    project_id: int = Field(
        ...,
        description="ID of the project being graded"
    )
    grade: int = Field(
        ..., 
        description="The grade assigned to the project"
    )
    description: str = Field(
        ..., 
        description="Justification for the assigned grade"
    )