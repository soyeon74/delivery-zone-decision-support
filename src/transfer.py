import pandas as pd


def validate_transfer_selection(
    route_master,
    selected_stop_ids,
    sender_route,
    receiver_route,
):
    """
    이관대상 배달점 선택값의 기본 정합성을 검증한다.
    """
    selected_stop_ids = list(dict.fromkeys(selected_stop_ids))

    if not selected_stop_ids:
        raise ValueError("이관대상 배달점이 선택되지 않았습니다.")

    if sender_route == receiver_route:
        raise ValueError("보내는 집배구와 받는 집배구는 서로 달라야 합니다.")

    master = route_master[
        ["stop_id", "route_id"]
    ].drop_duplicates()

    known_stops = set(master["stop_id"])
    unknown = sorted(
        set(selected_stop_ids) - known_stops
    )

    if unknown:
        raise ValueError(
            "주배달점 마스터에 없는 stop_id: "
            + ", ".join(unknown)
        )

    selected_master = master[
        master["stop_id"].isin(selected_stop_ids)
    ]

    wrong_route = sorted(
        selected_master.loc[
            selected_master["route_id"] != sender_route,
            "stop_id",
        ].tolist()
    )

    if wrong_route:
        raise ValueError(
            f"{sender_route} 소속이 아닌 배달점이 포함되어 있습니다: "
            + ", ".join(wrong_route)
        )

    return selected_stop_ids


def summarize_transfer_by_month(
    deliveries,
    route_master,
    selected_stop_ids,
    sender_route,
    receiver_route,
):
    """
    선택한 배달점을 sender_route에서 receiver_route로
    이관한다고 가정했을 때 월별 이관 활동량을 계산한다.

    activity_share:
        선택 배달점 활동기록 / 보내는 집배구 전체 활동기록

    visit_share:
        선택 배달점 배달점-일 방문수 / 보내는 집배구 전체 방문수
    """
    selected_stop_ids = validate_transfer_selection(
        route_master=route_master,
        selected_stop_ids=selected_stop_ids,
        sender_route=sender_route,
        receiver_route=receiver_route,
    )

    sender = deliveries[
        deliveries["route_id"] == sender_route
    ].copy()

    if sender.empty:
        raise ValueError(
            f"배달결과에 보내는 집배구 {sender_route} 자료가 없습니다."
        )

    selected = sender[
        sender["stop_id"].isin(selected_stop_ids)
    ].copy()

    sender_activity = (
        sender.groupby("month", as_index=False)
        .agg(
            sender_activity_records=("item_id", "size"),
            sender_unique_items=("item_id", "nunique"),
        )
    )

    sender_visits = (
        sender[
            [
                "month",
                "delivery_date",
                "stop_id",
            ]
        ]
        .drop_duplicates()
        .groupby("month", as_index=False)
        .agg(
            sender_address_day_visits=("stop_id", "size"),
        )
    )

    target_activity = (
        selected.groupby("month", as_index=False)
        .agg(
            transfer_activity_records=("item_id", "size"),
            transfer_unique_items=("item_id", "nunique"),
            observed_transfer_stops=("stop_id", "nunique"),
        )
    )

    target_visits = (
        selected[
            [
                "month",
                "delivery_date",
                "stop_id",
            ]
        ]
        .drop_duplicates()
        .groupby("month", as_index=False)
        .agg(
            transfer_address_day_visits=("stop_id", "size"),
        )
    )

    summary = (
        sender_activity
        .merge(
            sender_visits,
            on="month",
            how="left",
        )
        .merge(
            target_activity,
            on="month",
            how="left",
        )
        .merge(
            target_visits,
            on="month",
            how="left",
        )
    )

    zero_columns = [
        "transfer_activity_records",
        "transfer_unique_items",
        "observed_transfer_stops",
        "transfer_address_day_visits",
    ]

    summary[zero_columns] = (
        summary[zero_columns]
        .fillna(0)
        .astype(int)
    )

    summary["activity_share"] = (
        summary["transfer_activity_records"]
        / summary["sender_activity_records"]
    )

    summary["visit_share"] = (
        summary["transfer_address_day_visits"]
        / summary["sender_address_day_visits"]
    )

    summary["sender_route"] = sender_route
    summary["receiver_route"] = receiver_route
    summary["selected_stop_count"] = len(selected_stop_ids)

    column_order = [
        "month",
        "sender_route",
        "receiver_route",
        "selected_stop_count",
        "observed_transfer_stops",
        "transfer_activity_records",
        "sender_activity_records",
        "activity_share",
        "transfer_address_day_visits",
        "sender_address_day_visits",
        "visit_share",
        "transfer_unique_items",
        "sender_unique_items",
    ]

    return summary[column_order].sort_values(
        "month"
    ).reset_index(drop=True)


def summarize_transfer_item_types(
    deliveries,
    selected_stop_ids,
    sender_route,
):
    """
    선택 배달점의 월별 종별 활동기록을 집계한다.
    """
    selected = deliveries[
        (deliveries["route_id"] == sender_route)
        & (deliveries["stop_id"].isin(selected_stop_ids))
    ].copy()

    if selected.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "item_type",
                "activity_records",
            ]
        )

    return (
        selected.groupby(
            ["month", "item_type"],
            as_index=False,
        )
        .agg(
            activity_records=("item_id", "size"),
        )
        .sort_values(
            ["month", "item_type"]
        )
        .reset_index(drop=True)
    )
