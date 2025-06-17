from __future__ import annotations

import decimal
import operator
import os
import re
from typing import TYPE_CHECKING, Any, Literal

import pydantic_core.core_schema
from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.basic import Array
from tugboat.schemas.template.env import EnvFromSource, EnvVar
from tugboat.schemas.template.probe import Probe
from tugboat.schemas.template.volume import VolumeMount

if TYPE_CHECKING:
    from collections.abc import Callable
    from decimal import Decimal

    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema

if os.getenv("DOCUTILSCONFIG"):
    __all__ = [
        "ContainerSetRetryStrategy",
        "ContainerSetTemplate",
        "Quantity",
        "ResourceClaim",
        "ResourceQuantities",
        "ResourceRequirements",
    ]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _ContainerEntry(_BaseModel):

    command: Array[str] | None = None
    env: Array[EnvVar] | None = None
    envFrom: Array[EnvFromSource] | None = None
    image: str
    imagePullPolicy: Literal["Always", "Never", "IfNotPresent"] | None = None
    livenessProbe: Probe | None = None
    name: str | None = None
    readinessProbe: Probe | None = None
    resources: ResourceRequirements | None = None
    restartPolicy: Literal["Always"] | None = None
    startupProbe: Probe | None = None
    stdin: bool | None = None
    stdinOnce: bool | None = None
    terminationMessagePath: str | None = None
    terminationMessagePolicy: Literal["File", "FallbackToLogsOnError"] | None = None
    tty: bool | None = None
    volumeMounts: Array[VolumeMount] | None = None
    workingDir: str | None = None

    lifecycle: Any | None = None
    ports: Array[Any] | None = None
    resizePolicy: Array[Any] | None = None
    securityContext: Any | None = None
    volumeDevices: Array[Any] | None = None


class ContainerTemplate(_ContainerEntry):
    """
    A single application `container`_ that you want to run within a pod.

    .. _container: https://argo-workflows.readthedocs.io/en/latest/fields/#container
    """

    args: Array[str] | None = None

    def __hash__(self):
        return hash((self.image, self.command, self.args))


class ScriptTemplate(_ContainerEntry):
    """
    `ScriptTemplate`_ is a template subtype to enable scripting through code steps.

    .. _ScriptTemplate: https://argo-workflows.readthedocs.io/en/latest/fields/#scripttemplate
    """

    source: str

    def __hash__(self):
        return hash((self.image, self.source))


class ContainerNode(_ContainerEntry):
    """
    Represents an individual `ContainerNode`_ within a `ContainerSetTemplate`_.

    .. _ContainerNode:
       https://argo-workflows.readthedocs.io/en/latest/fields/#containernode
    .. _ContainerSetTemplate:
       https://argo-workflows.readthedocs.io/en/latest/fields/#containersettemplate
    """

    args: Array[str] | None = None
    dependencies: Array[str] | None = None

    def __hash__(self):
        return hash((self.image, self.command, self.args))


class ContainerSetTemplate(_BaseModel):
    """
    `ContainerSetTemplate`_ to specify multiple containers to run within a single pod.

    .. _ContainerSetTemplate:
       https://argo-workflows.readthedocs.io/en/latest/fields/#containersettemplate
    """

    containers: Array[ContainerNode]
    retryStrategy: ContainerSetRetryStrategy | None = None
    volumeMounts: Array[VolumeMount] | None = None


class ContainerSetRetryStrategy(_BaseModel):
    duration: str | None = Field(None, pattern=r"\d+(ns|us|µs|ms|s|m|h)")
    retries: int | str


class ResourceRequirements(_BaseModel):
    """
    `ResourceRequirements`_ describes the compute resource requirements.

    .. _ResourceRequirements:
       https://argo-workflows.readthedocs.io/en/latest/fields/#resourcerequirements
    """

    claims: Array[ResourceClaim] | None = None
    limits: ResourceQuantities | None = None
    requests: ResourceQuantities | None = None


class ResourceClaim(_BaseModel):
    """
    `ResourceClaim`_ references one entry in PodSpec.ResourceClaims.

    .. _ResourceClaim: https://argo-workflows.readthedocs.io/en/latest/fields/#resourceclaim
    """

    name: str
    request: str | None = None


class ResourceQuantities(_BaseModel):
    """
    ResourceQuantity is a class to represent resource quantities in Kubernetes.
    """

    cpu: Quantity | None = None
    memory: Quantity | None = None


class Quantity:
    """
    `Quantity`_ is a fixed-point representation of a number.

    .. _Quantity: https://kubernetes.io/docs/reference/kubernetes-api/common-definitions/quantity/#Quantity
    """

    expr: str
    value: decimal.Decimal

    def __init__(self, expr: str) -> None:
        expr = expr.strip()

        if m := re.search(r"(Ki|Mi|Gi|Ti|Pi|Ei|m|k|M|G|T|P|E)$", expr):
            num = expr[: m.start()]
            suffix = m.group(0)

            multiplier = {
                "Ki": 1024,
                "Mi": 1024**2,
                "Gi": 1024**3,
                "Ti": 1024**4,
                "Pi": 1024**5,
                "Ei": 1024**6,
                "m": decimal.Decimal("0.001"),
                "k": 1000,
                "M": 1_000_000,
                "G": 1_000_000_000,
                "T": 1_000_000_000_000,
                "P": 1_000_000_000_000_000,
                "E": 1_000_000_000_000_000_000,
            }[suffix]

        else:
            num = expr
            multiplier = 1

        try:
            dec = decimal.Decimal(num)
        except decimal.InvalidOperation:
            raise ValueError("Invalid decimal quantity") from None

        dec *= multiplier
        assert isinstance(dec, decimal.Decimal)  # satisfy type checker

        # it may not have more than 3 decimal places
        dec = dec.quantize(decimal.Decimal("0.001"), rounding=decimal.ROUND_UP)

        # this class is only used for cpu and memory quantities, which must be non-negative
        if dec < 0:
            raise ValueError("Quantity must be non-negative")

        self.expr = expr
        self.value = dec

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:

        def _validator(v: Any):
            if isinstance(v, int | float):
                v = str(v)
            if isinstance(v, str):
                v = cls(v)
            return v

        python_schema = pydantic_core.core_schema.no_info_before_validator_function(
            _validator, pydantic_core.core_schema.is_instance_schema(cls)
        )
        json_schema = pydantic_core.core_schema.no_info_after_validator_function(
            str, pydantic_core.core_schema.str_schema()
        )
        return pydantic_core.core_schema.json_or_python_schema(
            python_schema=python_schema,
            json_schema=json_schema,
            serialization=pydantic_core.core_schema.to_string_ser_schema(),
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.expr})"

    def __str__(self) -> str:
        return self.expr

    def __hash__(self) -> int:
        return hash(self.value)

    def _compare(self, other: Any, method: Callable[[Decimal, Decimal], bool]) -> bool:
        if isinstance(other, type(self)):
            return method(self.value, other.value)
        raise TypeError

    def __lt__(self, other) -> bool:
        return self._compare(other, operator.lt)

    def __le__(self, other) -> bool:
        return self._compare(other, operator.le)

    def __eq__(self, other) -> bool:
        return self._compare(other, operator.eq)

    def __ge__(self, other) -> bool:
        return self._compare(other, operator.ge)

    def __gt__(self, other) -> bool:
        return self._compare(other, operator.gt)

    def __ne__(self, other) -> bool:
        return self._compare(other, operator.ne)
