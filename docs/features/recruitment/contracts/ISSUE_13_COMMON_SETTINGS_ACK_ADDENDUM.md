> **현재 구현 기준(2026-10-21):** [전체84번째 Flutter · 계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083)에서 잔여 충돌 없이 소비 검토를 마감했다. 계약0.4.1/policy4를 고정하며 [W1~W5 작업계획](../planning/ISSUE_13_TWO_CYCLE_WORK_PLAN.md)을 따른다. 아래 검토대기/후속질문·구판 단계표는 당시 기록이다. 실제 기능/실행API·DB 인수는 별도 미완료다.

# Issue #13 계약4판 보완 — 공통 설정 성공 ACK

2026-10-21 / Backend / feat/raid-recruitment / HEAD6490f69, 실행 구현 cc003e9 계열. 설계·도구 미커밋/미push. [Flutter 전체82번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6309858607)의 마지막 한 항목에 대응한다. 기존 네 항목은 검토 완료이며 재검토를 요청하지 않는다. 실행 앱/원본 openapi/openapi.yaml·DB·서버·실제 자료는 변경하지 않았다.

## 응답 계약

PUT `/v2/raid-rooms/{room_id}/common-settings`의 200을 `Ack`에서 `CommonSettingsAck`로 교체한다. 요청은 기존 `CommonSettingsCommand` 그대로다. GlobalScope는 server_now/current_cycle_key/policy_version만 포함하고 target_cycle_key/playable_from/phase를 요구하지 않는다.

```json
{
  "scope": {
    "server_now": "2026-10-21T03:00:00Z",
    "current_cycle_key": "2026-10-21",
    "policy_version": "two-cycle-contract-4"
  },
  "data": {
    "command_id": "00000000-0000-4000-8000-000000000012",
    "outcome": "applied",
    "executed_at": "2026-10-21T03:00:00Z",
    "room_id": "00000000-0000-4000-8000-000000000006",
    "room_revision": 8,
    "affected_cycle_keys": ["2026-10-21", "2026-10-28"]
  }
}
```

위 식별자는 합성이다. wrapper와 data는 위 속성을 모두 필수로 요구하는 닫힌 객체다. room_revision은 양의 정수, affected_cycle_keys는 실제 영향 주차의 중복 없는 날짜 배열(0..2)이다. command_id UUID/outcome applied|noop/executed_at date-time은 기존 명령 ACK 의미를 유지한다.

- applied: 성공 후 room_revision과 실제 공통설정 영향 주차 목록을 반환한다. C/N 공존 예시는 7→8, 목록[C,N]이다. C가 없고 N만 존재하면 목록[N]이다. 없는 C를 만들거나 가짜 target revision을 채우지 않는다.
- noop: 동일 설정이면 room_revision 유지, affected_cycle_keys=[]이다.
- 공통 변경은 title/공개범위 등 합의된 공통 설정에만 작용한다. 주차별 리더·참가·예약·완료를 변경하지 않는다. ACK 목록은 회차별 참가 명령이나 권한을 뜻하지 않는다.
- G1은 C 공대장이 기본이며 **C 회차 행 자체가 없는 경우에만 N 공대장**이다. 닫힘/review C가 있으면 N으로 권한이 넘어가지 않는다. context.authorization_cycle_key는 권한 근거이며 ACK의 단일 target를 구성하는 값이 아니다.
- 같은 Idempotency-Key·불변본문 재시도는 원 성공200을 context만료/주차경계/권한 재검사보다 먼저 복구한다. 원 scope.server_now/current_cycle_key·executed_at·room_revision·영향목록을 바꾸지 않는다. 이는 과거 수행결과이며 현재 권한/현재 방 상태 증거가 아니다. 다른 본문 재사용은 기존 멱등 충돌 규칙을 유지한다.

## 출처·검증

C/N 공존과 N만 존재하는 두 사례 모두 실제 common-context GET200 → PUT requestBody → PUT200 schema를 조회하여 검증한다. 요청의 expected_cycle_key/expected_room_revision/context_token은 context data에서, group_id/expected_group_revision은 current_settings에서 얻는다. title/scope는 사용자의 편집 입력이다. 클라이언트에 주차 추정/CAS 상수/새 사용자 조작을 요구하지 않는다.

합성 사례는 기존70개를 보존하고14개를 추가한 **84개**다. 두 흐름6사례, 원ACK 동일 replay2사례, noop1사례, room_revision/영향목록 누락·가짜 scope/data target·중복주차 거절5사례를 포함한다. replay 사례는 값 동일성과 schema만 검증하며 실제 멱등 저장소 동작을 실행한 것이 아니다.

전체 **53경로/56동작/204schema**, info.version=0.4.1, 정책버전4/operationId는 유지한다. 이전4판과 비교해 기존 schema는 모두 동일하고 common-settings PUT의 성공 응답/설명과 전용 schema2개·info.version만 바뀌었다. 생성 이후 참가·탈퇴·위임·완료의 T별 독립 정책은 그대로다.

```bash
python3 docs/features/recruitment/artifacts/build_issue13_two_cycle_contract.py
python3 docs/features/recruitment/artifacts/build_issue13_two_cycle_examples.py
python3 docs/features/recruitment/artifacts/validate_issue13_two_cycle_contract.py
```

schema 메타/내부ref/required-property·전체84사례·기존global CAS6쌍·실제endpoint 흐름2개 검증 통과. 제공 보완 도구를 기존81번째 원문 도구에 적용한 격리 재현에서도 전체 명세/예시가 로컬과 동일했다. canonical SHA256: `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1`.

정식 OpenAPI validator/실행 FastAPI 비교·HTTP·DB경합/성능·실회원/기기 시험은 미실행이다. 이번은 명세 후보 검토 인계이며 기능 구현 시험 요청이 아니다. 다음 Flutter는 이 ACK 한 항목만 재대조하고, Backend는 남은 충돌 유무 확인 후 계약 고정/W1~W5로 진행한다.

인계: [전체83번째 Backend 회신](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310051618) (게시 전문·원격 내용 일치 확인). 다음 담당 Flutter: 공통 ACK 한 항목 재대조 대기.
