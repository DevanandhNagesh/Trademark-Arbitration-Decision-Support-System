from typing import Optional
import sys
import annotationlib

class TestMeta(type):
    def __new__(mcs, name, bases, namespace, **kwargs):
        print(f"Class: {name}")
        # Try annotationlib on Python 3.14
        if '__annotate__' in namespace:
            annots = namespace['__annotate__'](annotationlib.Format.FORWARDREF)
            print(f"  annotations via __annotate__: {annots}")
        else:
            print(f"  No __annotate__ in namespace")
        return super().__new__(mcs, name, bases, namespace, **kwargs)

class Test(metaclass=TestMeta):
    x: Optional[int] = None
    y: str = "hello"
