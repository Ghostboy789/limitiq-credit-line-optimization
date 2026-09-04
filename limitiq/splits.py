"""Frozen development and untouched-test split shared by behavioral evidence."""

from __future__ import annotations

from typing import TypeVar

import pandas as pd
from sklearn.model_selection import train_test_split

from limitiq.config import SEED

FrameT = TypeVar("FrameT", bound=pd.DataFrame)
SeriesT = TypeVar("SeriesT", bound=pd.Series)


def frozen_split(
    features: FrameT, target: SeriesT
) -> tuple[tuple[FrameT, SeriesT], tuple[FrameT, SeriesT], tuple[FrameT, SeriesT]]:
    """Return the immutable 60%/20%/20% stratified behavioral partition."""
    train_x, holdout_x, train_y, holdout_y = train_test_split(
        features, target, test_size=0.4, stratify=target, random_state=SEED
    )
    validation_x, test_x, validation_y, test_y = train_test_split(
        holdout_x, holdout_y, test_size=0.5, stratify=holdout_y, random_state=SEED
    )
    return (train_x, train_y), (validation_x, validation_y), (test_x, test_y)
