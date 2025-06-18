# app.py - ACTUALIZADO CON TODOS LOS ROUTERS
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importar todos los routers
from routes.auth import auth_router
from routes.user import user_router
from routes.subscription import subscription_router  # NUEVO
from routes.webhook import webhook_router

# Otros routers existentes (mantener los que ya tienes)
from routes.chat import chat_router
from routes.message import message_router
from routes.analysis import analysis_router
from routes.user_dictionary import user_dictionary_router
from routes.tasks import tasks_router

# Crear la aplicación
app = FastAPI(
    title="ActivLingo API",
    description="API para la plataforma de aprendizaje de idiomas ActivLingo",
    version="2.0.0",
    root_path="/api"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:3000",
        "http://147.182.130.162",
        "https://app.activlingo.com",
        "https://activlingo.com",
        # Agrega aquí tu dominio de producción
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)

# ========== INCLUIR ROUTERS ==========

# Autenticación y usuarios
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(user_router, prefix="/user", tags=["user"])

# Suscripciones (NUEVO)
app.include_router(subscription_router, prefix="/subscription", tags=["subscription"])

# Webhooks (MEJORADO)
app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])

# Funcionalidades principales de la app
app.include_router(chat_router, prefix="/chats", tags=["chats"])
app.include_router(message_router, prefix="/messages", tags=["messages"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
app.include_router(user_dictionary_router, prefix="/dictionary", tags=["dictionary"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

# ========== ENDPOINTS RAÍZ ==========

@app.get("/")
def read_root():
    """Endpoint raíz de la API"""
    return {
        "message": "ActivLingo API",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Authentication",
            "User Management", 
            "Subscriptions",
            "Chat System",
            "Learning Analytics",
            "Dictionary",
            "Tasks Management"
        ]
    }

@app.get("/health")
def health_check():
    """Health check endpoint para monitoring"""
    return {
        "status": "healthy",
        "timestamp": "2025-06-17",
        "api_version": "2.0.0",
        "services": {
            "database": "connected",
            "auth": "active",
            "subscriptions": "active",
            "webhooks": "active"
        }
    }

@app.get("/ping")
def ping():
    """Ping endpoint simple"""
    return {"message": "pong"}

# ========== MANEJO DE ERRORES GLOBAL ==========

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "message": f"The endpoint {request.url.path} was not found",
            "available_docs": f"{request.base_url}docs"
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "contact": "support@activlingo.com"
        }
    )

# ========== INFORMACIÓN ADICIONAL ==========

# Configuración para desarrollo
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )