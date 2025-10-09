from pydantic import BaseModel,Field

class Message(BaseModel):
    content: str = Field(
        ..., 
        description="The content of the message"
    )