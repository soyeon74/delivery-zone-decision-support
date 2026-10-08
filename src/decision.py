import itertools
import pandas as pd

from src.transfer import summarize_transfer_by_month
from src.workload_simulation import (
    simulate_workload_transfer,
    summarize_multi_month_simulation,
)


def evaluate_simulation(
    simulation,
    target_gap,
):
    """
    월별 시뮬레이션 결과를 평가한다.

    target_gap:
        사용자가 설정하는 목표 업무강도 격차.
        특정 기관 기준을 코드에 고정하지 않는다.
    """

    try:
        target_gap = float(target_gap)
    except (TypeError, ValueError):
        raise ValueError("목표 격차는 숫자여야 합니다.")

    if target_gap < 0:
        raise ValueError("목표 격차는 0 이상이어야 합니다.")

    evaluated = simulation.copy()

    evaluated["gap_improved"] = (
        evaluated["gap_after"] < evaluated["gap_before"]
    )

    evaluated["target_gap_met"] = (
        evaluated["gap_after"] <= target_gap
    )

    evaluated["crossover"] = (
        (
            evaluated["sender_workload_before"]
            > evaluated["receiver_workload_before"]
        )
        &
        (
            evaluated["sender_workload_after"]
            < evaluated["receiver_workload_after"]
        )
    ) | (
        (
            evaluated["sender_workload_before"]
            < evaluated["receiver_workload_before"]
        )
        &
        (
            evaluated["sender_workload_after"]
            > evaluated["receiver_workload_after"]
        )
    )

    evaluated["over_adjustment"] = (
        evaluated["crossover"]
        & (evaluated["gap_after"] > target_gap)
    )

    return evaluated


def summarize_decision(evaluated):
    """
    여러 월 평가결과를 하나의 의사결정 요약으로 만든다.
    """

    if evaluated.empty:
        raise ValueError("평가할 결과가 없습니다.")

    summary = summarize_multi_month_simulation(evaluated)

    summary.update(
        {
            "all_months_improved": bool(
                evaluated["gap_improved"].all()
            ),
            "all_months_target_met": bool(
                evaluated["target_gap_met"].all()
            ),
            "crossover_months": int(
                evaluated["crossover"].sum()
            ),
            "over_adjustment_months": int(
                evaluated["over_adjustment"].sum()
            ),
        }
    )

    return summary


def evaluate_stop_combination(
    deliveries,
    route_master,
    workload,
    stop_ids,
    sender_route,
    receiver_route,
    index_minutes_per_1,
    target_gap,
):
    """
    하나의 배달점 조합에 대해
    이관량 → 업무강도 → 판정을 한 번에 실행한다.
    """

    transfer = summarize_transfer_by_month(
        deliveries=deliveries,
        route_master=route_master,
        selected_stop_ids=stop_ids,
        sender_route=sender_route,
        receiver_route=receiver_route,
    )

    simulation = simulate_workload_transfer(
        workload=workload,
        transfer_summary=transfer,
        index_minutes_per_1=index_minutes_per_1,
    )

    evaluated = evaluate_simulation(
        simulation=simulation,
        target_gap=target_gap,
    )

    summary = summarize_decision(evaluated)

    summary["selected_stop_ids"] = list(stop_ids)
    summary["selected_stop_count"] = len(stop_ids)

    return {
        "transfer": transfer,
        "simulation": evaluated,
        "summary": summary,
    }


def compare_candidate_combinations(
    deliveries,
    route_master,
    workload,
    candidate_stop_ids,
    sender_route,
    receiver_route,
    index_minutes_per_1,
    target_gap,
    max_combination_size=None,
):
    """
    후보 배달점들의 조합을 비교한다.

    후보 수가 많아질수록 조합 수가 급증하므로
    max_combination_size로 최대 선택 개수를 제한할 수 있다.
    """

    candidate_stop_ids = list(
        dict.fromkeys(candidate_stop_ids)
    )

    if not candidate_stop_ids:
        raise ValueError("후보 배달점이 없습니다.")

    if max_combination_size is None:
        max_combination_size = len(candidate_stop_ids)

    max_combination_size = min(
        int(max_combination_size),
        len(candidate_stop_ids),
    )

    if max_combination_size <= 0:
        raise ValueError(
            "max_combination_size는 1 이상이어야 합니다."
        )

    rows = []

    for size in range(1, max_combination_size + 1):
        for combination in itertools.combinations(
            candidate_stop_ids,
            size,
        ):
            result = evaluate_stop_combination(
                deliveries=deliveries,
                route_master=route_master,
                workload=workload,
                stop_ids=list(combination),
                sender_route=sender_route,
                receiver_route=receiver_route,
                index_minutes_per_1=index_minutes_per_1,
                target_gap=target_gap,
            )

            summary = result["summary"]

            rows.append(
                {
                    "selected_stop_ids": ",".join(combination),
                    "selected_stop_count": size,
                    "avg_gap_before": summary["avg_gap_before"],
                    "avg_gap_after": summary["avg_gap_after"],
                    "all_months_improved": summary[
                        "all_months_improved"
                    ],
                    "all_months_target_met": summary[
                        "all_months_target_met"
                    ],
                    "crossover_months": summary[
                        "crossover_months"
                    ],
                    "over_adjustment_months": summary[
                        "over_adjustment_months"
                    ],
                    "avg_sender_workload_after": summary[
                        "avg_sender_workload_after"
                    ],
                    "avg_receiver_workload_after": summary[
                        "avg_receiver_workload_after"
                    ],
                }
            )

    result = pd.DataFrame(rows)

    return result.sort_values(
        [
            "all_months_target_met",
            "over_adjustment_months",
            "all_months_improved",
            "avg_gap_after",
            "selected_stop_count",
        ],
        ascending=[
            False,
            True,
            False,
            True,
            True,
        ],
    ).reset_index(drop=True)
