"""Pydantic models for what the LLM returns: the generated prompt and clarifying questions."""

from pydantic import BaseModel, Field, model_validator

MAX_QUESTIONS = 4


class GeneratedPrompt(BaseModel):
    """A structured LLM prompt built from the user's input for one target."""

    target: str = Field(description="Key in TARGETS, e.g. 'data_analytics'.")
    title: str = Field(description="Short name for the prompt.")
    sections: dict[str, str] = Field(description="Section name -> text, following the target's required_sections.")
    assumptions: list[str] = Field(default_factory=list, description="Gaps the model filled in, stated openly.")
    final_prompt: str = Field(description="The full prompt, ready to paste.")


class ClarifyingQuestion(BaseModel):
    """One question about missing information that changes the SQL, with short answer options."""

    question: str = Field(min_length=1)
    why: str = Field(min_length=1, description="One short line on why the answer changes the SQL.")
    options: list[str] = Field(min_length=2, max_length=4)
    default: str = Field(min_length=1, description="One of the options.")

    @model_validator(mode="after")
    def default_is_an_option(self) -> "ClarifyingQuestion":
        """Fall back to the first option when the model's default isn't one of its options."""
        # Small models sometimes rephrase the default; the question is still useful, so fix rather than reject.
        if self.default not in self.options:
            self.default = self.options[0]
        return self
