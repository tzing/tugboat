from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.basic import (
    Array,
    ConfigKeySelector,
    Empty,
    KeyValuePair,
    NameValuePair,
    PodMetadata,
)

if os.getenv("DOCUTILSCONFIG"):
    __all__ = [
        "ArchiveStrategy",
        "ArtifactGc",
        "ArtifactoryArtifact",
        "AzureArtifact",
        "BasicAuth",
        "ClientCertAuth",
        "CreateS3BucketOptions",
        "GcsArtifact",
        "GitArtifact",
        "HdfsArtifact",
        "HttpArtifact",
        "HttpAuth",
        "OAuth2Auth",
        "OssArtifact",
        "OssLifecycleRule",
        "RawArtifact",
        "S3Artifact",
        "S3EncryptionOptions",
        "TarStrategy",
    ]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Artifact(_BaseModel):

    name: str

    archive: ArchiveStrategy | None = None
    archiveLogs: bool | None = None
    artifactGc: ArtifactGc | None = Field(None, alias="artifactGC")
    artifactory: ArtifactoryArtifact | None = None
    azure: AzureArtifact | None = None
    deleted: bool | None = None
    from_: str | None = Field(None, alias="from")
    fromExpression: str | None = None
    gcs: GcsArtifact | None = None
    git: GitArtifact | None = None
    globalName: str | None = None
    hdfs: HdfsArtifact | None = None
    http: HttpArtifact | None = None
    mode: int | None = None
    optional: bool = False
    oss: OssArtifact | None = None
    path: str | None = None
    raw: RawArtifact | None = None
    recurseMode: bool | None = None
    s3: S3Artifact | None = None
    subPath: str | None = None


# ----------------------------------------------------------------------------
# archive
# ----------------------------------------------------------------------------
class ArchiveStrategy(_BaseModel):
    none: Empty | None = None
    tar: TarStrategy | None = None
    zip: Empty | None = None


class TarStrategy(_BaseModel):
    compressionLevel: int | None = None


# ----------------------------------------------------------------------------
# artifactGC
# ----------------------------------------------------------------------------
class ArtifactGc(_BaseModel):
    podMetadata: PodMetadata | None = None
    serviceAccountName: str | None = None
    strategy: str


# ----------------------------------------------------------------------------
# artifactory
# ----------------------------------------------------------------------------
class ArtifactoryArtifact(_BaseModel):
    passwordSecret: ConfigKeySelector
    url: str
    usernameSecret: ConfigKeySelector


# ----------------------------------------------------------------------------
# azure
# ----------------------------------------------------------------------------
class AzureArtifact(_BaseModel):
    accountKeySecret: ConfigKeySelector
    blob: str
    container: str
    endpoint: str
    useSdkCreds: bool | None = Field(None, alias="useSDKCreds")


# ----------------------------------------------------------------------------
# gcs
# ----------------------------------------------------------------------------
class GcsArtifact(_BaseModel):
    bucket: str
    key: str
    serviceAccountKeySecret: ConfigKeySelector


# ----------------------------------------------------------------------------
# git
# ----------------------------------------------------------------------------
class GitArtifact(_BaseModel):
    branch: str | None = None
    depth: int | None = None
    disableSubmodules: bool | None = None
    fetch: Array[str] | None = None
    insecureIgnoreHostKey: bool | None = None
    insecureSkipTls: bool | None = Field(None, alias="insecureSkipTLS")
    passwordSecret: ConfigKeySelector | None = None
    repo: str
    revision: str | None = None
    singleBranch: bool | None = None
    sshPrivateKeySecret: ConfigKeySelector | None = None
    usernameSecret: ConfigKeySelector | None = None


# ----------------------------------------------------------------------------
# hdfs
# ----------------------------------------------------------------------------
class HdfsArtifact(_BaseModel):
    addresses: Array[str]
    dataTransferProtection: str | None = None
    force: bool | None = None
    hdfsUser: str
    krbCCacheSecret: ConfigKeySelector | None = None
    krbConfigConfigMap: ConfigKeySelector | None = None
    krbKeytabSecret: ConfigKeySelector | None = None
    krbRealm: str | None = None
    krbServicePrincipalName: str | None = None
    krbUsername: str | None = None
    path: str


# ----------------------------------------------------------------------------
# http
# ----------------------------------------------------------------------------
class HttpArtifact(_BaseModel):
    auth: HttpAuth | None = None
    headers: Array[NameValuePair] | None = None
    url: str


class BasicAuth(_BaseModel):
    passwordSecret: ConfigKeySelector
    usernameSecret: ConfigKeySelector


class ClientCertAuth(_BaseModel):
    clientCertSecret: ConfigKeySelector | None = None
    clientKeySecret: ConfigKeySelector


class HttpAuth(_BaseModel):
    basic: BasicAuth | None = None
    clientCert: ClientCertAuth | None = None
    oauth2: OAuth2Auth | None = None


class OAuth2Auth(_BaseModel):
    clientIdSecret: ConfigKeySelector = Field(alias="clientIDSecret")
    clientSecretSecret: ConfigKeySelector
    endpointParams: Array[KeyValuePair] | None = None
    scopes: Array[str] | None = None
    tokenUrlSecret: ConfigKeySelector | None = Field(None, alias="tokenURLSecret")


# ----------------------------------------------------------------------------
# oss
# ----------------------------------------------------------------------------
class OssArtifact(_BaseModel):
    accessKeySecret: ConfigKeySelector
    bucket: str
    createBucketIfNotPresent: bool | None = None
    endpoint: str
    key: str
    lifecycleRule: OssLifecycleRule | None = None
    secretKeySecret: ConfigKeySelector
    securityToken: str | None = None
    useSdkCreds: bool | None = Field(None, alias="useSDKCreds")


class OssLifecycleRule(_BaseModel):
    markDeletionAfterDays: int | None = None
    markInfrequentAccessAfterDays: int | None = None


# ----------------------------------------------------------------------------
# raw
# ----------------------------------------------------------------------------
class RawArtifact(_BaseModel):
    data: str


# ----------------------------------------------------------------------------
# s3
# ----------------------------------------------------------------------------
class S3Artifact(_BaseModel):
    accessKeySecret: ConfigKeySelector | None = None
    bucket: str | None = None
    caSecret: ConfigKeySelector | None = None
    createBucketIfNotPresent: CreateS3BucketOptions | None = None
    encryptionOptions: S3EncryptionOptions | None = None
    endpoint: str | None = None
    insecure: bool | None = None
    key: str
    region: str | None = None
    roleArn: str | None = Field(None, alias="roleARN")
    secretKeySecret: ConfigKeySelector | None = None
    sessionTokenSecret: ConfigKeySelector | None = None
    useSdkCreds: bool | None = Field(None, alias="useSDKCreds")


class CreateS3BucketOptions(_BaseModel):
    objectLocking: bool


class S3EncryptionOptions(_BaseModel):
    enableEncryption: bool | None = None
    kmsEncryptionContext: str | None = None
    kmsKeyId: str | None = None
    serverSideCustomerKeySecret: ConfigKeySelector | None = None
