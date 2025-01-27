from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.basic import Array, ConfigKeySelector


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Probe(_BaseModel):
    exec: ExecAction | None = None
    failureThreshold: int | None = None
    grpc: GrpcAction | None = None
    httpGet: HttpGetAction | None = None
    initialDelaySeconds: int | None = None
    periodSeconds: int | None = None
    successThreshold: int | None = None
    tcpSocket: TcpSocketAction | None = None
    terminationGracePeriodSeconds: int | None = None
    timeoutSeconds: int | None = None


class ExecAction(_BaseModel):
    """
    `ExecAction`_ describes a "run in container" action.

    .. _ExecAction: https://argo-workflows.readthedocs.io/en/latest/fields/#execaction
    """

    command: Array[str]


class GrpcAction(_BaseModel):
    port: int
    service: str | None = None


class HttpGetAction(_BaseModel):
    """
    `HttpGetAction`_ describes an action based on HTTP Get requests.

    .. _HttpGetAction: https://argo-workflows.readthedocs.io/en/latest/fields/#httpgetaction
    """

    host: str | None = None
    httpHeaders: Array[HttpHeader] | None = None
    path: str
    port: int | str
    scheme: Literal["HTTP", "HTTPS"] | None = None


class HttpHeader(_BaseModel):
    name: str
    value: str | None = None
    valueFrom: HttpHeaderSource | None = None


class HttpHeaderSource(_BaseModel):
    secretKeyRef: ConfigKeySelector


class TcpSocketAction(_BaseModel):
    """
    `TcpSocketAction`_ describes an action based on opening a socket.

    .. _TcpSocketAction: https://argo-workflows.readthedocs.io/en/latest/fields/#tcpsocketaction
    """

    host: str | None = None
    port: int | str
