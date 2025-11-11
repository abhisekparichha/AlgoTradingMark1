from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple


@dataclass
class EntityLinker:
    """
    Maps extracted entity names to tradable symbols using a provided dictionary.
    """

    name_to_symbol: Dict[str, str] = field(default_factory=dict)

    def link(self, text: str) -> List[str]:
        tokens = [token.strip(",.") for token in text.split()]
        matches = {self.name_to_symbol[token.upper()] for token in tokens if token.upper() in self.name_to_symbol}
        return sorted(matches)

    @classmethod
    def from_mappings(cls, mappings: Iterable[Tuple[str, str]]) -> "EntityLinker":
        mapping_dict = {name.upper(): symbol for name, symbol in mappings}
        return cls(name_to_symbol=mapping_dict)
