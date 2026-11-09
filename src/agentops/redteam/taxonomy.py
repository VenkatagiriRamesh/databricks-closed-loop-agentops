"""Attack categories and the Attack record."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Category = Literal['direct_injection', 'indirect_injection', 'authority_bypass', 'pii_exfiltration',
                   'sql_abuse', 'scope_jailbreak']
CATEGORIES: tuple[str, ...] = ('direct_injection', 'indirect_injection', 'authority_bypass',
                               'pii_exfiltration', 'sql_abuse', 'scope_jailbreak')


@dataclass
class Attack:
    id: str
    category: str
    prompt: str
    turns: list[str] = field(default_factory=list)
    claim_id: str | None = None
    mutation: str = 'none'
    source: Literal['llm', 'seed'] = 'llm'
    forbidden_phrases: list[str] = field(default_factory=list)
