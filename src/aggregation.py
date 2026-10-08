from pathlib import Path
import pandas as pd

from src.validation import read_csv_file, validate_delivery_results


def combine_delivery_results(file_paths):
    """
    여러 월의 배달결과 CSV를 검증한 뒤 하나의 DataFrame으로 통합한다.
    """
    frames = []

    for file_path in file_paths:
        path = Path(file_path)
        df = read_csv_file(path)

        result = validate_delivery_results(df)
        if not result["valid"]:
            raise ValueError(
                f"{path.name} 검증 실패: " + "; ".join(result["errors"])
            )

        df = df.copy()
        df["delivery_date"] = pd.to_datetime(df["delivery_date"])
        df["month"] = df["delivery_date"].dt.to_period("M").astype(str)
        df["source_file"] = path.name

        frames.append(df)

    if not frames:
        raise ValueError("통합할 배달결과 파일이 없습니다.")

    combined = pd.concat(frames, ignore_index=True)

    return combined.sort_values(
        ["delivery_date", "route_id", "stop_id", "item_id"]
    ).reset_index(drop=True)


def summarize_route_month(deliveries):
    """
    월·집배구 단위 활동량을 집계한다.

    activity_records:
        배달결과 행 수

    address_day_visits:
        동일 날짜·동일 집배구·동일 배달점은 1회 방문으로 계산
    """
    df = deliveries.copy()

    visit_df = (
        df[
            [
                "month",
                "delivery_date",
                "route_id",
                "stop_id",
            ]
        ]
        .drop_duplicates()
    )

    visit_summary = (
        visit_df.groupby(
            ["month", "route_id"],
            as_index=False,
        )
        .agg(
            address_day_visits=("stop_id", "size"),
            delivery_days=("delivery_date", "nunique"),
            unique_stops=("stop_id", "nunique"),
        )
    )

    activity_summary = (
        df.groupby(
            ["month", "route_id"],
            as_index=False,
        )
        .agg(
            activity_records=("item_id", "size"),
            unique_items=("item_id", "nunique"),
        )
    )

    item_type_summary = (
        df.groupby(
            ["month", "route_id", "item_type"],
            as_index=False,
        )
        .size()
        .pivot(
            index=["month", "route_id"],
            columns="item_type",
            values="size",
        )
        .fillna(0)
        .astype(int)
        .reset_index()
    )

    item_type_summary.columns.name = None
    item_type_summary = item_type_summary.rename(
        columns={
            col: f"{col}_records"
            for col in item_type_summary.columns
            if col not in ["month", "route_id"]
        }
    )

    summary = (
        activity_summary
        .merge(
            visit_summary,
            on=["month", "route_id"],
            how="left",
        )
        .merge(
            item_type_summary,
            on=["month", "route_id"],
            how="left",
        )
    )

    return summary.sort_values(
        ["month", "route_id"]
    ).reset_index(drop=True)


def summarize_stop_month(deliveries):
    """
    월·집배구·배달점 단위 활동량을 집계한다.
    이후 특정 배달점을 다른 집배구로 이관할 때 사용한다.
    """
    df = deliveries.copy()

    visit_df = (
        df[
            [
                "month",
                "delivery_date",
                "route_id",
                "stop_id",
            ]
        ]
        .drop_duplicates()
    )

    visit_summary = (
        visit_df.groupby(
            ["month", "route_id", "stop_id"],
            as_index=False,
        )
        .agg(
            address_day_visits=("delivery_date", "size"),
            delivery_days=("delivery_date", "nunique"),
        )
    )

    activity_summary = (
        df.groupby(
            ["month", "route_id", "stop_id"],
            as_index=False,
        )
        .agg(
            activity_records=("item_id", "size"),
            unique_items=("item_id", "nunique"),
        )
    )

    summary = activity_summary.merge(
        visit_summary,
        on=["month", "route_id", "stop_id"],
        how="left",
    )

    return summary.sort_values(
        ["month", "route_id", "stop_id"]
    ).reset_index(drop=True)


def check_route_master_links(deliveries, route_master):
    """
    배달결과의 stop_id가 주배달점 마스터에 존재하는지,
    해당 stop_id의 route_id가 서로 일치하는지 확인한다.
    """
    master = route_master[
        ["stop_id", "route_id"]
    ].drop_duplicates().rename(
        columns={"route_id": "master_route_id"}
    )

    checked = deliveries.merge(
        master,
        on="stop_id",
        how="left",
    )

    unknown_stop_rows = checked[
        checked["master_route_id"].isna()
    ].copy()

    route_mismatch_rows = checked[
        checked["master_route_id"].notna()
        & (checked["route_id"] != checked["master_route_id"])
    ].copy()

    return {
        "unknown_stop_rows": len(unknown_stop_rows),
        "route_mismatch_rows": len(route_mismatch_rows),
        "unknown_stop_ids": sorted(
            unknown_stop_rows["stop_id"].dropna().unique().tolist()
        ),
        "route_mismatch_stop_ids": sorted(
            route_mismatch_rows["stop_id"].dropna().unique().tolist()
        ),
    }
