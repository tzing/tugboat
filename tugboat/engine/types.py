from __future__ import annotations

import io
import os
import textwrap
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import (
    BaseModel,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

if TYPE_CHECKING:
    from typing import Self


class DiagnosisModel(BaseModel):
    """A diagnosis reported by the analyzer."""

    # this class is a data model that conveys the same information as `tugboat.types.Diagnosis`
    # but is implemented using `pydantic.BaseModel`

    line: Annotated[
        int,
        Field(
            default=0,
            description=(
                "1-based line number in the YAML input where the issue begins. "
                "Line numbers continue across documents within the same multi-document stream."
            ),
        ),
    ]

    column: Annotated[
        int,
        Field(
            default=0,
            description=(
                "1-based column number for the first problematic character on that line."
            ),
        ),
    ]

    type: Annotated[
        Literal["error", "failure", "warning"],
        Field(
            default="failure",
            description=(
                "Diagnostic severity reported by the analyzer.\n"
                "* `error`: analysis stopped because processing could not continue.\n"
                "* `failure`: definite rule violation that prevents success.\n"
                "* `warning`: potential issue that should be reviewed.\n"
            ),
        ),
    ]

    code: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            to_upper=True,
            pattern=r"^[a-zA-Z]+\d+$",
        ),
        Field(
            description=(
                "Rule identifier for this diagnosis. "
                "Look up details at https://argo-tugboat.readthedocs.io/en/stable/search.html?q=CODE by replacing `CODE` with the value provided here."
            )
        ),
    ]

    loc: Annotated[
        tuple[str | int, ...],
        Field(
            description=(
                "JSONPath-like list that walks from the manifest root to the problematic field."
                'For example, an issue in `spec.containers[0].name` becomes `["spec", "containers", 0, "name"]`.'
            )
        ),
    ]

    summary: Annotated[
        str,
        Field(
            default="",
            description="Short title for the diagnosis, most often the rule name.",
        ),
    ]

    msg: Annotated[
        str,
        Field(
            description="Full sentence that explains the issue and may include fix guidance.",
        ),
    ]

    input: Annotated[
        str | int | bool | float | Any | None,
        Field(
            default=None,
            description="Original manifest value that triggered the diagnosis, when available.",
        ),
    ]

    fix: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Analyzer's suggested fix presented as plain text. Treat this as guidance, not a guaranteed solution."
            ),
        ),
    ]

    extras: Annotated[
        Extras,
        Field(
            default_factory=lambda: Extras.model_validate({}),
            description="Structured container for any additional context (see `Extras`).",
        ),
    ]

    @field_validator("msg")
    @classmethod
    def _validate_msg_(cls, v: str) -> str:
        return textwrap.dedent(v).strip()

    @model_validator(mode="after")
    def _post_init_(self) -> Self:
        # create summary if missing
        if not self.summary:
            first_sentence, *_ = self.msg.split("\n", 1)
            first_sentence, *_ = first_sentence.split(". ", 1)
            self.summary = first_sentence.rstrip(" .")

        return self

    @property
    def loc_path(self) -> str:
        """Return a JSONPath-like string representation of the `loc` field."""
        with io.StringIO() as buf:
            for part in self.loc:
                if isinstance(part, int):
                    buf.write(f"[{part}]")
                else:
                    buf.write(f".{part}")

            if path := buf.getvalue():
                return path

        return "."


class Extras(BaseModel):
    """Additional context supplied alongside a diagnosis."""

    file: Annotated[
        FilesystemMetadata | None,
        Field(
            default=None,
            description="Filesystem-level context (file path) for the manifest related to the diagnosis.",
        ),
    ]

    helm: Annotated[
        HelmMetadata | None,
        Field(
            default=None,
            description="Helm metadata (chart name and template path) for the manifest. Present only when Helm rendered the manifest.",
        ),
    ]

    manifest: Annotated[
        ManifestMetadata | None,
        Field(
            default=None,
            description="Manifest-level context (API version, name, file path) related to the diagnosis.",
        ),
    ]


class FilesystemMetadata(BaseModel):
    """Metadata describing the filesystem that supplied the manifest."""

    filepath: Annotated[
        str,
        Field(
            description="Filesystem path that supplied the manifest.",
        ),
    ]

    @property
    def is_stdin(self) -> bool:
        if self.filepath == "<stdin>":
            return True
        if os.path.realpath(self.filepath) == os.path.realpath("/dev/stdin"):
            return True
        return False


class HelmMetadata(BaseModel):
    """Metadata describing the Helm chart that produced the manifest."""

    chart: Annotated[
        str,
        Field(
            description="Name of the Helm chart that rendered this manifest.",
            examples=["my-chart"],
        ),
    ]

    template: Annotated[
        str,
        Field(
            description="Relative path in the chart to the template that emitted the manifest.",
            examples=[
                "templates/workflow.yaml",
            ],
        ),
    ]


class ManifestMetadata(BaseModel):
    """Metadata describing the manifest that produced the diagnosis."""

    group: Annotated[
        str,
        Field(
            description="Kubernetes API group (e.g., `argoproj.io` or ``). The empty string represents the core API group.",
        ),
    ]

    kind: Annotated[
        str,
        Field(
            description="Kubernetes kind.",
            examples=["Pod", "Workflow"],
        ),
    ]

    name: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Resource identifier taken from manifest metadata (`metadata.name` or `metadata.generateName`) to help locate the manifest."
            ),
        ),
    ]

    @property
    def fqk(self) -> str:
        """Return the fully qualified kind."""
        kind = self.kind.lower()
        if self.group:
            return f"{kind}.{self.group}"
        return kind

    @property
    def fqkn(self) -> str:
        """Return the fully qualified kind and name."""
        if not self.name:
            raise ValueError("name is not set")
        return f"{self.fqk}/{self.name}"


DiagnosisModel.model_rebuild()  # required for subclassing
