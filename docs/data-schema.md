# Data Schema

## route_master.csv

| column | type | meaning |
|---|---|---|
| stop_id | string | 합성 배달점 ID |
| route_id | string | 집배구 ID |
| road_name | string | 가상 도로명 |
| building_no | int | 가상 본번 |
| building_sub_no | int | 가상 부번 |
| stop_type | string | residential / apartment / business |
| sample_x | float | 가상 X 좌표 |
| sample_y | float | 가상 Y 좌표 |

## delivery_results_YYYY_MM.csv

| column | type | meaning |
|---|---|---|
| delivery_date | date | 배달일 |
| route_id | string | 배달 당시 집배구 |
| stop_id | string | 배달점 |
| item_id | string | 합성 우편물 ID |
| item_type | string | registered / parcel |

## workload.csv

| column | type | meaning |
|---|---|---|
| month | YYYY-MM | 월 |
| route_id | string | 집배구 |
| workdays | int | 근무일수 |
| workload_index | float | 합성 업무강도 |
| delivery_hours | float | 배달업무시간 |
| travel_hours | float | 이동시간 |
| ancillary_after_departure_hours | float | 출국후 부대업무 |
| total_volume_avg | float | 합성 일평균 총물량 |
| registered_avg | float | 합성 일평균 등기통상 |
| distance_km_avg | float | 합성 일평균 이동거리 |

## gis_candidates.csv

| column | type | meaning |
|---|---|---|
| sender_route | string | 보내는 구 |
| receiver_route | string | 받는 구 |
| stop_id | string | 후보 배달점 |
| adjacency_score | float | 합성 인접도 |
| continuity_score | float | 합성 순로연속성 |
| candidate_flag | bool | 후보 여부 |
