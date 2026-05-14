import sys
sys.path.insert(0, '.')

# Apply pydantic v1 compat patch for Python 3.14
import pydantic_v1_compat

from pydantic.v1 import BaseModel
from typing import Optional

class TestModel(BaseModel):
    x: Optional[int] = None
    y: str = "hello"
    z: int = 42

print(f"Fields: {list(TestModel.__fields__.keys())}")
t = TestModel(x=5, y="world", z=10)
print(f"Instance: x={t.x}, y={t.y}, z={t.z}")
