"""Pydantic model for the structured prompt returned by the LLM."""

from pydantic import BaseModel, Field


class GeneratedPrompt(BaseModel):
    """A structured LLM prompt built from the user's input."""

    role: str = Field(description="Who the model should act as.")
    task: str = Field(description="What the model must do.")
    context: str = Field(description="Background the model needs.")
    constraints: list[str] = Field(default_factory=list, description="Rules the answer must follow.")
    output_format: str = Field(description="Shape of the expected answer.")
    final_prompt: str = Field(description="The full prompt, ready to paste.")
