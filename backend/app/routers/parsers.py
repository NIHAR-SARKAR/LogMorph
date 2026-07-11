from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.parser import ParserTemplate
from app.models.user import User
from app.schemas.parser import ParserTemplate as PTSchema, ParserTemplateCreate, ParserTemplateUpdate, ParserTestRequest, ParserTestResult
from app.services.parser_service import parser_engine
from app.core.security import get_current_active_user, require_admin
from app.core.logging import logger

router = APIRouter(prefix="/parsers", tags=["Parsers"])

@router.get("/templates", response_model=List[PTSchema])
def list_templates(
    include_builtin: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all parser templates."""
    templates = db.query(ParserTemplate).all()

    if include_builtin:
        builtin = parser_engine.get_builtin_templates()
        for b in builtin:
            b["id"] = 0
            b["created_by_id"] = None
            b["created_at"] = None
            b["updated_at"] = None
        # Convert to schema objects
        from app.schemas.parser import ParserTemplate as PT
        builtin_schemas = [PT(**b) for b in builtin]
        return builtin_schemas + templates

    return templates

@router.post("/templates", response_model=PTSchema)
def create_template(
    template: ParserTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Create parser template."""
    db_template = ParserTemplate(
        **template.model_dump(),
        created_by_id=current_user.id
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

@router.get("/templates/{template_id}", response_model=PTSchema)
def get_template(
    template_id: int,
    db: Session = Depends(get_db)
):
    """Get parser template."""
    template = db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template

@router.put("/templates/{template_id}", response_model=PTSchema)
def update_template(
    template_id: int,
    template_update: ParserTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Update parser template."""
    template = db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot modify built-in template")

    for field, value in template_update.model_dump(exclude_unset=True).items():
        setattr(template, field, value)
    db.commit()
    db.refresh(template)
    return template

@router.delete("/templates/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete parser template."""
    template = db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if template.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in template")

    db.delete(template)
    db.commit()
    return {"message": f"Template '{template.name}' deleted"}

@router.post("/test", response_model=ParserTestResult)
def test_parser(
    request: ParserTestRequest,
    db: Session = Depends(get_db)
):
    """Test parser against sample log."""
    return parser_engine.test_parser(request)
