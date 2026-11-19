from typing import Protocol
from ..emailSchemas import EmailRequest, ValidationRequest, SemanticReport

class ProviderUnavailable(Exception):
    pass

class ModelProvider(Protocol):
    name: str
    isMock: bool
    def improve(self, request: EmailRequest) -> str: ...

class SemanticReviewer(Protocol):
    def reviewMeaning(self, request: ValidationRequest) -> SemanticReport: ...
