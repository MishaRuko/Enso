"""Structured verification models for furniture placement — whisker pattern."""

from typing import Literal

from pydantic import BaseModel, Field


class LayoutQuestion(BaseModel):
    question: str = Field(description="A Yes/No question about the layout")
    answer: Literal["yes", "no", "unclear"] = Field(description="Visual evaluation answer")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0-1")
    reasoning: str = Field(description="Brief explanation")


class LayoutIssue(BaseModel):
    description: str = Field(
        description="What looks wrong (e.g. 'sofa overlaps dining table')"
    )
    severity: Literal["critical", "major", "minor"] = Field(
        description="How important this issue is"
    )
    affected_items: list[str] = Field(
        description="Item names involved (e.g. ['FRIHETEN Sofa', 'DANDERYD Table'])"
    )
    suggested_fix: str = Field(
        description="Specific coordinate adjustment (e.g. 'move sofa to x=2.0, z=6.5')"
    )


class PlacementVerificationResult(BaseModel):
    answers: list[LayoutQuestion] = Field(description="Answers to layout validation questions")
    visual_issues: list[LayoutIssue] = Field(
        default_factory=list,
        description="Specific spatial problems observed in the rendered views",
    )
    overall_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall quality score (0=terrible, 1=perfect)",
    )
    summary: str = Field(description="Brief summary of the verification findings")
