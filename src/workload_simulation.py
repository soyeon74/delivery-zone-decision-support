import pandas as pd


def simulate_workload_transfer(
    workload,
    transfer_summary,
    index_minutes_per_1,
):
    """
    선택 배달점 이관에 따른 월별 업무강도 변화를 계산한다.

    index_minutes_per_1:
        업무강도 1.0에 대응시키는 환산 분(minute) 기준.
        공식값으로 고정하지 않고 호출 시 명시한다.
    """

    if index_minutes_per_1 is None:
        raise ValueError(
            "업무강도 환산 기준(index_minutes_per_1)을 입력해야 합니다."
        )

    try:
        index_minutes_per_1 = float(index_minutes_per_1)
    except (TypeError, ValueError):
        raise ValueError("업무강도 환산 기준은 숫자여야 합니다.")

    if index_minutes_per_1 <= 0:
        raise ValueError("업무강도 환산 기준은 0보다 커야 합니다.")

    results = []

    for row in transfer_summary.itertuples(index=False):
        month = row.month
        sender_route = row.sender_route
        receiver_route = row.receiver_route

        sender_match = workload[
            (workload["month"] == month)
            & (workload["route_id"] == sender_route)
        ]

        receiver_match = workload[
            (workload["month"] == month)
            & (workload["route_id"] == receiver_route)
        ]

        if len(sender_match) != 1:
            raise ValueError(
                f"{month} {sender_route} 업무강도 자료가 정확히 1행이어야 합니다."
            )

        if len(receiver_match) != 1:
            raise ValueError(
                f"{month} {receiver_route} 업무강도 자료가 정확히 1행이어야 합니다."
            )

        sender = sender_match.iloc[0]
        receiver = receiver_match.iloc[0]

        sender_workdays = float(sender["workdays"])
        receiver_workdays = float(receiver["workdays"])

        if sender_workdays <= 0 or receiver_workdays <= 0:
            raise ValueError("근무일수는 0보다 커야 합니다.")

        delivery_transfer_hours = (
            float(sender["delivery_hours"])
            * float(row.activity_share)
        )

        travel_transfer_hours = (
            float(sender["travel_hours"])
            * float(row.visit_share)
        )

        ancillary_transfer_hours = (
            float(sender["ancillary_after_departure_hours"])
            * float(row.activity_share)
        )

        transfer_hours = (
            delivery_transfer_hours
            + travel_transfer_hours
            + ancillary_transfer_hours
        )

        transfer_minutes = transfer_hours * 60.0

        sender_daily_transfer_minutes = (
            transfer_minutes / sender_workdays
        )

        receiver_daily_transfer_minutes = (
            transfer_minutes / receiver_workdays
        )

        sender_index_delta = (
            sender_daily_transfer_minutes
            / index_minutes_per_1
        )

        receiver_index_delta = (
            receiver_daily_transfer_minutes
            / index_minutes_per_1
        )

        sender_before = float(sender["workload_index"])
        receiver_before = float(receiver["workload_index"])

        sender_after = sender_before - sender_index_delta
        receiver_after = receiver_before + receiver_index_delta

        gap_before = abs(sender_before - receiver_before)
        gap_after = abs(sender_after - receiver_after)

        gap_reduction_rate = None
        if gap_before > 0:
            gap_reduction_rate = (
                (gap_before - gap_after)
                / gap_before
            )

        results.append(
            {
                "month": month,
                "sender_route": sender_route,
                "receiver_route": receiver_route,
                "activity_share": float(row.activity_share),
                "visit_share": float(row.visit_share),
                "delivery_transfer_hours": delivery_transfer_hours,
                "travel_transfer_hours": travel_transfer_hours,
                "ancillary_transfer_hours": ancillary_transfer_hours,
                "transfer_hours": transfer_hours,
                "transfer_minutes": transfer_minutes,
                "sender_workdays": sender_workdays,
                "receiver_workdays": receiver_workdays,
                "sender_daily_transfer_minutes": sender_daily_transfer_minutes,
                "receiver_daily_transfer_minutes": receiver_daily_transfer_minutes,
                "index_minutes_per_1": index_minutes_per_1,
                "sender_workload_before": sender_before,
                "sender_index_delta": sender_index_delta,
                "sender_workload_after": sender_after,
                "receiver_workload_before": receiver_before,
                "receiver_index_delta": receiver_index_delta,
                "receiver_workload_after": receiver_after,
                "gap_before": gap_before,
                "gap_after": gap_after,
                "gap_reduction_rate": gap_reduction_rate,
            }
        )

    return pd.DataFrame(results)


def summarize_multi_month_simulation(simulation):
    if simulation.empty:
        raise ValueError("요약할 시뮬레이션 결과가 없습니다.")

    return {
        "months": int(simulation["month"].nunique()),
        "avg_transfer_minutes": float(
            simulation["transfer_minutes"].mean()
        ),
        "avg_sender_workload_before": float(
            simulation["sender_workload_before"].mean()
        ),
        "avg_sender_workload_after": float(
            simulation["sender_workload_after"].mean()
        ),
        "avg_receiver_workload_before": float(
            simulation["receiver_workload_before"].mean()
        ),
        "avg_receiver_workload_after": float(
            simulation["receiver_workload_after"].mean()
        ),
        "avg_gap_before": float(
            simulation["gap_before"].mean()
        ),
        "avg_gap_after": float(
            simulation["gap_after"].mean()
        ),
    }
