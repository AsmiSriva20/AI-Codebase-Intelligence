from pydantic import BaseModel, Field

from app.config import CHANGE_IMPACT_MAX_DEPTH


class CloneRequest(BaseModel):
    url: str


class SearchRequest(BaseModel):
    query: str
    branch: str | None = None


class AskRequest(BaseModel):
    question: str
    branch: str | None = None


class ExplainRequest(BaseModel):
    path: str


class ReferenceRequest(BaseModel):
    function: str


class CallGraphRequest(BaseModel):
    function: str


class DependencyRequest(BaseModel):
    path: str


class ArchitectureRequest(BaseModel):
    path: str
    branch: str | None = None


class SwitchBranchRequest(BaseModel):
    name: str


class ChangeImpactRequest(BaseModel):
    target: str
    branch: str | None = None
    max_depth: int = Field(default=CHANGE_IMPACT_MAX_DEPTH, ge=1, le=8)
