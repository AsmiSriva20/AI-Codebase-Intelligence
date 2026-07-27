from pydantic import BaseModel


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
