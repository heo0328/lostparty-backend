# 참가·승인·캐릭터 변경

방의 실제 주차에 신청·직접 참가·승인하거나 참가 캐릭터를 명시적으로 교체한다. 지속 회원·그룹 가입만으로 실제 참가와 예약이 생기지 않는다.

<a id="behavior"></a>

## 현재 동작

admission-context는 선택한 실제T와 intent에 필요한 현재 자격·조건·정확한 revision/후보를 반환한다. 쓰기는 현재 회원·소유/활동·역할·레이드 레벨·주간 점유·한도·공개/그룹 권한·정원을 다시 검사한다. 일반 참가와 다음주 함께하기의 자격을 섞지 않는다.

신청 snapshot과 현재 자격은 다르다. 승인 시 최신 조건을 검사하며 마지막 자리·동일 회원 중복·주간 점유 경쟁을 같은 업무 트랜잭션에서 처리한다. 캐릭터 교체는 새 캐릭터의 현재 자격을 검증하고 기존 캐릭터의 예약·동의·정족수 영향을 합의된 범위에서 정리한다. 교체·재참가 뒤 과거 동의를 자동 복원하지 않는다.

기존 캐릭터의 소유/활동 이상은 검토 표시와 신규 사용 제한의 근거지만 이름 재사용한 타인에게 자리를 넘기는 근거가 아니다. 기존 관계를 정리하는 행동과 신규 참가를 분리한다.

<a id="section"></a>

## 조회·표시

상세·plan·본인 참가/신청은 현재 권한과 실제 T를 기준으로 읽는다. context의 opt-in session_display는 기존 실제 세션과 미생성 개방 일정 preview를 구분하며 없는 session UUID를 만들지 않는다. 표시 snapshot/token과 쓰기 자격은 각각의 역할을 유지한다.

완료/종료 기록의 권한과 current/ended/all·reader_profile은 [완료·기록](../completion-and-records/README.md), 명시 취소·일반 탈퇴·추방은 [관계 정리](../membership-actions/README.md), 주차 개방/승계는 [주차 관리](../weekly-cycles/README.md)를 따른다.

<a id="decisions"></a>

## 주요 결정과 근거

상태를 조회한 시점과 참가 확정 시점 사이 변경을 최종 검증으로 처리한다. [참가 구현](../../../archive/work-records/features/recruitment/development/ISSUE_13_W2_CYCLE_ADMISSION.md), [사전 표시 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6345290060), [표시 계약](../../../archive/work-records/features/recruitment/contracts/ISSUE_13_PREJOIN_SESSION_DISPLAY_DRAFT.md).

<a id="status"></a>

## 상태와 문서 연결

#26의 기존 신청 구성검사 보완은 source6e0063c·격리25PASS/개발 미반영이다. 최신 신청·캐릭터변경/역할전투력 요구는 [통합 자격 설계](eligibility-design.md)와 [보완 계약2](candidate-contract.md)를 검토 기준으로 사용한다. 두 문서는 설계/미합의·미구현이며 [제안1](candidate-proposal.md)은 이전 범위로 보존한다. [이전 구현/검증 기록](../../../archive/work-records/features/recruitment/development/ISSUE_26_APPLICATION_VALIDATION_DEVELOPMENT.md)·[검증 집계](validation/application-validation-results.json)는 신규 후보/변경 통합요구 완료 근거가 아니다.

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/raid-rooms/{room_id}` |
| GET | `/v1/raid-rooms/{room_id}/detail` |
| GET | `/v1/me/raid-room-memberships` |
| GET | `/v1/me/raid-room-applications` |
| GET | `/v1/raid-rooms/{room_id}/applications` |
| POST | `/v1/raid-rooms/{room_id}/applications` |
| GET | `/v1/raid-rooms/{room_id}/admission-context` |
| POST | `/v1/raid-rooms/{room_id}/join` |
| POST | `/v1/raid-room-applications/{application_id}/approve` |
| GET | `/v1/me/raid-rooms/{room_id}/plan` |
| GET | `/v1/raid-room-applications/{application_id}` |
| POST | `/v1/raid-room-applications/{application_id}/reject` |
| POST | `/v1/raid-room-applications/{application_id}/withdraw` |
| POST | `/v1/raid-rooms/{room_id}/character-changes` |
| GET | `/v2/raid-rooms/{room_id}/admission-context` |
| POST | `/v2/raid-rooms/{room_id}/join` |
| POST | `/v2/raid-rooms/{room_id}/applications` |
| GET | `/v2/raid-rooms/{room_id}/applications` |
| GET | `/v2/raid-room-applications/{application_id}` |
| POST | `/v2/raid-room-applications/{application_id}/approve` |
| POST | `/v2/raid-room-applications/{application_id}/reject` |
| POST | `/v2/raid-room-applications/{application_id}/withdraw` |
| GET | `/v2/raid-rooms/{room_id}` |
| GET | `/v2/raid-rooms/{room_id}/detail` |
| GET | `/v2/me/raid-rooms/{room_id}/plan` |
| GET | `/v2/me/raid-room-applications` |
| GET | `/v2/me/raid-room-memberships` |
| POST | `/v2/raid-rooms/{room_id}/character-changes` |
