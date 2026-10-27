# 계정별 이용 한도

회원별 그룹 정원·가입 그룹 수·참가 방 수의 유효 한도와 현재 사용량을 조회한다. 한도는 개인 캐릭터의 아이템레벨이나 주간 완료 횟수가 아니다.

<a id="behavior"></a>

## 현재 동작

| 차원 | 기본값 | 적용 기준 |
|---|---:|---|
| group_capacity | 15 | 현재 그룹장의 계정값과 해당 그룹 현재 확정 회원 수 |
| joined_groups | 5 | 해당 회원의 현재 가입 그룹 수, 직접 생성 포함 |
| raid_rooms | 10 | 해당 회원의 현재 확정 참가 방을 room UUID별 중복 제거 |

GET `/v1/me/usage-limits`는 본인에게만 제공하며 쓰기 없이 한도·사용량·revision·상태·초과 사유를 반환한다. 없는 설정은 기본값을 투영하며 GET에서 설정행을 만들지 않는다. 미지원/확인 불가 집계를0·정상으로 표시하지 않고 null/unavailable을 구분한다.

정확히 한도면 새 증가를 제한하고, 초과면 해당 차원의 영향 범위를 판단한다. 단순 주차 전환·완료·예약 해제로 지속 참가 방 수를 임의 초기화하지 않는다. 초대/신청 pending은 확정 회원 수가 아니며 수락·승인의 최종 쓰기에서 다시 검사한다.

<a id="section"></a>

## 권한·연결

회원이 한도를 임의 PUT하는 API는 없다. 서버 내부의 권한 있는 변경·감사와 관계 쓰기는 같은 업무 잠금·트랜잭션 책임을 가진다. 그룹장은 자기 정원을 새 그룹장에게 그대로 넘기지 않으며 이전 시 새 그룹장의 수용 가능 여부를 검사한다.

개인 초과의 직접 참가 제한과 그룹 자체 정원 초과의 그룹 전용 방 영향은 구분한다. 기존 관계/자료를 지우거나 관계 정리를 막는 일반 사유로 확대하지 않는다. [그룹 관리](../../groups/management/README.md), [모집 참가](../../recruitment/participation/README.md).

<a id="decisions"></a>

## 주요 결정과 근거

한도와 현재 집계 원본을 분리하고 관련 관계 확정/종료와 함께 revision을 갱신한다. [확정 영향범위](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232669446), [공통 원본](../../../archive/work-records/features/groups/ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md). 결제·구독·기간권·운영자 공개 API는 이 기능에 포함하지 않는다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/me/usage-limits` |
