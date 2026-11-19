from ..emailSchemas import EmailRequest

class MockProvider:
    name = "mock"
    isMock = True

    def improve(self, request: EmailRequest) -> str:
        # Only paragraph spacing changes; no fabricated rewrite or semantic assessment.
        return "\n\n".join(line.strip() for line in request.originalDraft.splitlines() if line.strip())
