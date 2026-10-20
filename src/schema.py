"""Pydantic model for the structured prompt returned by the LLM."""

from pydantic import BaseModel, Field


class GeneratedPrompt(BaseModel):
    """A structured LLM prompt built from the user's input for one target."""

    target: str = Field(description="Key in TARGETS, e.g. 'coding_agent'.")
    title: str = Field(description="Short name for the prompt.")
    sections: dict[str, str] = Field(description="Section name -> text, following the target's required_sections.")
    assumptions: list[str] = Field(default_factory=list, description="Gaps the model filled in, stated openly.")
    final_prompt: str = Field(description="The full prompt, ready to paste.")
    negative_prompt: str = Field(default="", description="What to avoid; used by image_generation only.")
