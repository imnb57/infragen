"""Project schemas."""

from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas.common import CloudProvider, IaCTool


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    cloud_provider: CloudProvider = CloudProvider.AWS
    iac_tool: IaCTool = IaCTool.TERRAFORM
    region: str = "us-east-1"
    tags: list[str] = []


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cloud_provider: CloudProvider | None = None
    iac_tool: IaCTool | None = None
    region: str | None = None
    tags: list[str] | None = None
    is_archived: bool | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    cloud_provider: str
    iac_tool: str
    region: str
    tags: list[str]
    is_archived: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}
