from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.ai import AIProvider as AIProviderSchema, AIProviderCreate, AIProviderUpdate, AIRequest, AIResponse, AIChatRequest
from app.services.ai_service import ai_service
from app.core.security import get_current_active_user, require_admin
from app.core.logging import logger

router = APIRouter(prefix="/ai", tags=["AI"])

@router.get("/providers", response_model=list[AIProviderSchema])
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all AI providers."""
    from app.models.ai import AIProvider
    return db.query(AIProvider).all()

@router.post("/providers", response_model=AIProviderSchema)
def create_provider(
    provider: AIProviderCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Create AI provider (admin only)."""
    from app.models.ai import AIProvider
    db_provider = AIProvider(**provider.model_dump())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    logger.info(f"AI provider created: {db_provider.name} by {admin.username}")
    return db_provider

@router.put("/providers/{provider_id}", response_model=AIProviderSchema)
def update_provider(
    provider_id: int,
    provider_update: AIProviderUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Update AI provider."""
    from app.models.ai import AIProvider
    provider = db.query(AIProvider).filter(AIProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    for field, value in provider_update.model_dump(exclude_unset=True).items():
        setattr(provider, field, value)
    db.commit()
    db.refresh(provider)
    return provider

@router.delete("/providers/{provider_id}")
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Delete AI provider."""
    from app.models.ai import AIProvider
    provider = db.query(AIProvider).filter(AIProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    db.delete(provider)
    db.commit()
    return {"message": f"Provider {provider.name} deleted"}

@router.post("/generate", response_model=AIResponse)
async def generate(
    request: AIRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate AI response."""
    return await ai_service.generate(db, request)

@router.post("/chat", response_model=AIResponse)
async def chat(
    request: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Chat with AI."""
    return await ai_service.chat(db, request)

@router.post("/summarize")
async def summarize(
    log_entries: list[str],
    provider_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Summarize log entries with AI."""
    return await ai_service.summarize_logs(db, log_entries, provider_id)

@router.post("/analyze-exception")
async def analyze_exception(
    exception_type: str,
    stack_trace: str,
    provider_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Analyze exception with AI."""
    return await ai_service.analyze_exception(db, exception_type, stack_trace, provider_id)
