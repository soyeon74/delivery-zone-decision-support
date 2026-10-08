from pathlib import Path
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.aggregation import (
    combine_delivery_results,
    summarize_route_month,
    check_route_master_links,
)
from src.validation import (
    read_csv_file,
    validate_route_master,
    validate_workload,
    validate_gis_candidates,
)
from src.decision import (
    evaluate_stop_combination,
    compare_candidate_combinations,
)


st.set_page_config(
    page_title="집배구 업무조정 의사결정 지원",
    layout="wide",
)

st.title("집배구 업무조정 의사결정 지원 시스템")
st.caption(
    "개발 중인 공개용 프로토타입 · 현재 화면은 완전 합성 샘플데이터만 사용합니다."
)

st.info(
    "실제 주소·고객정보·우편물 식별정보 등 운영 원자료는 "
    "공개 저장소에 포함하지 않습니다."
)


@st.cache_data
def load_sample_data():
    sample_dir = ROOT / "data" / "sample"

    delivery_files = sorted(
        sample_dir.glob("delivery_results_*.csv")
    )

    deliveries = combine_delivery_results(delivery_files)
    route_master = read_csv_file(
        sample_dir / "route_master.csv"
    )
    workload = read_csv_file(
        sample_dir / "workload.csv"
    )
    gis_candidates = read_csv_file(
        sample_dir / "gis_candidates.csv"
    )

    return (
        deliveries,
        route_master,
        workload,
        gis_candidates,
    )


try:
    (
        deliveries,
        route_master,
        workload,
        gis_candidates,
    ) = load_sample_data()

except Exception as exc:
    st.error(f"샘플데이터 로딩 실패: {exc}")
    st.stop()


st.header("1. 데이터 검증")

route_check = validate_route_master(route_master)
workload_check = validate_workload(workload)
gis_check = validate_gis_candidates(gis_candidates)
link_check = check_route_master_links(
    deliveries,
    route_master,
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "주배달점",
    "PASS" if route_check["valid"] else "FAIL",
)

c2.metric(
    "업무강도",
    "PASS" if workload_check["valid"] else "FAIL",
)

c3.metric(
    "GIS 후보",
    "PASS" if gis_check["valid"] else "FAIL",
)

link_pass = (
    link_check["unknown_stop_rows"] == 0
    and link_check["route_mismatch_rows"] == 0
)

c4.metric(
    "배달결과 연결",
    "PASS" if link_pass else "CHECK",
)

if not route_check["valid"]:
    st.error(route_check["errors"])

if not workload_check["valid"]:
    st.error(workload_check["errors"])

if not gis_check["valid"]:
    st.error(gis_check["errors"])

if not link_pass:
    st.warning(link_check)


st.subheader("다월 배달결과 요약")

route_month_summary = summarize_route_month(deliveries)

st.dataframe(
    route_month_summary,
    width="stretch",
    hide_index=True,
)


st.header("2. 이관 방향 설정")

routes = sorted(
    route_master["route_id"].dropna().unique().tolist()
)

default_sender = (
    routes.index("R02")
    if "R02" in routes
    else 0
)

sender_route = st.selectbox(
    "보내는 집배구",
    routes,
    index=default_sender,
)

receiver_options = [
    route
    for route in routes
    if route != sender_route
]

default_receiver = (
    receiver_options.index("R01")
    if "R01" in receiver_options
    else 0
)

receiver_route = st.selectbox(
    "받는 집배구",
    receiver_options,
    index=default_receiver,
)


st.header("3. 후보 배달점 선택")

candidate_table = gis_candidates[
    (gis_candidates["sender_route"] == sender_route)
    & (
        gis_candidates["receiver_route"]
        == receiver_route
    )
    & (
        gis_candidates["candidate_flag"]
        .astype(str)
        .str.lower()
        .isin(["true", "1"])
    )
].copy()

candidate_table = candidate_table.merge(
    route_master[
        [
            "stop_id",
            "road_name",
            "building_no",
            "stop_type",
        ]
    ],
    on="stop_id",
    how="left",
)

if candidate_table.empty:
    st.warning(
        "현재 선택한 이관 방향에는 "
        "candidate_flag=True 후보가 없습니다."
    )
    st.stop()

st.dataframe(
    candidate_table,
    width="stretch",
    hide_index=True,
)

candidate_stop_ids = (
    candidate_table["stop_id"]
    .dropna()
    .tolist()
)

selected_stop_ids = st.multiselect(
    "이관 대상으로 검토할 배달점",
    options=candidate_stop_ids,
    default=[candidate_stop_ids[0]],
)


st.header("4. 분석 기준")

c1, c2 = st.columns(2)

with c1:
    index_minutes_per_1 = st.number_input(
        "업무강도 1.0 환산 기준(분)",
        min_value=1.0,
        value=435.0,
        step=1.0,
        help=(
            "공식 기준으로 고정된 값이 아닙니다. "
            "현재 435분은 합성자료 기능검증용 시험값입니다."
        ),
    )

with c2:
    target_gap = st.number_input(
        "목표 업무강도 격차",
        min_value=0.0,
        value=0.10,
        step=0.01,
        format="%.2f",
        help=(
            "기관·분석 목적에 따라 사용자가 "
            "설정하는 기준입니다."
        ),
    )


st.header("5. 업무강도 시뮬레이션")

if st.button(
    "선택 배달점 이관 시뮬레이션",
    type="primary",
):
    if not selected_stop_ids:
        st.warning(
            "이관 대상 배달점을 1개 이상 선택하세요."
        )

    else:
        try:
            result = evaluate_stop_combination(
                deliveries=deliveries,
                route_master=route_master,
                workload=workload,
                stop_ids=selected_stop_ids,
                sender_route=sender_route,
                receiver_route=receiver_route,
                index_minutes_per_1=(
                    index_minutes_per_1
                ),
                target_gap=target_gap,
            )

            simulation = result["simulation"]
            summary = result["summary"]

            st.subheader("대표 결과")

            m1, m2, m3, m4 = st.columns(4)

            m1.metric(
                f"{sender_route} 업무강도",
                f"{summary['avg_sender_workload_after']:.3f}",
                (
                    f"{summary['avg_sender_workload_after'] - summary['avg_sender_workload_before']:+.3f}"
                ),
            )

            m2.metric(
                f"{receiver_route} 업무강도",
                f"{summary['avg_receiver_workload_after']:.3f}",
                (
                    f"{summary['avg_receiver_workload_after'] - summary['avg_receiver_workload_before']:+.3f}"
                ),
            )

            m3.metric(
                "평균 격차",
                f"{summary['avg_gap_after']:.3f}",
                (
                    f"{summary['avg_gap_after'] - summary['avg_gap_before']:+.3f}"
                ),
            )

            m4.metric(
                "평균 월 이관시간",
                f"{summary['avg_transfer_minutes']:.1f}분",
            )

            if summary["all_months_target_met"]:
                st.success(
                    "모든 분석월에서 목표 업무강도 "
                    "격차를 충족했습니다."
                )
            else:
                st.warning(
                    "일부 분석월에서 목표 업무강도 "
                    "격차를 충족하지 못했습니다."
                )

            if summary["over_adjustment_months"] > 0:
                st.error(
                    "과조정 가능성이 있는 분석월이 "
                    f"{summary['over_adjustment_months']}개월 있습니다."
                )

            elif summary["crossover_months"] > 0:
                st.info(
                    "업무강도 순위가 역전되는 월이 있으나 "
                    "설정한 목표 범위 안에서 발생했습니다."
                )

            st.subheader("월별 상세 결과")

            display_columns = [
                "month",
                "transfer_minutes",
                "sender_workload_before",
                "sender_workload_after",
                "receiver_workload_before",
                "receiver_workload_after",
                "gap_before",
                "gap_after",
                "target_gap_met",
                "crossover",
                "over_adjustment",
            ]

            st.dataframe(
                simulation[display_columns],
                width="stretch",
                hide_index=True,
            )

        except Exception as exc:
            st.error(f"시뮬레이션 오류: {exc}")


st.header("6. 후보 조합 비교")

max_size = st.slider(
    "최대 동시 이관 배달점 수",
    min_value=1,
    max_value=len(candidate_stop_ids),
    value=min(2, len(candidate_stop_ids)),
)

if st.button("후보 조합 비교"):
    try:
        comparison = compare_candidate_combinations(
            deliveries=deliveries,
            route_master=route_master,
            workload=workload,
            candidate_stop_ids=candidate_stop_ids,
            sender_route=sender_route,
            receiver_route=receiver_route,
            index_minutes_per_1=index_minutes_per_1,
            target_gap=target_gap,
            max_combination_size=max_size,
        )

        st.dataframe(
            comparison,
            width="stretch",
            hide_index=True,
        )

        if not comparison.empty:
            best = comparison.iloc[0]

            st.success(
                "현재 설정 기준 상위 조합: "
                f"{best['selected_stop_ids']}"
            )

    except Exception as exc:
        st.error(f"후보 비교 오류: {exc}")


st.divider()

st.caption(
    "본 화면은 업무조정 의사결정을 지원하기 위한 "
    "프로토타입이며 최종 판단은 관리자가 수행합니다."
)

