from sqlalchemy import select, func
from app.core.database import SessionLocal
from app.core.security import sanitize_pii_lgpd
from app.models import AuditLog, Course, Enrollment
from app.services.ai import load_markdown_docs, ROLE_DAILY_QUOTA

try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("SmartCampus-Secure-MCP")
except ImportError:  # pragma: no cover
    class _FallbackMCP:
        def tool(self):
            return lambda fn: fn
    mcp = _FallbackMCP()


def _log_tool_call(actor_user_id: int, tool_name: str, details: dict) -> None:
    db = SessionLocal()
    try:
        db.add(AuditLog(
            actor_user_id=actor_user_id,
            action="MCP_TOOL_CALL",
            resource_type="mcp_tool",
            resource_id=tool_name,
            details=details,
        ))
        db.commit()
    finally:
        db.close()


@mcp.tool()
def consultar_regras_academicas(topico: str, authenticated_user_id: int) -> dict:
    """Busca segura (Read-Only) nos documentos .md institucionais."""
    clean_topic = sanitize_pii_lgpd(topico).lower()
    matches = [
        d for d in load_markdown_docs()
        if any(w in (d["source"] + " " + d["content"]).lower() for w in clean_topic.split() if len(w) >= 3)
    ]
    _log_tool_call(authenticated_user_id, "consultar_regras_academicas", {"topic": clean_topic[:80], "hits": len(matches)})
    return {"matches": matches[:3]}


@mcp.tool()
def consultar_minhas_matriculas(authenticated_user_id: int) -> list[dict]:
    """Anti-IDOR: retorna apenas matrículas do próprio usuário autenticado."""
    db = SessionLocal()
    try:
        rows = db.scalars(select(Enrollment).where(Enrollment.student_id == authenticated_user_id)).all()
        result = [{"id": r.id, "course_id": r.course_id, "status": r.status} for r in rows]
        _log_tool_call(authenticated_user_id, "consultar_minhas_matriculas", {"count": len(result)})
        return result
    finally:
        db.close()


@mcp.tool()
def consultar_painel_staff(authenticated_user_id: int, role: str) -> dict:
    """RBAC: permite indicadores operacionais apenas para ADMIN ou SUPPORT."""
    if role not in ("ADMIN", "SUPPORT"):
        _log_tool_call(authenticated_user_id, "consultar_painel_staff", {"denied_role": role})
        return {"error": "Acesso negado: requer perfil ADMIN ou SUPPORT."}
    db = SessionLocal()
    try:
        courses = db.scalar(select(func.count()).select_from(Course)) or 0
        enrollments = db.scalar(select(func.count()).select_from(Enrollment)) or 0
        _log_tool_call(authenticated_user_id, "consultar_painel_staff", {"role": role})
        return {"total_courses": courses, "total_enrollments": enrollments}
    finally:
        db.close()


@mcp.tool()
def verificar_cota_tokens(authenticated_user_id: int, role: str) -> dict:
    """Retorna o limite diário de interações IA configurado para o perfil."""
    return {"user_id": authenticated_user_id, "role": role, "daily_limit": ROLE_DAILY_QUOTA.get(role, 30)}
