# API Security Enhancements

## Current State
- ✅ Managed Identity for Azure services
- ✅ HTTPS enforced on all endpoints
- ✅ CORS configured
- 🟡 No API key authentication (add in Phase 2)

## Recommendations for Phase 2

### 1. Add API Key Authentication
Add to src/web_api/web_api/main.py:
```python
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name='X-API-Key')

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    valid_keys = os.getenv('API_KEYS', '').split(',')
    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid API key'
        )
    return api_key

# Then add to routes:
@router.post('/v1/jobs', dependencies=[Depends(verify_api_key)])
```

### 2. Rate Limiting
Consider using slowapi or fastapi-limiter:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get('/v1/jobs')
@limiter.limit('100/minute')
async def get_jobs():
    ...
```

### 3. Request Validation
- ✅ Already using Pydantic models
- ✅ FastAPI automatic validation
- Consider: Max file size limits, content type validation

### 4. CORS Hardening (for production)
Currently allows all origins. Update for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://yourdomain.com'],
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
    allow_headers=['*'],
)
```

## Current Security Features ✅
- HTTPS only (enforced by Azure Container Apps)
- Managed Identity (no keys in code)
- Environment variable secrets
- Network isolation (container apps internal communication)
- PostgreSQL SSL required
- Blob storage SAS tokens with expiry

