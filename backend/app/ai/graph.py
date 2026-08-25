from typing import Optional, Dict, Any

from pydantic import BaseModel

from app.models.hcp import HCP
from app.services.hcp_service import HCPService
from app.services.interaction_service import InteractionService
from app.schemas.interaction_schema import InteractionCreate
from app.ai.wrapper import try_extract_with_optional_live, ExtractionError

# Strict LangGraph integration per requested API
from langgraph.graph import StateGraph, START, END


class LogMeetingState(BaseModel):
    meeting_text: str
    user_id: int
    mock_extraction: Optional[dict] = None

    # populated during graph execution
    extraction: Optional[dict] = None
    extraction_result: Optional[dict] = None
    extraction_valid: bool = False
    hcp_found: bool = False
    is_new_hcp: bool = False
    doctor_id: Optional[int] = None
    hcp_id: Optional[int] = None
    result: Optional[dict] = None


# Build the typed StateGraph
workflow = StateGraph(LogMeetingState)


# Node implementations
def extract_interaction(state: LogMeetingState) -> dict:
    # Perform extraction using wrapper (may raise RuntimeError if GROQ blocked)
    extraction = try_extract_with_optional_live(state.meeting_text, mock_extraction=state.mock_extraction)
    extracted = extraction.dict()
    return {
        "extraction": extracted,
        "extraction_result": extracted,
        "extraction_valid": True,
        "result": None,
    }


def validate_extraction(state: LogMeetingState) -> dict:
    # Validation step: ensure required fields are present
    if not state.extraction:
        return {
            "extraction_valid": False,
            "result": {"success": False, "message": "No extraction available"},
        }
    if not state.extraction.get("doctor_name"):
        return {
            "extraction_valid": False,
            "result": {"success": False, "message": "Doctor name could not be identified"},
        }
    return {
        "extraction_valid": True,
        "result": None,
    }


def find_hcp(state: LogMeetingState) -> dict:
    if not state.extraction:
        return {
            "hcp_found": False,
            "is_new_hcp": False,
            "doctor_id": None,
            "hcp_id": None,
            "result": {"success": False, "message": "No doctor match available"},
        }
    doctor_name = state.extraction.get("doctor_name")
    global _CURRENT_DB
    doctors = HCPService.get_all_hcps(_CURRENT_DB)
    # Perform case-insensitive match
    found = None
    for d in doctors:
        try:
            if d.doctor_name and d.doctor_name.strip().lower() == doctor_name.strip().lower():
                found = d
                break
        except Exception:
            continue

    if not found:
        return {
            "hcp_found": False,
            "is_new_hcp": True,
            "doctor_id": None,
            "hcp_id": None,
            "result": None,
        }
    return {
        "hcp_found": True,
        "is_new_hcp": False,
        "doctor_id": found.id,
        "hcp_id": found.id,
        "result": None,
    }


def create_hcp(state: LogMeetingState) -> dict:
    if not state.extraction or not state.extraction.get("doctor_name"):
        return {
            "hcp_found": False,
            "result": {"success": False, "message": "Cannot create HCP without doctor name"},
        }
    global _CURRENT_DB
    doctor_name = state.extraction.get("doctor_name").strip()
    hospital = (state.extraction.get("hospital") or "Not Specified").strip()
    specialization = (state.extraction.get("specialization") or "General Medicine").strip()
    city = (state.extraction.get("city") or "Not Specified").strip()

    # Create new HCP using ONLY information actually present in transcript (phone/email remain null)
    new_hcp = HCP(
        doctor_name=doctor_name,
        specialization=specialization,
        hospital=hospital,
        city=city,
        phone=None,
        email=None,
    )
    _CURRENT_DB.add(new_hcp)
    _CURRENT_DB.commit()
    _CURRENT_DB.refresh(new_hcp)

    return {
        "hcp_found": True,
        "is_new_hcp": True,
        "doctor_id": new_hcp.id,
        "hcp_id": new_hcp.id,
        "result": None,
    }


def create_interaction(state: LogMeetingState) -> dict:
    if not state.hcp_found or not state.doctor_id or not state.extraction:
        return {
            "result": {"success": False, "message": "Preconditions not met for creating interaction"},
        }
    interaction_payload = InteractionCreate(
        user_id=state.user_id,
        hcp_id=state.doctor_id,
        meeting_notes=state.extraction.get("meeting_summary"),
        products_discussed=state.extraction.get("products_discussed") or "",
        follow_up_date=state.extraction.get("follow_up_date"),
    )
    global _CURRENT_DB
    interaction_result = InteractionService.create_interaction(_CURRENT_DB, interaction_payload)
    if interaction_result.get("success"):
        interaction_result["doctor_id"] = state.doctor_id
        interaction_result["is_new_hcp"] = getattr(state, "is_new_hcp", False)
        interaction_result["extraction"] = state.extraction
    return {"result": interaction_result}


# Register nodes with the workflow
workflow.add_node("extract_interaction", extract_interaction)
workflow.add_node("validate_extraction", validate_extraction)
workflow.add_node("find_hcp", find_hcp)
workflow.add_node("create_hcp", create_hcp)
workflow.add_node("create_interaction", create_interaction)


def validation_router(state: LogMeetingState):
    if getattr(state, "extraction_valid", False):
        return "find_hcp"
    return "end"


def hcp_router(state: LogMeetingState):
    if getattr(state, "hcp_found", False):
        return "create_interaction"
    elif getattr(state, "extraction_valid", False):
        return "create_hcp"
    return "end"


# Add edges per the required structure
workflow.add_edge(START, "extract_interaction")
workflow.add_edge("extract_interaction", "validate_extraction")

# Conditional edges from validate_extraction
workflow.add_conditional_edges(
    "validate_extraction",
    validation_router,
    {
        "find_hcp": "find_hcp",
        "end": END,
    },
)

# Conditional edges from find_hcp
workflow.add_conditional_edges(
    "find_hcp",
    hcp_router,
    {
        "create_interaction": "create_interaction",
        "create_hcp": "create_hcp",
        "end": END,
    },
)

# create_hcp -> create_interaction
workflow.add_edge("create_hcp", "create_interaction")

# create_interaction -> END
workflow.add_edge("create_interaction", END)

# Compile the workflow
compiled_graph = workflow.compile()


# Settable DB reference used by node actions. Must be set before invocation.
_CURRENT_DB = None


def run_state_graph(db, meeting_text: str, user_id: int, mock_extraction: Optional[dict] = None) -> Dict[str, Any]:
    """Execute the compiled LangGraph StateGraph using compiled_graph.invoke(initial_state).

    Note: this function intentionally does not perform any imperative fallback logic.
    It relies on langgraph to execute the graph and raise if something went wrong.
    """
    # Build initial state
    initial_state = LogMeetingState(meeting_text=meeting_text, user_id=user_id, mock_extraction=mock_extraction)

    # Set DB reference for nodes
    global _CURRENT_DB
    _CURRENT_DB = db

    # Invoke compiled graph
    invoked = compiled_graph.invoke(initial_state)

    # LangGraph may return the final state object or a dict-like state container.
    if isinstance(invoked, dict):
        final_state = invoked.get("value", invoked)
    else:
        final_state = getattr(invoked, "value", invoked)

    # Expect the final state to carry the result payload generated by create_interaction.
    if isinstance(final_state, dict):
        result = final_state.get("result")
    else:
        result = getattr(final_state, "result", None)

    if result is not None:
        return result

    # If graph ended without explicit result, return a safe failure
    return {"success": False, "message": "Graph executed but no result returned"}