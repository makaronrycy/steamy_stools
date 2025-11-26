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
    index: str = Field(..., description="Index ocenianego członka")

class IsLeaderRequest(BaseModel):
    index: str = Field(..., description="Index studenta")

class GetProjectMembersRequest(BaseModel):
    project_id: str = Field(..., description="ID projektu")

class GetUserInfoRequest(BaseModel):
    index: str = Field(..., description="Index studenta")

class HasGradedAllMembersRequest(BaseModel):
    index: str = Field(..., description="Index oceniającego")

class GetUngradedMembersRequest(BaseModel):
    index: str = Field(..., description="Index oceniającego")

class HasGradedAllProjectsRequest(BaseModel):
    index: str = Field(..., description="Index oceniającego")

class GetUngradedProjectsRequest(BaseModel):
    index: str = Field(..., description="Index oceniającego")

class GetStudentCompletionStatusRequest(BaseModel):
    index: str = Field(..., description="Index studenta")

class IdentifyTeammateByNameRequest(BaseModel):
    name: str = Field(..., description="Imię do dopasowania (case-insensitive)")
    surname: str = Field(..., description="Nazwisko do dopasowania (case-insensitive)")


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
    project_id: str = Field(..., description="ID projektu")
    grade: float = Field(..., ge=2.0, le=5.0, description="Ocena 2.0–5.0")
    description: str = Field(..., description="Uzasadnienie oceny")
