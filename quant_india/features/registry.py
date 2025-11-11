from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

import pandas as pd

FeatureFunction = Callable[[pd.DataFrame], pd.DataFrame]


@dataclass
class FeatureDefinition:
    name: str
    description: str
    function: FeatureFunction
    inputs: List[str]
    tags: List[str]


REGISTRY: Dict[str, FeatureDefinition] = {}


def register_feature(
    name: str,
    description: str,
    inputs: Optional[Iterable[str]] = None,
    tags: Optional[Iterable[str]] = None,
) -> Callable[[FeatureFunction], FeatureFunction]:
    def decorator(func: FeatureFunction) -> FeatureFunction:
        REGISTRY[name] = FeatureDefinition(
            name=name,
            description=description,
            function=func,
            inputs=list(inputs or []),
            tags=list(tags or []),
        )
        return func

    return decorator


def get_feature(name: str) -> FeatureDefinition:
    if name not in REGISTRY:
        raise KeyError(f"Feature {name} not registered")
    return REGISTRY[name]


def list_features(tags: Optional[Iterable[str]] = None) -> List[FeatureDefinition]:
    if tags is None:
        return list(REGISTRY.values())
    tags_set = set(tags)
    return [definition for definition in REGISTRY.values() if tags_set.intersection(definition.tags)]
