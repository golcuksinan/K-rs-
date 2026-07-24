from typing import Optional

from pydantic import BaseModel


class UniversityResponse(BaseModel):
    id: int
    name: str
    short_name: Optional[str]
    city: str

    class Config:
        from_attributes = True