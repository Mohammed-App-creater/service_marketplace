"""Abstract provider interfaces.

All business code depends on these interfaces, never on a concrete provider.
Swapping in Twilio / FCM / Channels later is a settings-only change (see factory).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ProviderResult:
    success: bool
    provider_ref: str = ""
    detail: str = ""
    meta: dict = field(default_factory=dict)


class SMSProvider(ABC):
    @abstractmethod
    def send(self, to: str, message: str, *, context: dict | None = None) -> ProviderResult: ...


class EmailProvider(ABC):
    @abstractmethod
    def send(
        self, to: str, subject: str, message: str, *, context: dict | None = None
    ) -> ProviderResult: ...


class PushProvider(ABC):
    @abstractmethod
    def send(
        self, tokens: list[str], title: str, body: str, *, data: dict | None = None
    ) -> ProviderResult: ...


class RealtimeProvider(ABC):
    @abstractmethod
    def publish(self, channel: str, event: str, payload: dict) -> ProviderResult: ...
