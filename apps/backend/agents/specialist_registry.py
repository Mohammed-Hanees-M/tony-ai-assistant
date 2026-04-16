from typing import List, Dict
from apps.backend.schemas.agent import SpecialistProfile

SPECIALISTS: Dict[str, SpecialistProfile] = {
    "coding_expert": SpecialistProfile(
        id="coding_expert",
        name="Coding Specialist",
        domain="software",
        description="Expert in programming, algorithms, debugging and code generation.",
        capability_tags=["python", "javascript", "bash", "architecture", "debugging"]
    ),
    "research_expert": SpecialistProfile(
        id="research_expert",
        name="Research Specialist",
        domain="information",
        description="Expert in looking up facts, summarizing web pages, and structuring information.",
        capability_tags=["web_search", "summarization", "literature_review", "fact_checking"]
    ),
    "planning_expert": SpecialistProfile(
        id="planning_expert",
        name="Planning Specialist",
        domain="orchestration",
        description="Expert in breaking down goals into actionable steps.",
        capability_tags=["decomposition", "strategy", "project_management"],
        can_manage_subtasks=True,
        child_specialist_tags=["coding_expert", "research_expert", "finance_expert", "writing_expert"]
    ),
    "finance_expert": SpecialistProfile(
        id="finance_expert",
        name="Finance Specialist",
        domain="finance",
        description="Expert in math, financial modeling, and economic statistics.",
        capability_tags=["math", "analysis", "markets", "accounting"]
    ),
    "writing_expert": SpecialistProfile(
        id="writing_expert",
        name="Writing Specialist",
        domain="communication",
        description="Expert in creative writing, editing, and formatting.",
        capability_tags=["copywriting", "editing", "formatting", "creative"]
    )
}

def get_specialist(specialist_id: str) -> SpecialistProfile:
    return SPECIALISTS.get(specialist_id)

def list_all_specialists() -> List[SpecialistProfile]:
    return list(SPECIALISTS.values())
