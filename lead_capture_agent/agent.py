import re
from typing import Optional

from google.adk.agents.llm_agent import Agent
from google.adk.tools import ToolContext

REQUIRED_LEAD_FIELDS = (
    "full_name",
    "birth_date",
    "email",
    "contact_reason",
)

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def save_lead_info(
    tool_context: ToolContext,
    full_name: Optional[str] = None,
    birth_date: Optional[str] = None,
    email: Optional[str] = None,
    contact_reason: Optional[str] = None,
) -> dict:
    """Guarda o actualiza los datos de contacto del prospecto en el estado del usuario.

    Llama a esta herramienta cada vez que el usuario proporcione o corrija uno o más
    de los datos requeridos. Solo envía los campos que el usuario haya mencionado.

    Args:
        tool_context: Proporcionado automáticamente por ADK.
        full_name: Nombre completo del usuario.
        birth_date: Fecha o día de nacimiento del usuario (por ejemplo, "15/03/1990" o "1990-03-15").
        email: Correo electrónico del usuario.
        contact_reason: Razón breve por la cual el usuario desea ser contactado.

    Returns:
        Un diccionario con el estado de captura ("complete" o "incomplete"), los datos
        guardados, los campos faltantes y posibles errores de validación.
    """
    existing = tool_context.state.get("user:lead_info", {})
    lead = dict(existing) if isinstance(existing, dict) else {}
    validation_errors: dict[str, str] = {}

    if full_name is not None:
        cleaned = full_name.strip()
        if cleaned:
            lead["full_name"] = cleaned
        else:
            validation_errors["full_name"] = "El nombre completo no puede estar vacío."

    if birth_date is not None:
        cleaned = birth_date.strip()
        if cleaned:
            lead["birth_date"] = cleaned
        else:
            validation_errors["birth_date"] = "La fecha de nacimiento no puede estar vacía."

    if email is not None:
        cleaned = email.strip().lower()
        if _EMAIL_PATTERN.match(cleaned):
            lead["email"] = cleaned
        else:
            validation_errors["email"] = (
                "El correo electrónico no tiene un formato válido (ejemplo: nombre@dominio.com)."
            )

    if contact_reason is not None:
        cleaned = contact_reason.strip()
        if cleaned:
            lead["contact_reason"] = cleaned
        else:
            validation_errors["contact_reason"] = "La razón de contacto no puede estar vacía."

    tool_context.state["user:lead_info"] = lead
    missing_fields = [field for field in REQUIRED_LEAD_FIELDS if not lead.get(field)]

    return {
        "status": "complete" if not missing_fields else "incomplete",
        "lead": lead,
        "missing_fields": missing_fields,
        "validation_errors": validation_errors,
    }


def get_lead_info(tool_context: ToolContext) -> dict:
    """Obtiene los datos del prospecto capturados hasta el momento y los campos faltantes.

    Args:
        tool_context: Proporcionado automáticamente por ADK.

    Returns:
        Un diccionario con el estado actual de captura, los datos guardados y los campos faltantes.
    """
    existing = tool_context.state.get("user:lead_info", {})
    lead = dict(existing) if isinstance(existing, dict) else {}
    missing_fields = [field for field in REQUIRED_LEAD_FIELDS if not lead.get(field)]

    return {
        "status": "complete" if not missing_fields else "incomplete",
        "lead": lead,
        "missing_fields": missing_fields,
    }


root_agent = Agent(
    model="gemini-3.5-flash-lite",
    name="root_agent",
    description=(
        "Agente de captura de prospectos que recopila nombre completo, fecha de nacimiento, "
        "correo electrónico y razón breve de contacto."
    ),
    instruction=(
        "Eres un asistente amable y profesional encargado de capturar datos de contacto.\n\n"
        "Tu objetivo es recopilar los siguientes 4 datos obligatorios del usuario:\n"
        "1. Nombre completo (`full_name`)\n"
        "2. Día / fecha de nacimiento (`birth_date`)\n"
        "3. Correo electrónico (`email`)\n"
        "4. Razón breve de contacto (`contact_reason`)\n\n"
        "Reglas de comportamiento:\n"
        "- Responde en español (o en el idioma que use el usuario) de forma cordial, clara y concisa.\n"
        "- Cada vez que el usuario proporcione o corrija cualquiera de estos datos, llama inmediatamente "
        "a la herramienta `save_lead_info` con los campos recibidos.\n"
        "- Si `save_lead_info` devuelve errores en `validation_errors`, pide amablemente al usuario que "
        "corrija ese dato.\n"
        "- Revisa `missing_fields` y solicita únicamente los datos que aún falten, sin volver a pedir "
        "los que ya fueron guardados.\n"
        "- Cuando `status` sea `complete`, muestra un resumen claro con los 4 datos capturados, "
        "agradece al usuario y pregúntale si desea corregir algún dato."
    ),
    tools=[save_lead_info, get_lead_info],
)
