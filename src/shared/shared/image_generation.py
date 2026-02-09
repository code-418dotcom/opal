"""
Image generation service abstraction.
Supports: FAL.AI, Replicate, Hugging Face
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional
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


class FalProvider(ImageGenerationProvider):
    """FAL.AI image generation (FLUX models)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://fal.run/fal-ai"
        LOG.info("FAL.AI provider initialized")
    
    def generate(self, prompt: str, image_url: Optional[str] = None, **kwargs) -> bytes:
        """Generate with FLUX-schnell (fast, high quality)"""
        LOG.info(f"Generating with FAL.AI FLUX: {prompt[:50]}...")
        
        # Use FLUX-schnell for fast generation
        endpoint = f"{self.base_url}/flux/schnell"
        
        payload = {
            "prompt": prompt,
            "image_size": "landscape_16_9",
            "num_inference_steps": 4,  # Fast mode
            "num_images": 1,
            "enable_safety_checker": False
        }
        
        # Add image conditioning if provided
        if image_url:
            payload["image_url"] = image_url
            payload["strength"] = 0.8  # Control influence
        
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
            
            LOG.info("FAL.AI generation successful")
            return img_response.content
    
    @property
    def name(self) -> str:
        return "fal.ai"


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
    """Factory function to get image generation provider"""
    providers = {
        "fal": FalProvider,
        "replicate": ReplicateProvider,
        "huggingface": HuggingFaceProvider,
    }
    
    if provider_name not in providers:
        raise ValueError(f"Unknown provider: {provider_name}. Available: {list(providers.keys())}")
    
    provider_class = providers[provider_name]
    return provider_class(**kwargs)
