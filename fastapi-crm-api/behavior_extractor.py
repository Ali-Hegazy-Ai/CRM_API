"""
Behavior extraction utilities for schema-agnostic randomness modeling.

This module intentionally learns only abstract behavior from CSV data:
- entropy / variability
- distribution shape tendencies
- temporal burst/idle behavior
- soft dependency strength
- imperfection rates (missing, outliers, format noise)

It does NOT map source columns to target CRM schema.
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BEHAVIOR_PROFILE: Dict[str, Any] = {
    "rows_analyzed": 0,
    "missing_rate": 0.08,
    "entropy_mean": 0.62,
    "uniqueness_mean": 0.54,
    "repetition_mean": 0.46,
    "distribution": {
        "uniform_ratio": 0.20,
        "normal_ratio": 0.40,
        "long_tail_ratio": 0.40,
        "imbalance_score": 0.42,
    },
    "temporal": {
        "burst_rate": 0.18,
        "idle_rate": 0.14,
        "gap_irregularity": 0.58,
    },
    "dependency_strength": 0.38,
    "imperfection": {
        "outlier_rate": 0.04,
        "format_noise": 0.12,
        "noise_level": 0.11,
    },
    "irregularity_score": 0.44,
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(text: str) -> Optional[float]:
    if text is None:
        return None

    value = str(text).strip()
    if not value:
        return None

    # Keep parsing conservative to avoid accidental coercion.
    candidate = value.replace(",", "")
    try:
        number = float(candidate)
    except ValueError:
        return None

    if math.isnan(number) or math.isinf(number):
        return None
    return number


_DATE_PATTERNS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
]


def _parse_datetime(value: str) -> Optional[datetime]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # Fast-path ISO handling.
    try:
        normalized = text.replace("Z", "+00:00") if text.endswith("Z") else text
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for pattern in _DATE_PATTERNS:
        try:
            parsed = datetime.strptime(text, pattern)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def _quantile(sorted_values: List[float], q: float) -> float:
    if not sorted_values:
        return 0.0

    if len(sorted_values) == 1:
        return float(sorted_values[0])

    index = (len(sorted_values) - 1) * q
    low = int(math.floor(index))
    high = int(math.ceil(index))

    if low == high:
        return float(sorted_values[low])

    left = sorted_values[low]
    right = sorted_values[high]
    ratio = index - low
    return float(left + (right - left) * ratio)


def _shannon_entropy_ratio(counts: Counter) -> float:
    total = sum(counts.values())
    unique = len(counts)

    if total <= 0 or unique <= 1:
        return 0.0

    entropy = 0.0
    for value_count in counts.values():
        p = value_count / total
        if p > 0:
            entropy -= p * math.log2(p)

    max_entropy = math.log2(unique)
    if max_entropy <= 0:
        return 0.0

    return _clamp(entropy / max_entropy, 0.0, 1.0)


def _pattern_signature(value: str) -> str:
    text = str(value).strip()
    if not text:
        return "empty"

    has_digit = False
    has_alpha = False
    has_space = False
    has_symbol = False
    is_upper = text.upper() == text and any(ch.isalpha() for ch in text)
    is_lower = text.lower() == text and any(ch.isalpha() for ch in text)
    is_title = text.title() == text and any(ch.isalpha() for ch in text)

    for ch in text:
        if ch.isdigit():
            has_digit = True
        elif ch.isalpha():
            has_alpha = True
        elif ch.isspace():
            has_space = True
        else:
            has_symbol = True

    token = []
    if has_alpha:
        token.append("A")
    if has_digit:
        token.append("N")
    if has_space:
        token.append("S")
    if has_symbol:
        token.append("P")

    if is_upper:
        token.append("UP")
    elif is_lower:
        token.append("LOW")
    elif is_title:
        token.append("TTL")
    else:
        token.append("MIX")

    return "-".join(token)


def _pearson_abs(x_values: List[float], y_values: List[float]) -> Optional[float]:
    if len(x_values) < 3 or len(y_values) < 3 or len(x_values) != len(y_values):
        return None

    mean_x = statistics.mean(x_values)
    mean_y = statistics.mean(y_values)

    numerator = 0.0
    sum_x = 0.0
    sum_y = 0.0

    for x, y in zip(x_values, y_values):
        dx = x - mean_x
        dy = y - mean_y
        numerator += dx * dy
        sum_x += dx * dx
        sum_y += dy * dy

    denominator = math.sqrt(sum_x * sum_y)
    if denominator <= 0:
        return None

    corr = numerator / denominator
    return abs(_clamp(corr, -1.0, 1.0))


def _categorical_dependency(pairs: List[Tuple[str, str]]) -> Optional[float]:
    if len(pairs) < 6:
        return None

    buckets: Dict[str, Counter] = defaultdict(Counter)
    for left, right in pairs:
        if not left or not right:
            continue
        buckets[left][right] += 1

    if not buckets:
        return None

    weighted_sum = 0.0
    total_weight = 0

    for counter in buckets.values():
        subtotal = sum(counter.values())
        if subtotal <= 0:
            continue
        dominant = max(counter.values())
        weighted_sum += (dominant / subtotal) * subtotal
        total_weight += subtotal

    if total_weight <= 0:
        return None

    return _clamp(weighted_sum / total_weight, 0.0, 1.0)


def extract_behavior_profile(csv_path: str, max_rows: int = 25000) -> Dict[str, Any]:
    """Extract schema-agnostic behavior metrics from a CSV file."""
    if not csv_path:
        return dict(DEFAULT_BEHAVIOR_PROFILE)

    rows: List[Dict[str, str]] = []
    field_names: List[str] = []

    try:
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as file_handle:
            reader = csv.DictReader(file_handle)
            if reader.fieldnames:
                field_names = [str(name) for name in reader.fieldnames if name]

            for index, row in enumerate(reader):
                if index >= max_rows:
                    break
                rows.append(row)
    except OSError:
        return dict(DEFAULT_BEHAVIOR_PROFILE)

    if not rows or not field_names:
        return dict(DEFAULT_BEHAVIOR_PROFILE)

    row_count = len(rows)
    missing_rates: List[float] = []
    entropy_scores: List[float] = []
    uniqueness_scores: List[float] = []
    repetition_scores: List[float] = []
    imbalance_scores: List[float] = []
    outlier_rates: List[float] = []
    format_noise_scores: List[float] = []
    temporal_burst_scores: List[float] = []
    temporal_idle_scores: List[float] = []
    temporal_irregularity_scores: List[float] = []

    uniform_like_count = 0
    normal_like_count = 0
    long_tail_like_count = 0
    numeric_series_count = 0

    # Used later for dependency calculations.
    numeric_fields: List[str] = []
    categorical_fields: List[str] = []

    for field_name in field_names:
        values: List[str] = []
        non_empty_numeric: List[float] = []
        parsed_datetimes: List[datetime] = []
        pattern_counter: Counter = Counter()

        missing_count = 0

        for row in rows:
            raw_value = row.get(field_name)
            text = "" if raw_value is None else str(raw_value).strip()

            if not text:
                missing_count += 1
                continue

            values.append(text)

            parsed_float = _safe_float(text)
            if parsed_float is not None:
                non_empty_numeric.append(parsed_float)

            parsed_dt = _parse_datetime(text)
            if parsed_dt is not None:
                parsed_datetimes.append(parsed_dt)

            pattern_counter[_pattern_signature(text)] += 1

        missing_rate = missing_count / row_count
        missing_rates.append(missing_rate)

        if not values:
            entropy_scores.append(0.0)
            uniqueness_scores.append(0.0)
            repetition_scores.append(1.0)
            imbalance_scores.append(1.0)
            format_noise_scores.append(0.0)
            continue

        counts = Counter(values)
        unique_ratio = len(counts) / len(values)
        entropy_ratio = _shannon_entropy_ratio(counts)
        repetition_ratio = 1.0 - unique_ratio
        top_share = max(counts.values()) / len(values)

        uniqueness_scores.append(_clamp(unique_ratio, 0.0, 1.0))
        entropy_scores.append(_clamp(entropy_ratio, 0.0, 1.0))
        repetition_scores.append(_clamp(repetition_ratio, 0.0, 1.0))
        imbalance_scores.append(_clamp(top_share, 0.0, 1.0))

        dominant_pattern_share = max(pattern_counter.values()) / len(values)
        signature_variety = len(pattern_counter)
        format_noise = (1.0 - dominant_pattern_share) * _clamp(signature_variety / 6.0, 0.1, 1.0)
        format_noise_scores.append(_clamp(format_noise, 0.0, 1.0))

        numeric_ratio = len(non_empty_numeric) / len(values)
        if len(non_empty_numeric) >= 20 and numeric_ratio >= 0.65:
            numeric_fields.append(field_name)
            numeric_series_count += 1
            sorted_values = sorted(non_empty_numeric)

            q10 = _quantile(sorted_values, 0.10)
            q25 = _quantile(sorted_values, 0.25)
            q50 = _quantile(sorted_values, 0.50)
            q75 = _quantile(sorted_values, 0.75)
            q90 = _quantile(sorted_values, 0.90)

            spread = max(sorted_values) - min(sorted_values)
            iqr = q75 - q25
            low_fence = q25 - (1.5 * iqr)
            high_fence = q75 + (1.5 * iqr)

            outlier_count = 0
            for value in sorted_values:
                if value < low_fence or value > high_fence:
                    outlier_count += 1

            outlier_rates.append(outlier_count / len(sorted_values))

            if spread > 0:
                middle_fraction = iqr / spread
                lower_half = max(q50 - q10, 1e-9)
                upper_half = max(q90 - q50, 1e-9)
                tail_ratio = upper_half / lower_half

                if tail_ratio > 2.2 or (abs(q90) > abs(q50) * 4.0 and abs(q50) > 1e-9):
                    long_tail_like_count += 1
                elif 0.42 <= middle_fraction <= 0.58:
                    uniform_like_count += 1
                else:
                    normal_like_count += 1

        else:
            if len(values) >= 20:
                categorical_fields.append(field_name)

        if len(parsed_datetimes) >= 8 and (len(parsed_datetimes) / len(values)) >= 0.50:
            parsed_datetimes.sort()
            gaps: List[float] = []

            for idx in range(1, len(parsed_datetimes)):
                delta = (parsed_datetimes[idx] - parsed_datetimes[idx - 1]).total_seconds()
                if delta > 0:
                    gaps.append(delta)

            if gaps:
                sorted_gaps = sorted(gaps)
                mean_gap = statistics.mean(sorted_gaps)
                std_gap = statistics.pstdev(sorted_gaps) if len(sorted_gaps) > 1 else 0.0
                p25 = _quantile(sorted_gaps, 0.25)
                p75 = _quantile(sorted_gaps, 0.75)

                burst_count = 0
                idle_count = 0

                for gap in sorted_gaps:
                    if gap <= max(1.0, p25 * 0.55):
                        burst_count += 1
                    if gap >= max(1.0, p75 * 1.8):
                        idle_count += 1

                temporal_burst_scores.append(burst_count / len(sorted_gaps))
                temporal_idle_scores.append(idle_count / len(sorted_gaps))

                if mean_gap > 0:
                    temporal_irregularity_scores.append(_clamp(std_gap / mean_gap, 0.0, 3.0) / 3.0)

    # Dependency strength estimation.
    numeric_corr_scores: List[float] = []
    selected_numeric_fields = numeric_fields[:8]
    for left, right in combinations(selected_numeric_fields, 2):
        x_values: List[float] = []
        y_values: List[float] = []

        for row in rows:
            x = _safe_float(row.get(left))
            y = _safe_float(row.get(right))
            if x is None or y is None:
                continue
            x_values.append(x)
            y_values.append(y)

        corr = _pearson_abs(x_values, y_values)
        if corr is not None:
            numeric_corr_scores.append(corr)

    categorical_dep_scores: List[float] = []
    selected_categorical_fields = categorical_fields[:8]
    for left, right in combinations(selected_categorical_fields, 2):
        pair_values: List[Tuple[str, str]] = []

        for row in rows:
            left_value = row.get(left)
            right_value = row.get(right)

            left_text = "" if left_value is None else str(left_value).strip()
            right_text = "" if right_value is None else str(right_value).strip()
            if not left_text or not right_text:
                continue

            pair_values.append((left_text, right_text))

        dep = _categorical_dependency(pair_values)
        if dep is not None:
            categorical_dep_scores.append(dep)

    dependency_strength = 0.0
    dep_parts = []
    if numeric_corr_scores:
        dep_parts.append(statistics.mean(numeric_corr_scores))
    if categorical_dep_scores:
        # Categorical dependency tends to run high; dampen it slightly.
        dep_parts.append(statistics.mean(categorical_dep_scores) * 0.85)

    if dep_parts:
        dependency_strength = _clamp(statistics.mean(dep_parts), 0.0, 1.0)

    outlier_rate_mean = statistics.mean(outlier_rates) if outlier_rates else 0.03
    format_noise_mean = statistics.mean(format_noise_scores) if format_noise_scores else 0.10

    burst_rate_mean = statistics.mean(temporal_burst_scores) if temporal_burst_scores else 0.15
    idle_rate_mean = statistics.mean(temporal_idle_scores) if temporal_idle_scores else 0.12
    gap_irregularity_mean = statistics.mean(temporal_irregularity_scores) if temporal_irregularity_scores else 0.50

    if numeric_series_count <= 0:
        uniform_ratio = 0.20
        normal_ratio = 0.40
        long_tail_ratio = 0.40
    else:
        uniform_ratio = uniform_like_count / numeric_series_count
        normal_ratio = normal_like_count / numeric_series_count
        long_tail_ratio = long_tail_like_count / numeric_series_count

    missing_rate_mean = statistics.mean(missing_rates) if missing_rates else 0.0
    entropy_mean = statistics.mean(entropy_scores) if entropy_scores else 0.0
    uniqueness_mean = statistics.mean(uniqueness_scores) if uniqueness_scores else 0.0
    repetition_mean = statistics.mean(repetition_scores) if repetition_scores else 1.0
    imbalance_mean = statistics.mean(imbalance_scores) if imbalance_scores else 0.5

    noise_level = _clamp(
        (missing_rate_mean * 0.45) + (outlier_rate_mean * 0.30) + (format_noise_mean * 0.25),
        0.0,
        1.0,
    )

    irregularity_score = _clamp(
        (gap_irregularity_mean * 0.45)
        + (long_tail_ratio * 0.25)
        + (imbalance_mean * 0.20)
        + (format_noise_mean * 0.10),
        0.0,
        1.0,
    )

    return {
        "rows_analyzed": row_count,
        "missing_rate": _clamp(missing_rate_mean, 0.0, 1.0),
        "entropy_mean": _clamp(entropy_mean, 0.0, 1.0),
        "uniqueness_mean": _clamp(uniqueness_mean, 0.0, 1.0),
        "repetition_mean": _clamp(repetition_mean, 0.0, 1.0),
        "distribution": {
            "uniform_ratio": _clamp(uniform_ratio, 0.0, 1.0),
            "normal_ratio": _clamp(normal_ratio, 0.0, 1.0),
            "long_tail_ratio": _clamp(long_tail_ratio, 0.0, 1.0),
            "imbalance_score": _clamp(imbalance_mean, 0.0, 1.0),
        },
        "temporal": {
            "burst_rate": _clamp(burst_rate_mean, 0.0, 1.0),
            "idle_rate": _clamp(idle_rate_mean, 0.0, 1.0),
            "gap_irregularity": _clamp(gap_irregularity_mean, 0.0, 1.0),
        },
        "dependency_strength": dependency_strength,
        "imperfection": {
            "outlier_rate": _clamp(outlier_rate_mean, 0.0, 1.0),
            "format_noise": _clamp(format_noise_mean, 0.0, 1.0),
            "noise_level": noise_level,
        },
        "irregularity_score": irregularity_score,
    }


def profile_to_generation_knobs(profile: Dict[str, Any]) -> Dict[str, float]:
    distribution = profile.get("distribution", {})
    temporal = profile.get("temporal", {})
    imperfection = profile.get("imperfection", {})

    long_tail_ratio = float(distribution.get("long_tail_ratio", 0.4))
    imbalance = float(distribution.get("imbalance_score", 0.4))
    burst_rate = float(temporal.get("burst_rate", 0.15))
    idle_rate = float(temporal.get("idle_rate", 0.12))
    gap_irregularity = float(temporal.get("gap_irregularity", 0.5))
    dependency = float(profile.get("dependency_strength", 0.35))
    missing_rate = float(profile.get("missing_rate", 0.08))
    outlier_rate = float(imperfection.get("outlier_rate", 0.03))
    noise_level = float(imperfection.get("noise_level", 0.10))

    return {
        "burst_chance": _clamp(0.07 + (burst_rate * 0.52), 0.05, 0.80),
        "silence_chance": _clamp(0.04 + (idle_rate * 0.55), 0.03, 0.60),
        "missing_field_chance": _clamp(0.02 + (missing_rate * 0.95), 0.02, 0.45),
        "format_noise_chance": _clamp(0.03 + (noise_level * 1.05), 0.03, 0.50),
        "outlier_chance": _clamp(0.01 + (outlier_rate * 1.30) + (long_tail_ratio * 0.10), 0.01, 0.40),
        "long_tail_strength": _clamp(0.30 + (long_tail_ratio * 0.65), 0.25, 0.95),
        "activity_skew": _clamp(0.45 + (imbalance * 0.45) + (long_tail_ratio * 0.10), 0.45, 0.98),
        "dependency_strength": _clamp(dependency, 0.05, 0.95),
        "irregularity": _clamp((gap_irregularity * 0.6) + (noise_level * 0.4), 0.05, 0.95),
    }


def profile_to_stream_settings(profile: Dict[str, Any]) -> Dict[str, float]:
    knobs = profile_to_generation_knobs(profile)

    return {
        "burst_probability": knobs["burst_chance"],
        "silence_probability": knobs["silence_chance"],
        "out_of_order_probability": _clamp(0.02 + (knobs["irregularity"] * 0.30), 0.02, 0.45),
        "activity_event_probability": _clamp(0.18 + (knobs["activity_skew"] * 0.28), 0.18, 0.72),
        "lead_convert_probability": _clamp(0.08 + (knobs["dependency_strength"] * 0.24), 0.05, 0.55),
        "lead_stall_probability": _clamp(0.22 + (knobs["silence_chance"] * 0.52), 0.20, 0.80),
        "deal_stall_probability": _clamp(0.20 + (knobs["silence_chance"] * 0.55), 0.20, 0.85),
        "deal_close_probability": _clamp(0.10 + (knobs["dependency_strength"] * 0.25) - (knobs["silence_chance"] * 0.10), 0.05, 0.60),
        "deal_disappear_probability": _clamp(0.01 + (knobs["outlier_chance"] * 0.30) + (knobs["format_noise_chance"] * 0.10), 0.01, 0.30),
        "burst_batch_min": 2,
        "burst_batch_max": int(max(4, round(4 + knobs["activity_skew"] * 7))),
        "silence_min_seconds": 1.5 + (knobs["silence_chance"] * 4.0),
        "silence_max_seconds": 4.5 + (knobs["silence_chance"] * 13.0),
    }
