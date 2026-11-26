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
    """Saves or updates the prospect's contact details in the user state.

    Call this tool whenever the user provides or corrects one or more of the
    required details. Only pass the fields that the user has mentioned.

    Args:
        tool_context: Automatically provided by ADK.
        full_name: The user's full name.
        birth_date: The user's date of birth (e.g., "03/15/1990" or "1990-03-15").
        email: The user's email address.
        contact_reason: A brief reason why the user wants to be contacted.

    Returns:
        A dictionary with the capture status ("complete" or "incomplete"),
        saved data, missing fields, and any validation errors.
    """
    existing = tool_context.state.get("user:lead_info", {})
    lead = dict(existing) if isinstance(existing, dict) else {}
    validation_errors: dict[str, str] = {}

    if full_name is not None:
        cleaned = full_name.strip()
        if cleaned:
            lead["full_name"] = cleaned
        else:
            validation_errors["full_name"] = "Full name cannot be empty."

    if birth_date is not None:
        cleaned = birth_date.strip()
        if cleaned:
            lead["birth_date"] = cleaned
        else:
            validation_errors["birth_date"] = "Date of birth cannot be empty."

    if email is not None:
        cleaned = email.strip().lower()
        if _EMAIL_PATTERN.match(cleaned):
            lead["email"] = cleaned
        else:
            validation_errors["email"] = (
                "Email address is not in a valid format (example: name@domain.com)."
            )

    if contact_reason is not None:
        cleaned = contact_reason.strip()
        if cleaned:
            lead["contact_reason"] = cleaned
        else:
            validation_errors["contact_reason"] = "Contact reason cannot be empty."

    tool_context.state["user:lead_info"] = lead
    missing_fields = [field for field in REQUIRED_LEAD_FIELDS if not lead.get(field)]

    return {
        "status": "complete" if not missing_fields else "incomplete",
        "lead": lead,
        "missing_fields": missing_fields,
        "validation_errors": validation_errors,
    }


def get_lead_info(tool_context: ToolContext) -> dict:
    """Retrieves the prospect details captured so far and the missing fields.

    Args:
        tool_context: Automatically provided by ADK.

    Returns:
        A dictionary with the current capture status, saved data, and missing fields.
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
        "Lead capture agent that collects full name, date of birth, "
        "email address, and a brief reason for contact."
    ),
    instruction=(
        "You are a friendly and professional assistant responsible for capturing contact details.\n\n"
        "Your goal is to collect the following 4 required details from the user:\n"
        "1. Full name (`full_name`)\n"
        "2. Date of birth (`birth_date`)\n"
        "3. Email address (`email`)\n"
        "4. Brief reason for contact (`contact_reason`)\n\n"
        "Behavior rules:\n"
        "- Respond in English (or in the language the user uses) in a polite, clear, and concise manner.\n"
        "- Whenever the user provides or corrects any of these details, immediately call "
        "the `save_lead_info` tool with the received fields.\n"
        "- If `save_lead_info` returns errors in `validation_errors`, politely ask the user "
        "to correct that field.\n"
        "- Check `missing_fields` and ask only for the details that are still missing, without "
        "asking again for those already saved.\n"
        "- When `status` is `complete`, display a clear summary of all 4 captured details, "
        "thank the user, and ask if they would like to correct any information."
    ),
    tools=[save_lead_info, get_lead_info],
)
