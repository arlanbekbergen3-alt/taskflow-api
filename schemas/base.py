from typing import ClassVar

from pydantic import BaseModel, ConfigDict, model_validator


class AppBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PatchModel(BaseModel):
    """Base for PATCH payloads.

    Fields listed in `non_nullable` may be omitted, but not sent as an
    explicit null: that would hit a NOT NULL constraint and surface as a
    500 instead of a clean 422.
    """

    non_nullable: ClassVar[tuple[str, ...]] = ()

    @model_validator(mode="after")
    def _reject_explicit_null(self):
        for name in self.non_nullable:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self
