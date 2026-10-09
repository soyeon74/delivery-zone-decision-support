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
    validate_delivery_results,
    validate_workload,
    validate_gis_candidates,
)
from src.input_loader import (
    read_uploaded_table,
    read_multiple_delivery_files,
)
from src.column_mapping import (
    get_standard_fields,
    FIELD_LABELS,
    exact_name_mapping,
    apply_column_mapping,
)
from src.decision import (
    evaluate_stop_combination,
    compare_candidate_combinations,
)


st.set_page_config(
    page_title="집배구 업무조정 의사결정 지원 V2",
    layout="wide",
)

st.title("집배구 업무조정 의사결정 지원 시스템")
st.caption(
    "개발 중인 공개용 프로토타입 · 합성 샘플모드와 로컬 파일모드를 지원합니다."
)

st.warning(
    "실제 운영자료는 반드시 사용자 PC에서 로컬 실행할 때만 사용하세요. "
    "공개 배포된 웹사이트나 GitHub에는 실제 주소·고객정보·우편물 식별정보를 "
    "업로드하거나 저장하지 않습니다."
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


def combine_uploaded_deliveries(uploaded_files):
    loaded = read_multiple_delivery_files(
        uploaded_files
    )

    frames = []

    for item in loaded:
        filename = item["filename"]
        df = item["dataframe"].copy()

        result = validate_delivery_results(df)

        if not result["valid"]:
            raise ValueError(
                f"{filename} 검증 실패: "
                + "; ".join(result["errors"])
            )

        df["delivery_date"] = pd.to_datetime(
            df["delivery_date"],
            errors="raise",
        )

        df["month"] = (
            df["delivery_date"]
            .dt.to_period("M")
            .astype(str)
        )

        df["source_file"] = filename

        frames.append(df)

    if not frames:
        raise ValueError(
            "배달결과 파일이 없습니다."
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    return combined.sort_values(
        [
            "delivery_date",
            "route_id",
            "stop_id",
            "item_id",
        ]
    ).reset_index(drop=True)


def render_mapping_editor(
    df,
    dataset_type,
    key_prefix,
    title,
):
    auto_mapping = exact_name_mapping(
        df,
        dataset_type,
    )

    source_columns = [
        str(column)
        for column in df.columns
    ]

    empty_option = "-- 선택 안 함 --"
    options = [empty_option] + source_columns
    mapping = {}

    with st.expander(
        title,
        expanded=True,
    ):
        st.caption(
            "원본 컬럼을 프로그램 표준 컬럼에 직접 연결합니다. "
            "이름이 정확히 같은 컬럼만 자동 선택합니다."
        )

        for field in get_standard_fields(
            dataset_type
        ):
            auto_source = auto_mapping.get(field)

            if auto_source in options:
                default_index = options.index(
                    auto_source
                )
            else:
                default_index = 0

            selected = st.selectbox(
                f"{FIELD_LABELS.get(field, field)} ({field})",
                options=options,
                index=default_index,
                key=f"{key_prefix}_{field}",
            )

            mapping[field] = (
                None
                if selected == empty_option
                else selected
            )

    return mapping


def mapping_is_complete(mapping):
    return all(
        value is not None
        and str(value).strip() != ""
        for value in mapping.values()
    )


def prepare_mapped_delivery_files(
    loaded_files,
    mappings,
):
    frames = []

    for item, mapping in zip(
        loaded_files,
        mappings,
    ):
        filename = item["filename"]
        raw_df = item["dataframe"]

        df = apply_column_mapping(
            raw_df,
            "delivery_results",
            mapping,
        )

        result = validate_delivery_results(df)

        if not result["valid"]:
            raise ValueError(
                f"{filename} 검증 실패: "
                + "; ".join(result["errors"])
            )

        df = df.copy()

        df["delivery_date"] = pd.to_datetime(
            df["delivery_date"],
            errors="raise",
        )

        df["month"] = (
            df["delivery_date"]
            .dt.to_period("M")
            .astype(str)
        )

        df["source_file"] = filename
        frames.append(df)

    if not frames:
        raise ValueError(
            "배달결과 파일이 없습니다."
        )

    combined = pd.concat(
        frames,
        ignore_index=True,
    )

    return combined.sort_values(
        [
            "delivery_date",
            "route_id",
            "stop_id",
            "item_id",
        ]
    ).reset_index(drop=True)

st.sidebar.header("데이터 입력")

data_mode = st.sidebar.radio(
    "분석 데이터",
    [
        "완전 합성 샘플데이터",
        "로컬 파일 업로드",
    ],
)


if data_mode == "완전 합성 샘플데이터":

    (
        deliveries,
        route_master,
        workload,
        gis_candidates,
    ) = load_sample_data()

    st.sidebar.success(
        "완전 합성 샘플데이터 사용 중"
    )

else:

    st.sidebar.info(
        "실제 운영자료는 localhost에서만 사용하고 "
        "GitHub에는 저장하지 마세요."
    )

    route_file = st.sidebar.file_uploader(
        "① 주배달점",
        type=["csv", "xlsx"],
        key="route_master_upload",
    )

    delivery_files = st.sidebar.file_uploader(
        "② 배달결과 · 여러 달 선택 가능",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        key="delivery_uploads",
    )

    workload_file = st.sidebar.file_uploader(
        "③ 업무강도",
        type=["csv", "xlsx"],
        key="workload_upload",
    )

    gis_file = st.sidebar.file_uploader(
        "④ GIS 후보",
        type=["csv", "xlsx"],
        key="gis_upload",
    )

    ready = (
        route_file is not None
        and bool(delivery_files)
        and workload_file is not None
        and gis_file is not None
    )

    if not ready:
        st.info(
            "로컬 분석을 시작하려면 좌측에서 "
            "주배달점, 배달결과, 업무강도, GIS 후보 자료를 "
            "모두 선택하세요."
        )

        st.caption(
            "현재 단계에서는 공개용 표준 컬럼 형식의 "
            "CSV 또는 XLSX를 지원합니다."
        )

        st.stop()

    try:
        route_raw = read_uploaded_table(
            route_file
        )

        delivery_loaded = read_multiple_delivery_files(
            delivery_files
        )

        workload_raw = read_uploaded_table(
            workload_file
        )

        gis_raw = read_uploaded_table(
            gis_file
        )

    except Exception as exc:
        st.error(
            f"파일 읽기 실패: {exc}"
        )
        st.stop()

    st.header("0. 원본 컬럼 연결")

    st.info(
        "원본 파일의 컬럼명을 프로그램이 임의로 추측하지 않습니다. "
        "정확히 같은 컬럼명만 자동 선택되며, "
        "나머지는 사용자가 직접 연결합니다."
    )

    route_mapping = render_mapping_editor(
        route_raw,
        "route_master",
        "map_route",
        "① 주배달점 컬럼 연결",
    )

    delivery_mappings = []

    for index, item in enumerate(
        delivery_loaded,
        start=1,
    ):
        mapping = render_mapping_editor(
            item["dataframe"],
            "delivery_results",
            f"map_delivery_{index}",
            f"② 배달결과 컬럼 연결 [{item['filename']}]",
        )

        delivery_mappings.append(
            mapping
        )

    workload_mapping = render_mapping_editor(
        workload_raw,
        "workload",
        "map_workload",
        "③ 업무강도 컬럼 연결",
    )

    gis_mapping = render_mapping_editor(
        gis_raw,
        "gis_candidates",
        "map_gis",
        "④ GIS 후보 컬럼 연결",
    )

    all_mappings_complete = (
        mapping_is_complete(route_mapping)
        and mapping_is_complete(workload_mapping)
        and mapping_is_complete(gis_mapping)
        and all(
            mapping_is_complete(mapping)
            for mapping in delivery_mappings
        )
    )

    if not all_mappings_complete:
        st.warning(
            "아직 연결되지 않은 필수 컬럼이 있습니다. "
            "모든 항목을 연결하면 기술 검증 단계로 진행됩니다."
        )
        st.stop()

    try:
        route_master = apply_column_mapping(
            route_raw,
            "route_master",
            route_mapping,
        )

        deliveries = prepare_mapped_delivery_files(
            delivery_loaded,
            delivery_mappings,
        )

        workload = apply_column_mapping(
            workload_raw,
            "workload",
            workload_mapping,
        )

        gis_candidates = apply_column_mapping(
            gis_raw,
            "gis_candidates",
            gis_mapping,
        )

    except Exception as exc:
        st.error(
            f"컬럼 매핑 또는 변환 실패: {exc}"
        )
        st.stop()


st.header("1. 입력자료 기술 검증")

route_check = validate_route_master(
    route_master
)

workload_check = validate_workload(
    workload
)

gis_check = validate_gis_candidates(
    gis_candidates
)

link_check = check_route_master_links(
    deliveries,
    route_master,
)

link_pass = (
    link_check["unknown_stop_rows"] == 0
    and link_check["route_mismatch_rows"] == 0
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "주배달점",
    "PASS"
    if route_check["valid"]
    else "FAIL",
)

c2.metric(
    "업무강도",
    "PASS"
    if workload_check["valid"]
    else "FAIL",
)

c3.metric(
    "GIS 후보",
    "PASS"
    if gis_check["valid"]
    else "FAIL",
)

c4.metric(
    "배달결과 연결",
    "PASS"
    if link_pass
    else "CHECK",
)

has_error = False

if not route_check["valid"]:
    st.error(
        "주배달점: "
        + "; ".join(route_check["errors"])
    )
    has_error = True

if not workload_check["valid"]:
    st.error(
        "업무강도: "
        + "; ".join(workload_check["errors"])
    )
    has_error = True

if not gis_check["valid"]:
    st.error(
        "GIS 후보: "
        + "; ".join(gis_check["errors"])
    )
    has_error = True

if not link_pass:
    st.warning(
        f"미연결 배달행: "
        f"{link_check['unknown_stop_rows']}건 / "
        f"집배구 불일치: "
        f"{link_check['route_mismatch_rows']}건"
    )

if has_error:
    st.error(
        "필수 입력구조 오류가 있으므로 "
        "시뮬레이션을 중단합니다."
    )
    st.stop()


st.subheader("다월 배달결과 집계")

route_month_summary = summarize_route_month(
    deliveries
)

st.dataframe(
    route_month_summary,
    width="stretch",
    hide_index=True,
)


st.header("2. 이관 방향 설정")

routes = sorted(
    route_master[
        "route_id"
    ]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

if len(routes) < 2:
    st.error(
        "이관 분석에는 최소 2개 집배구가 필요합니다."
    )
    st.stop()

sender_route = st.selectbox(
    "보내는 집배구",
    routes,
)

receiver_options = [
    route
    for route in routes
    if route != sender_route
]

receiver_route = st.selectbox(
    "받는 집배구",
    receiver_options,
)


st.header("3. 이관 후보 선택")

candidate_flag = (
    gis_candidates[
        "candidate_flag"
    ]
    .astype(str)
    .str.strip()
    .str.lower()
    .isin(
        [
            "true",
            "1",
            "yes",
            "y",
        ]
    )
)

candidate_table = gis_candidates[
    (
        gis_candidates[
            "sender_route"
        ].astype(str)
        == str(sender_route)
    )
    &
    (
        gis_candidates[
            "receiver_route"
        ].astype(str)
        == str(receiver_route)
    )
    &
    candidate_flag
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
        "현재 선택한 이관 방향에 "
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
    .astype(str)
    .tolist()
)

selected_stop_ids = st.multiselect(
    "이관 대상으로 검토할 배달점",
    candidate_stop_ids,
    default=[
        candidate_stop_ids[0]
    ],
)


st.header("4. 분석 기준")

c1, c2 = st.columns(2)

with c1:
    index_minutes_per_1 = (
        st.number_input(
            "업무강도 1.0 환산 기준(분)",
            min_value=1.0,
            value=435.0,
            step=1.0,
            help=(
                "공식값을 코드에 고정하지 않습니다. "
                "샘플모드의 435분은 기능검증용 시험값입니다."
            ),
        )
    )

with c2:
    target_gap = st.number_input(
        "목표 업무강도 격차",
        min_value=0.0,
        value=0.10,
        step=0.01,
        format="%.2f",
    )


st.header("5. 선택안 시뮬레이션")

if st.button(
    "선택 배달점 이관 시뮬레이션",
    type="primary",
):

    if not selected_stop_ids:
        st.warning(
            "이관 대상 배달점을 선택하세요."
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

            simulation = result[
                "simulation"
            ]

            summary = result[
                "summary"
            ]

            m1, m2, m3, m4 = (
                st.columns(4)
            )

            m1.metric(
                f"{sender_route} 조정 후",
                f"{summary['avg_sender_workload_after']:.3f}",
            )

            m2.metric(
                f"{receiver_route} 조정 후",
                f"{summary['avg_receiver_workload_after']:.3f}",
            )

            m3.metric(
                "조정 후 평균 격차",
                f"{summary['avg_gap_after']:.3f}",
            )

            m4.metric(
                "평균 월 이관시간",
                f"{summary['avg_transfer_minutes']:.1f}분",
            )

            if (
                summary[
                    "all_months_target_met"
                ]
            ):
                st.success(
                    "모든 분석월에서 "
                    "목표 업무강도 격차를 충족했습니다."
                )

            else:
                st.warning(
                    "일부 분석월에서 "
                    "목표 업무강도 격차를 충족하지 못했습니다."
                )

            if (
                summary[
                    "over_adjustment_months"
                ]
                > 0
            ):
                st.error(
                    "과조정 가능성이 있는 월: "
                    f"{summary['over_adjustment_months']}개월"
                )

            elif (
                summary[
                    "crossover_months"
                ]
                > 0
            ):
                st.info(
                    "업무강도 순위 역전이 있으나 "
                    "설정한 목표범위 안에서 발생했습니다."
                )

            st.dataframe(
                simulation,
                width="stretch",
                hide_index=True,
            )

        except Exception as exc:
            st.error(
                f"시뮬레이션 오류: {exc}"
            )


st.header("6. 후보 조합 비교")

max_size = st.slider(
    "최대 동시 이관 배달점 수",
    min_value=1,
    max_value=len(
        candidate_stop_ids
    ),
    value=min(
        2,
        len(candidate_stop_ids),
    ),
)

if st.button(
    "후보 조합 비교"
):

    try:
        comparison = (
            compare_candidate_combinations(
                deliveries=deliveries,
                route_master=route_master,
                workload=workload,
                candidate_stop_ids=(
                    candidate_stop_ids
                ),
                sender_route=sender_route,
                receiver_route=receiver_route,
                index_minutes_per_1=(
                    index_minutes_per_1
                ),
                target_gap=target_gap,
                max_combination_size=(
                    max_size
                ),
            )
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
        st.error(
            f"후보 비교 오류: {exc}"
        )


st.divider()

st.caption(
    "기술적 PASS는 기관의 공식 보안·반출 승인이나 "
    "최종 업무조정 결정을 의미하지 않습니다. "
    "최종 판단은 관리자가 수행합니다."
)


