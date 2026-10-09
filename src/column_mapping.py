from copy import deepcopy


STANDARD_FIELDS = {
    "route_master": [
        "stop_id",
        "route_id",
        "road_name",
        "building_no",
        "building_sub_no",
        "stop_type",
        "sample_x",
        "sample_y",
    ],
    "delivery_results": [
        "delivery_date",
        "route_id",
        "stop_id",
        "item_id",
        "item_type",
    ],
    "workload": [
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
    ],
    "gis_candidates": [
        "sender_route",
        "receiver_route",
        "stop_id",
        "adjacency_score",
        "continuity_score",
        "candidate_flag",
    ],
}


FIELD_LABELS = {
    "stop_id": "배달점 식별코드",
    "route_id": "집배구 코드",
    "road_name": "도로명",
    "building_no": "건물 본번",
    "building_sub_no": "건물 부번",
    "stop_type": "배달점 유형",
    "sample_x": "X 좌표",
    "sample_y": "Y 좌표",
    "delivery_date": "배달일자",
    "item_id": "우편물 식별코드",
    "item_type": "우편물 종별",
    "month": "분석 월",
    "workdays": "근무일수",
    "workload_index": "업무강도",
    "delivery_hours": "배달업무시간",
    "travel_hours": "이동시간",
    "ancillary_after_departure_hours": "출발후 부수업무시간",
    "total_volume_avg": "평균 전체물량",
    "registered_avg": "평균 등기물량",
    "distance_km_avg": "평균 거리",
    "sender_route": "보내는 집배구",
    "receiver_route": "받는 집배구",
    "adjacency_score": "인접도 점수",
    "continuity_score": "연속성 점수",
    "candidate_flag": "후보 여부",
}


def get_standard_fields(dataset_type):
    if dataset_type not in STANDARD_FIELDS:
        raise ValueError(
            f"지원하지 않는 데이터 종류입니다: {dataset_type}"
        )

    return deepcopy(STANDARD_FIELDS[dataset_type])


def validate_mapping(df, dataset_type, mapping):
    """
    mapping 형식:
    {
        "표준컬럼명": "원본컬럼명",
        ...
    }
    """

    standard_fields = get_standard_fields(dataset_type)

    errors = []

    missing_mapping = [
        field
        for field in standard_fields
        if field not in mapping
        or not mapping[field]
    ]

    if missing_mapping:
        errors.append(
            "매핑되지 않은 필수 항목: "
            + ", ".join(missing_mapping)
        )

    mapped_source_columns = [
        source
        for source in mapping.values()
        if source
    ]

    duplicated_sources = sorted(
        {
            source
            for source in mapped_source_columns
            if mapped_source_columns.count(source) > 1
        }
    )

    if duplicated_sources:
        errors.append(
            "하나의 원본 컬럼이 여러 표준 항목에 중복 연결됨: "
            + ", ".join(duplicated_sources)
        )

    unknown_columns = sorted(
        {
            source
            for source in mapped_source_columns
            if source not in df.columns
        }
    )

    if unknown_columns:
        errors.append(
            "원본 파일에 없는 컬럼이 지정됨: "
            + ", ".join(unknown_columns)
        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def apply_column_mapping(
    df,
    dataset_type,
    mapping,
):
    """
    원본 DataFrame을 복사한 뒤
    사용자가 지정한 원본 컬럼명을
    프로그램 표준 컬럼명으로 변환한다.

    원본 DataFrame은 수정하지 않는다.
    """

    result = validate_mapping(
        df=df,
        dataset_type=dataset_type,
        mapping=mapping,
    )

    if not result["valid"]:
        raise ValueError(
            "; ".join(result["errors"])
        )

    reverse_mapping = {
        source: standard
        for standard, source in mapping.items()
    }

    mapped = df.rename(
        columns=reverse_mapping
    ).copy()

    standard_fields = get_standard_fields(
        dataset_type
    )

    return mapped[standard_fields].copy()


def exact_name_mapping(
    df,
    dataset_type,
):
    """
    원본 컬럼명이 이미 표준 컬럼명과 같은 경우에만
    자동 연결한다.

    비슷한 이름을 임의 추정해서 연결하지 않는다.
    """

    mapping = {}

    for field in get_standard_fields(
        dataset_type
    ):
        mapping[field] = (
            field
            if field in df.columns
            else None
        )

    return mapping
