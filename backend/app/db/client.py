from functools import lru_cache
from supabase import Client, create_client
from app.core.config import get_settings

@lru_cache
def get_supabase_client() -> Client:
    """Create a client from environment configuration; never hard-code keys."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise RuntimeError('Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in backend/.env first.')
    return create_client(settings.supabase_url, settings.supabase_publishable_key)
