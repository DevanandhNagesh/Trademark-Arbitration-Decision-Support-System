import warnings
warnings.filterwarnings('ignore')

from pydantic.v1 import BaseModel, validator
from typing import Optional

class Test(BaseModel):
    x: Optional[int] = None

print("Test1 OK:", Test.__fields__)

class Test2(BaseModel):
    @validator("y", pre=True, always=True, allow_reuse=True)
    def empty_str_to_none(cls, v):
        return v
    y: Optional[int] = None

print("Test2 OK:", Test2.__fields__)
