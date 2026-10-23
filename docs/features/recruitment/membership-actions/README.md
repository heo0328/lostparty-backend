# 탈퇴·추방·해산·공대장 복구

실제 주차 참가를 정리하는 행동을 구분한다. 명령 이름이 비슷해도 기존 leave/end/cancel·개인완료후탈퇴·현재/양주차 추방·새 일반 탈퇴/해산은 입력·원 효과·ACK가 서로 다르다.

<a id="section"></a>

## 현재 명령 구분

| 행동 | 현재 의미 |
|---|---|
| 개인 완료후T탈퇴 | 선택 raid만 manual 완료하고 본인T의 다른 active 참가를 정리. N·기존 완료·지속 관계 보존. |
| 현재만/양주차 동일회원 추방 | 카드의 source 실제T/CM을 고정하고 선택 option의 자격·영향을 원자 검증. 불가 both를 current_only로 fallback하지 않음. |
| leave_target / leave_all | 선택T 또는 전체 본인 주차 참가/지속 관계를 합의한 범위로 정리. 적격 후임 승계 또는 명시 review 상태를 남김. |
| dissolve_led_targets | 자신이 실제 리더인 모든 유효C/N 주차를 함께 해산. 다인 허용, 비대상T·완료 이력 보존. |
| recover_leadership | 명시 POST에서 복구 자격 재검사. 서버 계약과 제품 UX 승인은 별개이며 새 UI는 승인 전 제안. |

<a id="section-2"></a>

## context·동의·ACK

membership-action-context는 활성 지속회원에게 메뉴를 제공하되 각 옵션 권한을 따로 계산한다. 현재T 미참가/일반회원이어도 반대T의 적격 옵션을 읽을 수 있다. 불가 옵션은 impact/confirmation=null이다. GET은 권한·리더·자료를 변경하지 않는다.

POST는 합의된6필드와 선택 옵션 token을 사용한다. 사용자의 확인은 선택 영향에 결합하며 비선택 옵션 변화로 의미를 바꾸지 않는다. 선택 context의 대상 집합·후상태/revision을 재검사한 뒤 한 트랜잭션에서 C→N 순으로 적용한다. 공용 API 연속 호출이나 중간 commit을 하지 않는다.

전용ACK의 원Key/action/room/actor/당시C/viewT·영향T·세대·리더·후상태를 검증한다. 성공 후 GET403/404나 갱신 실패는 성공을 취소하지 않는다. effects=[]의 지속 관계 종료에도 가짜T를 만들지 않고 관련 목록·한도를 갱신한다. 구 pending의 원method/path/body/key/token/효과와 최대24시간 원ACK 복구는 유지한다.

<a id="section-3"></a>

## 승계·호환·기록

새 일반 탈퇴는 본인의 정리가 증명되면 적격 후임 부재 때문에 막지 않고 필요 시 null 리더·review/명시 복구 상태를 남긴다. 이것을 기존 개인완료후탈퇴의 SUCCESSOR_UNAVAILABLE 거절 정책에 소급하지 않는다. 새 일반 다인 해산도 기존 전역 마지막1인 종료와 별개다.

완료 Assignment·원 완료 근거·감사는 보존하고, 현재 관계 정리와 재참가의 새 CM/Assignment·가입 순번을 분리한다. 자기 종료 기록·profile은 [완료·기록](../completion-and-records/README.md)을 따른다. [정확한 명령별 계약](contract.md).

<a id="decisions"></a>

## 상태·결정 근거

Backend 구현·개발 반영 완료. Flutter A 전용context/원명령·ACK는6968f47a/177mock·분석0 보고를 수신했으나 실제버튼은구명령이고 B메뉴/성공사건·C기록Router·#24검색·실회원/기기 인수는 미완료다. 새 Backend 차단/반복시험 요청은 없다.

[새 정책·개발 인계](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996), [Flutter A 범위 보고](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371981415), [기존 원자 명령 원문](../../../archive/work-records/features/recruitment/development/ISSUE_22_23_ATOMIC_MEMBER_ACTIONS_DEVELOPMENT.md). 과거 명령 복구를 보존하기 위해 새 행동을 별도 transport/ACK로 제공했다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/raid-rooms/{room_id}/leave` |
| POST | `/v1/raid-rooms/{room_id}/end` |
| POST | `/v1/raid-rooms/{room_id}/removals` |
| POST | `/v2/raid-rooms/{room_id}/removals` |
| POST | `/v2/raid-rooms/{room_id}/leave` |
| POST | `/v2/raid-rooms/{room_id}/end` |
| GET | `/v2/raid-rooms/{room_id}/personal-completion-departure-context` |
| POST | `/v2/raid-rooms/{room_id}/personal-completion-departures` |
| GET | `/v2/raid-rooms/{room_id}/member-removal-context` |
| POST | `/v2/raid-rooms/{room_id}/member-removals` |
| GET | `/v2/raid-rooms/{room_id}/membership-action-context` |
| POST | `/v2/raid-rooms/{room_id}/membership-actions` |
