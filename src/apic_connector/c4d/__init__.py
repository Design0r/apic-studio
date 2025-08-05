from .core import router as core_router
from .hdris import router as hdri_router
from .materials import router as material_router
from .models import router as models_router

__all__ = [
    "core_router",
    "hdri_router",
    "material_router",
    "models_router",
]
