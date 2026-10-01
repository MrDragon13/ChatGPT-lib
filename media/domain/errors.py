from __future__ import annotations

from typing import Any, Mapping


class MediaDomainError(Exception):
    """Base class for media domain/service errors."""


class CommandValidationError(MediaDomainError):
    pass


class NotFoundError(MediaDomainError):
    pass


class UnknownTargetError(MediaDomainError):
    pass


class AmbiguousIdentityError(MediaDomainError):
    def __init__(self, candidates: tuple[object, ...]):
        super().__init__("ambiguous media identity")
        self.candidates = candidates


class MetadataRefreshPreflightError(MediaDomainError):
    def __init__(self, blockers: tuple[Mapping[str, Any], ...]):
        super().__init__("metadata refresh preflight failed")
        self.blockers = blockers


class ProviderUnavailableError(MediaDomainError):
    pass


class ConflictError(MediaDomainError):
    pass


class TransactionValidationError(MediaDomainError):
    pass


class PathPolicyError(MediaDomainError):
    pass
