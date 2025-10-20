# app/nodes/graph_state/schema.py
# LangGraph 워크플로우 데이터 스키마 정의

from dataclasses import dataclass
from pydantic import BaseModel, Field
from typing import TypedDict, Annotated, Optional, List, Dict, Any

@dataclass
class Metadata(TypedDict):
    """
    고객이 업로드한 파일의 메타데이터
    """
    filename: str = Field(..., description="고객이 업로드한 파일의 타이틀")