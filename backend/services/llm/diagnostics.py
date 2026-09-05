from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderDiagnostic:
    category: str
    message: str
    http_status: int | None = None

    def as_safe_dict(self) -> dict:
        return {
            "category": self.category,
            "http_status": self.http_status,
            "message": self.message,
        }


class ProviderRequestError(Exception):
    def __init__(self, diagnostic: ProviderDiagnostic):
        super().__init__(diagnostic.category)
        self.diagnostic = diagnostic
