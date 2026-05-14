from typing import Optional
import sys

class TestMeta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        print(f"Class: {name}")
        print(f"  __annotations__ in namespace: {'__annotations__' in namespace}")
        annots = namespace.get('__annotations__', {})
        print(f"  annotations type: {type(annots)}")
        print(f"  annotations: {annots}")
        return super().__new__(mcs, name, bases, namespace, **kwargs)

class Test(metaclass=TestMeta):
    x: Optional[int] = None
    y: str = "hello"
    z: int = 42

print(f"\nPython: {sys.version_info}")
print(f"Test.__annotations__: {Test.__annotations__}")
