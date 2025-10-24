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
    