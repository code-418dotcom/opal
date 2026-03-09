"""
Background removal service abstraction.
Supports multiple providers: BiRefNet (local), rembg (local), remove.bg (API), Azure AI Vision
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

LOG = logging.getLogger(__name__)


class BackgroundRemovalProvider(ABC):
    """Abstract base class for background removal providers"""
    
    @abstractmethod
    def remove_background(self, image_bytes: bytes) -> bytes:
        """Remove background from image, return processed bytes"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass


class BiRefNetProvider(BackgroundRemovalProvider):
    """Local background removal using BiRefNet (MIT license).

    Produces 256-level alpha mattes with sharp edges — a significant quality
    upgrade over rembg/u2net which only produces binary masks.
    """

    def __init__(self, model_id: str = "ZhengPeng7/BiRefNet", device: str = ""):
        import torch
        from torchvision import transforms
        from transformers import AutoModelForImageSegmentation

        self._device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        LOG.info("Loading BiRefNet model %s on %s …", model_id, self._device)
        self._model = (
            AutoModelForImageSegmentation.from_pretrained(model_id, trust_remote_code=True)
            .eval()
            .to(self._device)
        )
        self._transform = transforms.Compose([
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self._torch = torch
        LOG.info("BiRefNet provider initialized (%s)", self._device)

    def remove_background(self, image_bytes: bytes) -> bytes:
        from io import BytesIO
        from PIL import Image

        LOG.info("Processing with BiRefNet (local)")

        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        orig_size = image.size

        input_tensor = self._transform(image).unsqueeze(0).to(self._device)

        with self._torch.no_grad():
            preds = self._model(input_tensor)[-1].sigmoid().cpu()

        mask = preds[0].squeeze()
        mask_img = Image.fromarray((mask.numpy() * 255).astype("uint8"), mode="L")
        mask_img = mask_img.resize(orig_size, Image.Resampling.LANCZOS)

        result = image.convert("RGBA")
        result.putalpha(mask_img)

        buf = BytesIO()
        result.save(buf, format="PNG")
        LOG.info("BiRefNet background removal successful (%d bytes -> %d bytes)",
                 len(image_bytes), buf.tell())
        return buf.getvalue()

    @property
    def name(self) -> str:
        return "birefnet"


class RembgProvider(BackgroundRemovalProvider):
    """Local background removal using rembg library"""
    
    def __init__(self):
        try:
            from rembg import remove
            self._remove = remove
            LOG.info("rembg provider initialized")
        except ImportError:
            raise ImportError("rembg not installed. Run: pip install rembg")
    
    def remove_background(self, image_bytes: bytes) -> bytes:
        LOG.info("Processing with rembg (local)")
        return self._remove(image_bytes)
    
    @property
    def name(self) -> str:
        return "rembg"


class RemoveBgProvider(BackgroundRemovalProvider):
    """Cloud background removal using remove.bg API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        LOG.info("remove.bg provider initialized")
    
    def remove_background(self, image_bytes: bytes) -> bytes:
        import httpx
        LOG.info("Processing with remove.bg API")
        
        response = httpx.post(
            'https://api.remove.bg/v1.0/removebg',
            headers={'X-Api-Key': self.api_key},
            files={'image_file': image_bytes},
            data={'size': 'auto'},
            timeout=60
        )
        response.raise_for_status()
        return response.content
    
    @property
    def name(self) -> str:
        return "remove.bg"


class AzureVisionProvider(BackgroundRemovalProvider):
    """Azure AI Vision background removal using Image Analysis 4.0"""

    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint.rstrip('/')
        self.key = key
        LOG.info("Azure AI Vision provider initialized (endpoint: %s)", self.endpoint)

    def remove_background(self, image_bytes: bytes) -> bytes:
        import httpx

        LOG.info("Processing with Azure Computer Vision Image Analysis 4.0")

        # Use Image Analysis 4.0 API with backgroundRemoval feature
        # Requires resource-specific endpoint: {resource}.cognitiveservices.azure.com
        # (NOT the regional endpoint westeurope.api.cognitive.microsoft.com)
        url = f"{self.endpoint}/computervision/imageanalysis:segment"
        params = {
            "api-version": "2023-10-01",  # GA version for Image Analysis 4.0
            "mode": "backgroundRemoval"
        }
        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Content-Type": "application/octet-stream"
        }

        LOG.info("Calling Azure Vision API: %s?api-version=%s&mode=%s",
                 url, params['api-version'], params['mode'])

        # Call Azure Computer Vision API
        response = httpx.post(
            url,
            params=params,
            headers=headers,
            content=image_bytes,
            timeout=60
        )

        # Log response details for debugging
        LOG.info("Azure Vision API response: status=%d, content-type=%s, size=%d bytes",
                 response.status_code,
                 response.headers.get('content-type', 'unknown'),
                 len(response.content))

        response.raise_for_status()

        # The API returns a PNG image with transparent background
        result_bytes = response.content

        LOG.info("Azure Computer Vision background removal successful (%d bytes -> %d bytes)",
                 len(image_bytes), len(result_bytes))

        return result_bytes

    @property
    def name(self) -> str:
        return "azure-vision"


def get_provider(provider_name: str = "birefnet", **kwargs) -> BackgroundRemovalProvider:
    """Factory function to get background removal provider"""
    providers = {
        "birefnet": BiRefNetProvider,
        "rembg": RembgProvider,
        "remove.bg": RemoveBgProvider,
        "azure-vision": AzureVisionProvider,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")
    
    provider_class = providers[provider_name]
    return provider_class(**kwargs)
