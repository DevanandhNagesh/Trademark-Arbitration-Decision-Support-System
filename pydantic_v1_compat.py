"""Monkey-patch pydantic v1 ModelMetaclass to work with Python 3.14+ (PEP 649)."""
import sys

if sys.version_info >= (3, 14):
    import warnings
    warnings.filterwarnings('ignore', message='Core Pydantic V1')
    
    import annotationlib
    from pydantic.v1 import main as pydantic_main
    
    _original_new = pydantic_main.ModelMetaclass.__new__
    
    def _patched_new(mcs, name, bases, namespace, **kwargs):
        # On Python 3.14+, __annotations__ is not in namespace during __new__.
        # We need to evaluate annotations via __annotate__ or type hints.
        if '__annotations__' not in namespace:
            # Try to get annotations from __annotate__ function
            annotate_fn = namespace.get('__annotate__')
            if annotate_fn is not None:
                try:
                    namespace['__annotations__'] = annotate_fn(annotationlib.Format.FORWARDREF)
                except Exception:
                    namespace['__annotations__'] = {}
            else:
                # Build annotations by creating a temporary class first
                try:
                    temp_cls = super(pydantic_main.ModelMetaclass, mcs).__new__(
                        mcs, name, bases, namespace, **kwargs
                    )
                    if hasattr(temp_cls, '__annotations__'):
                        # Only include annotations defined in this class (not inherited)
                        own_annotations = {}
                        for k, v in temp_cls.__annotations__.items():
                            if k in namespace or k not in getattr(bases[0], '__annotations__', {}) if bases else True:
                                own_annotations[k] = v
                        namespace['__annotations__'] = own_annotations
                except Exception:
                    namespace['__annotations__'] = {}
        
        return _original_new(mcs, name, bases, namespace, **kwargs)
    
    pydantic_main.ModelMetaclass.__new__ = _patched_new
