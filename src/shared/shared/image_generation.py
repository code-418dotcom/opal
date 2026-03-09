"""
Image generation service abstraction.
Supports: FAL.AI (FLUX-dev, FLUX.2 Pro Edit), Replicate, Hugging Face
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, List
import httpx

LOG = logging.getLogger(__name__)


class ImageGenerationProvider(ABC):
    """Abstract base class for image generation providers"""

    @abstractmethod
    def generate(self, prompt: str, image_url: Optional[str] = None, **kwargs) -> bytes:
        """Generate image from prompt, optionally with reference image"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging"""
        pass

    @property
    def supports_edit(self) -> bool:
        """Whether this provider supports native image editing (no PIL compositing needed)."""
        return False


class FalProvider(ImageGenerationProvider):
    """FAL.AI image generation (FLUX-dev via flux-lora endpoint)"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://fal.run/fal-ai"
        LOG.info("FAL.AI provider initialized")

    NEGATIVE_PROMPT = (
        "objects, products, items, people, hands, text, letters, watermark, "
        "jewelry, accessories, clothing, food, bottles, cups, plants, flowers, "
        "decorations, ornaments, clutter, busy, crowded"
    )

    def generate(self, prompt: str, image_url: Optional[str] = None, **kwargs) -> bytes:
        """Generate with FLUX.1 [dev] via flux-lora endpoint (supports negative prompt)."""
        LOG.info(f"Generating with FAL.AI FLUX-dev: {prompt[:50]}...")

        # Allow runtime config via settings_service or kwargs
        num_steps = kwargs.get("num_inference_steps", 20)
        guidance = kwargs.get("guidance_scale", 3.5)
        model_endpoint = kwargs.get("fal_endpoint", "flux-lora")
        endpoint = f"{self.base_url}/{model_endpoint}"

        payload = {
            "prompt": prompt,
            "negative_prompt": self.NEGATIVE_PROMPT,
            "image_size": "landscape_16_9",
            "num_inference_steps": num_steps,
            "guidance_scale": guidance,
            "num_images": 1,
            "enable_safety_checker": False
        }

        # Add image conditioning if provided
        if image_url:
            payload["image_url"] = image_url
            payload["strength"] = 0.8

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

        with httpx.Client(timeout=120) as client:
            # Submit generation request
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            # Get image URL from result
            image_url = result["images"][0]["url"]

            # Download generated image
            img_response = client.get(image_url)
            img_response.raise_for_status()

            LOG.info("FAL.AI FLUX-dev generation successful")
            return img_response.content

    @property
    def name(self) -> str:
        return "fal.ai"


class FalFlux2ProEditProvider(ImageGenerationProvider):
    """FAL.AI FLUX.2 Pro Edit — native scene compositing.

    Sends the product image + scene prompt to FLUX.2 Pro Edit which
    generates the scene *around* the product with natural lighting,
    shadows and reflections.  No PIL compositing needed.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://fal.run/fal-ai"
        LOG.info("FAL.AI FLUX.2 Pro Edit provider initialized")

    @property
    def supports_edit(self) -> bool:
        return True

    def generate(self, prompt: str, image_url: Optional[str] = None, **kwargs) -> bytes:
        """Generate with FLUX.2 Pro Edit.

        When *image_url* is provided the model edits / composites the
        product into the described scene.  Without an image URL it falls
        back to pure text-to-image generation.
        """
        image_urls: List[str] = kwargs.get("image_urls") or (
            [image_url] if image_url else []
        )

        LOG.info(
            "Generating with FLUX.2 Pro Edit (images=%d): %s",
            len(image_urls), prompt[:80],
        )

        endpoint = f"{self.base_url}/flux-2-pro/edit"

        payload: dict = {
            "prompt": prompt,
            "image_size": kwargs.get("image_size", "landscape_16_9"),
            "output_format": "png",
            "safety_tolerance": "2",
            "enable_safety_checker": False,
        }

        if image_urls:
            payload["image_urls"] = image_urls

        seed = kwargs.get("seed")
        if seed is not None:
            payload["seed"] = int(seed)

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=180) as client:
            response = client.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            result_url = result["images"][0]["url"]
            img_response = client.get(result_url)
            img_response.raise_for_status()

            LOG.info("FLUX.2 Pro Edit generation successful")
            return img_response.content

    @property
    def name(self) -> str:
        return "fal.ai/flux2-pro-edit"


class ReplicateProvider(ImageGenerationProvider):
    """Replicate API (SDXL models)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        LOG.info("Replicate provider initialized")
    
    def generate(self, prompt: str, image_url: Optional[str] = None, **kwargs) -> bytes:
        LOG.info(f"Generating with Replicate SDXL: {prompt[:50]}...")
        
        import replicate
        
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": prompt,
                "image": image_url,
                "strength": 0.8 if image_url else None,
                "num_outputs": 1
            }
        )
        
        # Download image
        with httpx.Client(timeout=60) as client:
            response = client.get(output[0])
            response.raise_for_status()
            return response.content
    
    @property
    def name(self) -> str:
        return "replicate"


class HuggingFaceProvider(ImageGenerationProvider):
    """Hugging Face Inference API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        LOG.info("Hugging Face provider initialized")
    
    def generate(self, prompt: str, image_url: Optional[str] = None, **kwargs) -> bytes:
        LOG.info(f"Generating with Hugging Face: {prompt[:50]}...")
        
        endpoint = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        with httpx.Client(timeout=120) as client:
            response = client.post(endpoint, headers=headers, json={"inputs": prompt})
            response.raise_for_status()
            return response.content
    
    @property
    def name(self) -> str:
        return "huggingface"


def get_image_gen_provider(provider_name: str = "fal", **kwargs) -> ImageGenerationProvider:
    """Factory function to get image generation provider.

    Provider names:
      fal          – FLUX.1 [dev] via flux-lora (legacy, PIL compositing)
      fal-flux2    – FLUX.2 Pro Edit (native scene compositing)
      replicate    – Replicate SDXL
      huggingface  – HuggingFace Inference API
    """
    providers = {
        "fal": FalProvider,
        "fal-flux2": FalFlux2ProEditProvider,
        "replicate": ReplicateProvider,
        "huggingface": HuggingFaceProvider,
    }

    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")

    provider_class = providers[provider_name]
    return provider_class(**kwargs)
