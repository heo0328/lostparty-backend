# 가능 시간·일정 조율·명시 확인

개인의 주간 가능 시간을 저장하고, 방·실제 주차의 제출표를 기준으로 일정을 조율·제안·명시 확인한다. 개인표·제출표·제안 수락·예약은 서로 다른 상태다.

<a id="behavior"></a>

## 현재 동작

개인표 GET/PUT은 본인 원본만 저장한다. 방 제출은 실제 T/generation/CycleMember에 귀속한 명시 snapshot이며 개인표 수정이 모든 방 제출을 자동 변경하지 않는다. schedule-context는 권한 범위의 제출표·익명 busy를 읽고 본인의 overlap은 실제 활성 예약 기준으로 조회한다.

일정 그룹·후보 계산은 제출표 교집합·개시 하한·시각/기간·현재 예약을 사용한다. 조회는 읽기 전용이며 제안·선택·예약을 자동 적용하지 않는다. 이미 확정된 초기 일정은 표 재제출·인원 변경만으로 이동하지 않는다. 조율형 선택에 임의 수동 시각을 주입하지 않는다.

변경 제안은 실제 session·일정 revision·item 기간을 고정한다. 현재 CM revision의 명시 응답과 세션별 정족수를 검사하고 여러 타임이 모두 충족된 뒤 함께 적용한다. N1=1도 별도 본인 응답이 필요하다. N2 이상 제안자는 본인1표를 기록하지만 생성만으로 적용하지 않는다. 정족수는 N2=2/N3·4=2/N5·6=3/N7·8=4다.

<a id="section"></a>

## 명시 확인·보존

명시 수락·참가 확인은 개인표 밖·예약 중복만으로 거절하지 않는다. 확정/변경 시 수락자의 새 예약·불변 동의를 남기고, 미동의자의 해당 이전 예약은 해제해 확인 대기로 둔다. 취소·재참가·캐릭터 교체 후 옛 표·예약을 자동 복원하지 않는다.

일정·제안·투표·해제 예약·당시 캐릭터/표 snapshot은 이력으로 보존한다. 계산 중 시각/자격 변화는 최종 DB 검사와 rollback으로 처리한다. 같은 주차 재개 관련 표시·제안은 [비활성 보존](../completion-and-records/inactive-features.md)을 따르며 일반 일정 제안과 구분한다.

<a id="decisions"></a>

## 주요 결정과 근거

개인표 변경을 타인의 확정 일정 변경으로 해석하지 않고 실제 동의를 보존한다. [명시 제출·예약](../../../archive/work-records/features/recruitment/development/ISSUE_13_W4A1_SUBMISSION_CONSENT.md), [일정 정족수·원자 적용](../../../archive/work-records/features/recruitment/development/ISSUE_13_W4A2_CYCLE_PLANNING.md), [일정 구현 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6316089641).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/me/raid-rooms/{room_id}/schedule-context` |
| GET | `/v1/me/raid-schedule-overlaps` |
| GET | `/v1/me/play-availability` |
| PUT | `/v1/me/play-availability` |
| GET | `/v1/me/raid-rooms/{room_id}/availability-submission` |
| PUT | `/v1/me/raid-rooms/{room_id}/availability-submission` |
| PUT | `/v1/raid-rooms/{room_id}/schedule-groups` |
| GET | `/v1/raid-schedule-groups/{group_id}/candidates` |
| POST | `/v1/raid-schedule-groups/{group_id}/selections` |
| POST | `/v1/raid-rooms/{room_id}/schedule-proposals` |
| POST | `/v1/raid-schedule-proposals/{proposal_id}/responses` |
| POST | `/v1/raid-sessions/{session_id}/participation-confirmations` |
| GET | `/v2/me/raid-rooms/{room_id}/availability-submission` |
| PUT | `/v2/me/raid-rooms/{room_id}/availability-submission` |
| GET | `/v2/me/raid-rooms/{room_id}/schedule-context` |
| GET | `/v2/me/raid-schedule-overlaps` |
| POST | `/v2/raid-sessions/{session_id}/participation-confirmations` |
| PUT | `/v2/raid-rooms/{room_id}/schedule-groups` |
| GET | `/v2/raid-schedule-groups/{group_id}/candidates` |
| POST | `/v2/raid-schedule-groups/{group_id}/selections` |
| POST | `/v2/raid-rooms/{room_id}/schedule-proposals` |
| POST | `/v2/raid-schedule-proposals/{proposal_id}/responses` |
