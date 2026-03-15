"""Common schemas — shared types and enums."""

from enum import Enum
from pydantic import BaseModel


class CloudProvider(str, Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"


class IaCTool(str, Enum):
    TERRAFORM = "terraform"
    PULUMI = "pulumi"
    CDK = "cdk"
    CLOUDFORMATION = "cloudformation"


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
