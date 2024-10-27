from pydantic import BaseModel, Field


class Role_Rec(BaseModel):
    id: str = Field(description="id of the recommended role")
    name: str = Field(description="name of the recommended role")
    confidence: float = Field(description="confidence level of this recommendation")
