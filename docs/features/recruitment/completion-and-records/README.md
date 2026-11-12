# 완료·정정·보관 기록

본인 item·공대장 전체 완료, 본인 완료 근거 정정과 완료/종료 방의 기록을 관리한다. 완료 정정은 과거 참가·편성·예약 복원과 다르다.

Issue47 선택 레이드 일괄 완료는 [v3 전체 효과 표시·이력 집계](batch-completion-wire-v3.md)의 [공개 API·원자 명령](batch-completion-implementation.md)을 구현·게시/로컬 지원하고 Native 담당의 실제 연결/잔여 없음 확인 후 **사용자 지시로 completed 종료**했다. Backend 업무44eb4ba/게시624ef00, Native47a30dad 게시와 #48 후속 미게시 범위는 구분한다. [로컬 반영 기록](../../../engineering/operations/records/batch-completion-local-rollout.json)·[종료 근거](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6767992300)를 따른다.

<a id="behavior"></a>

## 현재 동작

2026-11-10 **완료 오류/계정 복구 구간의 사용자 기기 인수와 Native 게시가 완료**됐다. [인수 결과 원본](completion-recovery-acceptance-20261110.md)에서 완료 범위·시점·커밋·자동 검증·별도 후속을 확인한다. 기존 계정은 문구 수정 전에 이미 복구됐고, 최종 버튼은 ‘현재 정보로 화면갱신’이다. 같은 복구 재시험을 요구하지 않는다.

| 찾을 내용 | 문서 |
|---|---|
| 완료 profile 선언 보정·실제 로컬 반영 | [계약 보정](completion-profile-contract-fix.md) |
| 계정 정정/수동 완료의 group 옵션 | [BUG-033 최소 옵션](account-completion-group-profile-bug033.md) |
| 기존 무옵션 v3의 현재 상태 채택·로컬 대기 해제 | [BUG-033 복구 조건](bug033-current-state-adoption.md) |
| 두 key·공대/개인 완료의 도착 순서 | [좁힌 경합 확인](completion-retry-order-check.md) |
| 미해결 명령의 일반 한계/별도 공용 구조 제외 | [복구·충돌 조사](pending-recovery-and-conflicts.md) |
| 최초 완료 차단 원인/선언 누락 재현 | [초기 조사](completion-context-profile-audit.md) |

각 조사 문서의 당시 대기와 현재 완료를 구분한다. 누락 캐릭터/부분 완료 자료·기기 경계는 #17 잔여다. 묶음 선택 완료는 #47에서 구현·종료됐고 공통 복구 안내/일정 읽기는 #48에서 종료됐다. Penpot은 Native 차후 후속이며 두 이슈를 다시 보류하지 않는다. #17 복구 구간의 Backend/Native dev 통합은 완료됐고, #47/#48 후속 통합·운영 반영·Issue17 전체 종료와는 다르다.

선택 실제T의 command-context는 현재 권한·Round/Assignment·원장·예약·시각과 영향의 snapshot을 제공한다. 현재주와 수요일10시 이후 조건을 확인하며, 개인 완료는 본인 item, 전체 완료는 실제 해당T 공대장과 명령 범위를 검사한다. 다른 item/T의 완료와 자료를 보존한다.

본인 완료 정정은 별도 completion-correction-context와 POST를 사용한다. 실제 manual/party 근거·ownership·원장/대상 revision·source digest·서명 context를 확인하고 정정 감사·투영·원ACK를 원자적으로 저장한다. 다른 완료·과거 Assignment·참가·예약을 되살리지 않는다. 원pending의 실제T/C와 원ACK의 당시 시각을 대조하며 현재C를 덮어쓰지 않는다.

<a id="section"></a>

## 보관·기록 접근

전체 완료되고 열린 N이 없는 방의 논리 보관과 실제 데이터 삭제를 구분한다. current/ended/all 목록 의미는 실제 상태를 따르며 보관 상세/plan 읽기가 쓰기 권한을 재활성화하지 않는다.

새 `reader_profile=membership-actions-1`은 opt-in이다. 생략 시 기존 DTO를 유지하고 오타/미지원 profile이나 반쪽 기록 anchor는 거절한다. 종료 회원의 기록은 자기 membership_id+cycle_member_id와 방/T 귀속으로 확인하며, 그룹 탈퇴 뒤에도 허용된 자기 기록만 읽는다. 재가입으로 옛 기록의 ID가 새 쓰기 권한이 되지 않는다. [탈퇴·해산](../membership-actions/README.md).

<a id="constraints"></a>

## 비활성·미완료

이번주 미완료 종료·같은 주차 weekly_resume는 앱 활성 기능에서 제외한다. 서버 endpoint/권한·과거자료·pending/ACK 보존과 다음주 reopen은 유지한다. [비활성 보존 기준](inactive-features.md). 실제 회원·기기 전체 인수와 운영은 미완료이며, 기록 Router의 Flutter 연결도 명령 처리 구현과 구분한다.

<a id="decisions"></a>

## 주요 결정과 근거

완료 근거 정리와 참가 복원을 분리해 과거 증거를 덮어쓰지 않는다. [완료 정정·보관 구현](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360251618), [정정 원문](../../../archive/work-records/features/recruitment/development/ISSUE_13_COMPLETION_CORRECTION_DEVELOPMENT.md), [새 기록 접근 계약](../../../archive/work-records/features/recruitment/contracts/ISSUE_25_CONTRACT_REVIEW_V2.md).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/raid-rooms/{room_id}/weekly-resume-proposals` |
| POST | `/v1/raid-rooms/{room_id}/weekly-incomplete-closures` |
| POST | `/v1/raid-rounds/{round_id}/completion` |
| POST | `/v1/raid-rounds/{round_id}/personal-completion` |
| POST | `/v2/raid-rooms/{room_id}/weekly-incomplete-closures` |
| POST | `/v2/raid-rounds/{round_id}/completion` |
| POST | `/v2/raid-rounds/{round_id}/personal-completion` |
| POST | `/v2/raid-rooms/{room_id}/weekly-resume-proposals` |
| GET | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-correction-context` |
| POST | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-corrections` |
| GET | `/v1/raid-rooms/{room_id}/command-context` |
| GET | `/v2/raid-rooms/{room_id}/command-context` |

## Issue47 v3 실행 API

| Method | 경로 |
|---|---|
| GET | `/v2/raid-rooms/{room_id}/batch-completion-context` |
| POST | `/v2/raid-rooms/{room_id}/batch-completions` |
| GET | `/v2/raid-rooms/{room_id}/batch-personal-completion-departure-context` |
| POST | `/v2/raid-rooms/{room_id}/batch-personal-completion-departures` |
