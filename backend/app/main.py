from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.routes.health import router as health_router
settings=get_settings()
app=FastAPI(title=settings.app_name,description='Phase 1 starter API. Hospital workflows are not implemented yet.',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=['GET','POST','PATCH','PUT','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type','Idempotency-Key'])
app.include_router(health_router,prefix=settings.api_v1_prefix)
@app.get('/',tags=['root'],include_in_schema=False)
def root()->dict[str,str]: return {'service':settings.app_name,'docs':'/docs'}
