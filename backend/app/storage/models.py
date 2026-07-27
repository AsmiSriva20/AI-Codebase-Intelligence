import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.storage.db import Base


def _uuid():
    return str(uuid.uuid4())


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    url = Column(String, nullable=False)
    status = Column(String, nullable=False, default="cloning")  # cloning | built | failed
    cloned_at = Column(DateTime(timezone=True))
    built_at = Column(DateTime(timezone=True))
    error_message = Column(String)

    branches = relationship("Branch", back_populates="repository", cascade="all, delete-orphan")


class Branch(Base):
    __tablename__ = "branches"
    __table_args__ = (UniqueConstraint("repository_id", "name", name="uq_branch_repo_name"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    repository_id = Column(UUID(as_uuid=False), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    last_commit_sha = Column(String)
    indexed_at = Column(DateTime(timezone=True))

    repository = relationship("Repository", back_populates="branches")
    files = relationship("File", back_populates="branch", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="branch", uselist=False, cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("branch_id", "path", name="uq_file_branch_path"),)

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    branch_id = Column(UUID(as_uuid=False), ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    path = Column(String, nullable=False)
    extension = Column(String)
    size = Column(Integer)
    analysis = Column(JSONB)  # functions/classes/imports (any language) or raw_text fallback

    branch = relationship("Branch", back_populates="files")


class Report(Base):
    __tablename__ = "reports"

    branch_id = Column(UUID(as_uuid=False), ForeignKey("branches.id", ondelete="CASCADE"), primary_key=True)
    issues_report = Column(JSONB)
    dependency_report = Column(JSONB)
    dead_code_report = Column(JSONB)
    hotspots_report = Column(JSONB)
    architecture_report = Column(JSONB)  # generate_architecture() output, cached to skip re-parsing every request
    call_graph_report = Column(JSONB)    # build_call_graph() output, cached the same way
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    branch = relationship("Branch", back_populates="report")
