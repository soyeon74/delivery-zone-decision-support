from pathlib import Path
import pandas as pd


REQUIRED_COLUMNS = {
    "route_master": {
        "stop_id",
        "route_id",
        "road_name",
        "building_no",
        "building_sub_no",
        "stop_type",
        "sample_x",
        "sample_y",
    },
    "delivery_results": {
        "delivery_date",
        "route_id",
        "stop_id",
        "item_id",
        "item_type",
    },
    "workload": {
        "month",
        "route_id",
        "workdays",
        "workload_index",
        "delivery_hours",
        "travel_hours",
        "ancillary_after_departure_hours",
        "total_volume_avg",
        "registered_avg",
        "distance_km_avg",
    },
    "gis_candidates": {
        "sender_route",
        "receiver_route",
        "stop_id",
        "adjacency_score",
        "continuity_score",
        "candidate_flag",
    },
}


def read_csv_file(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"파일이 없습니다: {path}")

    if path.suffix.lower() != ".csv":
        raise ValueError(f"현재 1단계에서는 CSV만 지원합니다: {path.name}")

    return pd.read_csv(path)


def validate_required_columns(df, dataset_type):
    required = REQUIRED_COLUMNS[dataset_type]
    missing = sorted(required - set(df.columns))

    if missing:
        return {
            "valid": False,
            "errors": [f"필수 컬럼 누락: {', '.join(missing)}"],
        }

    return {
        "valid": True,
        "errors": [],
    }


def validate_route_master(df):
    result = validate_required_columns(df, "route_master")

    if not result["valid"]:
        return result

    errors = []

    if df["stop_id"].isna().any():
        errors.append("stop_id에 결측값이 있습니다.")

    if df["stop_id"].duplicated().any():
        errors.append("stop_id 중복값이 있습니다.")

    if df["route_id"].isna().any():
        errors.append("route_id에 결측값이 있습니다.")

    for column in ["sample_x", "sample_y"]:
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.isna().any():
            errors.append(f"{column}에 숫자가 아닌 값이 있습니다.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_delivery_results(df):
    result = validate_required_columns(df, "delivery_results")

    if not result["valid"]:
        return result

    errors = []

    dates = pd.to_datetime(df["delivery_date"], errors="coerce")
    if dates.isna().any():
        errors.append("delivery_date에 날짜로 해석할 수 없는 값이 있습니다.")

    for column in ["route_id", "stop_id", "item_id", "item_type"]:
        if df[column].isna().any():
            errors.append(f"{column}에 결측값이 있습니다.")

    if df.duplicated().any():
        errors.append("완전히 동일한 중복 행이 있습니다.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_workload(df):
    result = validate_required_columns(df, "workload")

    if not result["valid"]:
        return result

    errors = []

    numeric_columns = [
        "workdays",
        "workload_index",
        "delivery_hours",
        "travel_hours",
        "ancillary_after_departure_hours",
        "total_volume_avg",
        "registered_avg",
        "distance_km_avg",
    ]

    for column in numeric_columns:
        numeric = pd.to_numeric(df[column], errors="coerce")

        if numeric.isna().any():
            errors.append(f"{column}에 숫자가 아닌 값이 있습니다.")

        if (numeric < 0).any():
            errors.append(f"{column}에 음수값이 있습니다.")

    workdays = pd.to_numeric(df["workdays"], errors="coerce")
    if (workdays <= 0).any():
        errors.append("workdays는 0보다 커야 합니다.")

    if df.duplicated(subset=["month", "route_id"]).any():
        errors.append("동일한 month + route_id 조합이 중복되어 있습니다.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_gis_candidates(df):
    result = validate_required_columns(df, "gis_candidates")

    if not result["valid"]:
        return result

    errors = []

    if (df["sender_route"] == df["receiver_route"]).any():
        errors.append("보내는 집배구와 받는 집배구가 동일한 후보가 있습니다.")

    for column in ["adjacency_score", "continuity_score"]:
        numeric = pd.to_numeric(df[column], errors="coerce")

        if numeric.isna().any():
            errors.append(f"{column}에 숫자가 아닌 값이 있습니다.")
        elif ((numeric < 0) | (numeric > 1)).any():
            errors.append(f"{column}은 0~1 범위여야 합니다.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }

