# api/api.py
from ninja import NinjaAPI
from .routers import documents_router, chat_router, auth_router

api = NinjaAPI(title="IntelliDoc API", version="1.0.0")

# Include routers
api.add_router("/documents/", documents_router)
api.add_router("/chat/", chat_router)
api.add_router("/auth/", auth_router)
