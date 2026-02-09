import json
import base64
import logging

def init():
    logging.info("Noop model initialized")

def run(raw_data):
    logging.info("Noop model invoked")
    
    try:
        data = json.loads(raw_data)
        
        # Return a simple 1x1 transparent PNG as base64
        stub_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        return json.dumps({
            "image_bytes_b64": stub_image_b64,
            "tenant_id": data.get("tenant_id"),
            "job_id": data.get("job_id"),
            "item_id": data.get("item_id"),
            "status": "completed_stub"
        })
    except Exception as e:
        logging.error(f"Error: {e}")
        return json.dumps({"error": str(e)})
