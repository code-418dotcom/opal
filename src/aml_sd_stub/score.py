import base64
from fastapi import FastAPI
from pydantic import BaseModel

# This is an AML "stub" that returns a fake PNG payload.
# Replace this container with Stable Diffusion placement later.

app = FastAPI()

# A tiny 1x1 transparent PNG
ONE_BY_ONE_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
    "ASsJTYQAAAAASUVORK5CYII="
)

class InferenceRequest(BaseModel):
    tenant_id: str
    job_id: str
    item_id: str
    input_image_sas: str
    prompt: str

@app.post("/score")
def score(req: InferenceRequest):
    # We ignore the input_image_sas in the stub and return a constant output.
    return {
        "image_bytes_b64": ONE_BY_ONE_PNG_B64,
        "meta": {
            "prompt_used": req.prompt,
            "note": "stub response - replace with Stable Diffusion later"
        }
    }
