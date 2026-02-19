"""
Image upscaling service abstraction.
Supports: Real-ESRGAN (local), FAL.AI (API), Replicate (API)
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional
import httpx

LOG = logging.getLogger(__name__)


class UpscalingProvider(ABC):
    """Abstract base class for upscaling providers"""
    
    @abstractmethod
    def upscale(self, image_bytes: bytes, scale: int = 2) -> bytes:
        """Upscale image, return processed bytes"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass


class RealESRGANProvider(UpscalingProvider):
    """Local upscaling using Real-ESRGAN with singleton pattern"""

    _instance = None
    _upsampler = None
    _Image = None
    _np = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._upsampler is not None:
            return

        try:
            from PIL import Image
            import numpy as np
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet

            RealESRGANProvider._Image = Image
            RealESRGANProvider._np = np

            import os
            # Use baked-in model if available (Dockerfile downloads it to /app/models/),
            # otherwise fall back to downloading from GitHub at runtime.
            _local = '/app/models/RealESRGAN_x2plus.pth'
            _model_url = 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth'
            _model_path = _local if os.path.exists(_local) else _model_url

            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=2)
            RealESRGANProvider._upsampler = RealESRGANer(
                scale=2,
                model_path=_model_path,
                model=model,
                tile=400,
                tile_pad=10,
                pre_pad=0,
                half=False
            )
            LOG.info("Real-ESRGAN provider initialized (2x upscaling, singleton)")
        except ImportError as e:
            raise ImportError(f"Real-ESRGAN not installed: {e}")
    
    def upscale(self, image_bytes: bytes, scale: int = 2) -> bytes:
        from io import BytesIO

        LOG.info("Upscaling with Real-ESRGAN (2x)")

        img = RealESRGANProvider._Image.open(BytesIO(image_bytes)).convert('RGB')
        img_array = RealESRGANProvider._np.array(img)

        output, _ = RealESRGANProvider._upsampler.enhance(img_array, outscale=2)

        result_img = RealESRGANProvider._Image.fromarray(output)
        output_buffer = BytesIO()
        result_img.save(output_buffer, format='PNG', optimize=True)

        LOG.info(f"Real-ESRGAN upscaling complete: {img.size} → {result_img.size}")
        return output_buffer.getvalue()
    
    @property
    def name(self) -> str:
        return "realesrgan"


class FalUpscalingProvider(UpscalingProvider):
    """FAL.AI upscaling (API)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        LOG.info("FAL.AI upscaling provider initialized")
    
    def upscale(self, image_bytes: bytes, scale: int = 2) -> bytes:
        LOG.info(f"Upscaling with FAL.AI ({scale}x)")
        
        # TODO: Implement FAL.AI upscaling when needed
        # For now, return original
        LOG.warning("FAL.AI upscaling not yet implemented, returning original")
        return image_bytes
    
    @property
    def name(self) -> str:
        return "fal-upscale"


class ReplicateUpscalingProvider(UpscalingProvider):
    """Replicate upscaling (API)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        LOG.info("Replicate upscaling provider initialized")
    
    def upscale(self, image_bytes: bytes, scale: int = 2) -> bytes:
        LOG.info(f"Upscaling with Replicate ({scale}x)")
        
        # TODO: Implement Replicate upscaling when needed
        # Use: nightmareai/real-esrgan or similar
        LOG.warning("Replicate upscaling not yet implemented, returning original")
        return image_bytes
    
    @property
    def name(self) -> str:
        return "replicate-upscale"


def get_upscaling_provider(provider_name: str = "realesrgan", **kwargs) -> UpscalingProvider:
    """Factory function to get upscaling provider"""
    providers = {
        "realesrgan": RealESRGANProvider,
        "fal": FalUpscalingProvider,
        "replicate": ReplicateUpscalingProvider,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")
    
    provider_class = providers[provider_name]
    
    # Real-ESRGAN doesn't need kwargs
    if provider_name == "realesrgan":
        return provider_class()
    else:
        return provider_class(**kwargs)
