from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.basic import (
    ConfigMapKeySelector,
    Empty,
    KeyValuePair,
    NameValuePair,
    PodMetadata,
    SecretKeySelector,
)


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Artifact(_BaseModel):

    name: str

    archive: ArchiveStrategy | None = None
    archiveLogs: bool | None = None
    artifactGC: ArtifactGc | None = None
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
    passwordSecret: SecretKeySelector
    url: str
    usernameSecret: SecretKeySelector


# ----------------------------------------------------------------------------
# azure
# ----------------------------------------------------------------------------
class AzureArtifact(_BaseModel):
    accountKeySecret: SecretKeySelector
    blob: str
    container: str
    endpoint: str
    useSDKCreds: bool | None = None


# ----------------------------------------------------------------------------
# gcs
# ----------------------------------------------------------------------------
class GcsArtifact(_BaseModel):
    bucket: str
    key: str
    serviceAccountKeySecret: SecretKeySelector


# ----------------------------------------------------------------------------
# git
# ----------------------------------------------------------------------------
class GitArtifact(_BaseModel):
    branch: str | None = None
    depth: int | None = None
    disableSubmodules: bool | None = None
    fetch: list[str] | None = None
    insecureIgnoreHostKey: bool | None = None
    insecureSkipTLS: bool | None = None
    passwordSecret: SecretKeySelector | None = None
    repo: str
    revision: str | None = None
    singleBranch: bool | None = None
    sshPrivateKeySecret: SecretKeySelector | None = None
    usernameSecret: SecretKeySelector | None = None


# ----------------------------------------------------------------------------
# hdfs
# ----------------------------------------------------------------------------
class HdfsArtifact(_BaseModel):
    addresses: list[str]
    dataTransferProtection: str | None = None
    force: bool | None = None
    hdfsUser: str
    krbCCacheSecret: SecretKeySelector | None = None
    krbConfigConfigMap: ConfigMapKeySelector | None = None
    krbKeytabSecret: SecretKeySelector | None = None
    krbRealm: str | None = None
    krbServicePrincipalName: str | None = None
    krbUsername: str | None = None
    path: str


# ----------------------------------------------------------------------------
# http
# ----------------------------------------------------------------------------
class HttpArtifact(_BaseModel):
    auth: HttpAuth | None = None
    headers: list[NameValuePair] | None = None
    url: str


class BasicAuth(_BaseModel):
    passwordSecret: SecretKeySelector
    usernameSecret: SecretKeySelector


class ClientCertAuth(_BaseModel):
    clientCertSecret: SecretKeySelector | None = None
    clientKeySecret: SecretKeySelector


class HttpAuth(_BaseModel):
    basic: BasicAuth | None = None
    clientCert: ClientCertAuth | None = None
    oauth2: OAuth2Auth | None = None


class OAuth2Auth(_BaseModel):
    clientIDSecret: SecretKeySelector
    clientSecretSecret: SecretKeySelector
    endpointParams: list[KeyValuePair] | None = None
    scopes: list[str] | None = None
    tokenURLSecret: SecretKeySelector | None = None


# ----------------------------------------------------------------------------
# oss
# ----------------------------------------------------------------------------
class OssArtifact(_BaseModel):
    accessKeySecret: SecretKeySelector
    bucket: str
    createBucketIfNotPresent: bool | None = None
    endpoint: str
    key: str
    lifecycleRule: OssLifecycleRule | None = None
    secretKeySecret: SecretKeySelector
    securityToken: str | None = None
    useSDKCreds: bool | None = None


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
    accessKeySecret: SecretKeySelector | None = None
    bucket: str | None = None
    caSecret: SecretKeySelector | None = None
    createBucketIfNotPresent: CreateS3BucketOptions | None = None
    encryptionOptions: S3EncryptionOptions | None = None
    endpoint: str | None = None
    insecure: bool | None = None
    key: str
    region: str | None = None
    roleARN: str | None = None
    secretKeySecret: SecretKeySelector | None = None
    sessionTokenSecret: SecretKeySelector | None = None
    useSDKCreds: bool | None = None


class CreateS3BucketOptions(_BaseModel):
    objectLocking: bool


class S3EncryptionOptions(_BaseModel):
    enableEncryption: bool | None = None
    kmsEncryptionContext: str | None = None
    kmsKeyId: str | None = None
    serverSideCustomerKeySecret: SecretKeySelector | None = None
