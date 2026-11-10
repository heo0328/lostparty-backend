# Issue47 선택 레이드 일괄 완료 계약 제안

현재 구분: 이 파일은 최초 제안/보완 경과다. [v3 계약](batch-completion-wire-v3.md)·[구현/게시/로컬 지원](batch-completion-implementation.md)이 최종 기준이며 #47은 사용자 승인 completed 종료다. 아래 미구현/Native 대기는 제안 당시 기록이다.

2026-11-10 / 상태: **Native 소비 검토·합의 대기, 미구현**. [Issue47 요청 원문](https://github.com/heo0328/lostparty-backend/issues/47)을 기준으로 사용자 승인 계획을 구체화했다. 브랜치 `feat/raid-batch-completion`, 기준 `084a6af`. 문서·예시는 로컬 미커밋·미push이며 실행 OpenAPI·서버 지원을 뜻하지 않는다. 공식 제안은 Issue 댓글에 본문으로 전달한다.

[공식 Backend 계약 제안](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6759461926)을 게시했다. 다음 담당은 Native 소비 검토·합의이며 현재 구현 지원은 없다.

## 최신 v3

[전체 효과 표시·이력 집계 v3](batch-completion-wire-v3.md)가 현재 제안이다. 아래 v2의 보존 ID 배열/이력 상한은 최신 구현 기준이 아니다.

## v2 보완 제안

Native 요청에 따라 [정확한 wire·revision/탈퇴 대조 v2](batch-completion-wire-v2.md)와 전체 응답/JSON Schema를 작성했다. 아래 v1의 개략 설명보다 v2가 우선한다. 최종 합의·기능 구현은 아직 미완료다.

## Native 전체2번째 검토 수신 — 당시 보완 요청

[전체2번째 Native 계약 검토](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6759918260)는 전용4경로·원자 처리·기존 단건 복구 보존 방향을 수용했다. 최종 합의는 아직 아니다. 다음 담당은 Backend다.

1. 실제 query는 `contract_profile=beta-recruitment-1`이다. 최초 제안의 `beta-recruitment-wire-2`는 계약 version과 혼동한 잘못된 값이며 변경 의도는 없다. 코드 beta_profile.PROFILE과 기존 beta-contract-wire 문서로 확인해 이 로컬 원본을 정정했다. 최초 댓글 정정 회신은 아래 보완과 함께 진행해야 한다.
2. context/ACK 전체 필드의 타입·필수/nullable·추가 필드 정책, 허용/권한 거절 전체 응답 예시, display/효과 집합별 상한을 구체화해 전달해야 한다. 현재 효과 발췌 예시는 전체 응답 계약이 아니다.
3. ACK revisions의 resource/ID·전이 규칙과 개인 탈퇴 후 state·leadership·successor의 원 context 대조 기준을 확정 제안해야 한다.

위 요청 수신 시점에는 사실 정정만 완료했으며 이후 v2 전체 wire/예시를 보완했다. 공식 회신과 최신 담당은 NEXT_WORK를 따른다. 기존 댓글 원문은 당시 제안으로 보존한다.

## 목적과 보존 흐름

공대장은 선택 round의 활성 참가자 전원을 party 원천으로 완료한다. 개인은 선택한 본인 활성 참가를 manual 원천으로 완료하고, 미선택 본인 활성 참가를 취소한 뒤 해당 주차에서 탈퇴한다. 기존 완료·다음주·타인·지속 소속을 보존한다. 내 계정 개별 완료는 기존 단건 경로를 유지한다. 기본 전체 선택/부분 선택·0개 실행 금지·레이드 이름 세로 체크박스 UX는 Native 요청을 따른다.

전용 API로 기존 DTO/원query·본문·token·key·namespace·원ACK를 보존한다. Native 단건 반복/병렬 호출로 원자성을 대체하지 않는다. 새 큐·다중 저장·원pending 자동 정리·완료/자료 초기화는 포함하지 않는다.

## Wire 제안 v1

공통 prefix는 `/v2/raid-rooms/{room_id}`다. 이 문서의 새 필드·경로는 합의 전 제안이다.

| 동작/action | Context GET suffix | POST suffix | operation |
|---|---|---|---|
| `batch_completion` | `/batch-completion-context` | `/batch-completions` | `batch-complete` |
| `batch_personal_completion_departure` | `/batch-personal-completion-departure-context` | `/batch-personal-completion-departures` | `batch-depart` |

GET 필수 query는 `target_cycle_key`(기존 CycleKey), `round_ids`(JSON UUID 문자열 배열을 URL 인코딩한 단일 query 값, 최대512 UTF-8 bytes)다. 둘 다 중복 query key는 거절한다. round 집합은 1~5개·중복 금지이며 UUID 문자열 표준화 후 소문자 UUID 문자열 오름차순으로 반환한다. POST도 중복·0개·6개 이상은 거절한다. 선택 배열 순서는 집합 의미에 영향을 주지 않지만 pending의 원문/fingerprint는 그대로 보존하므로 재전송 때 배열을 재작성하지 않는다. Native는 context가 반환한 정렬된 명령 값을 그대로 사용한다.

공통 명령 필드(모두 필수, 추가 필드 금지):

| 필드 | 의미 |
|---|---|
| `expected_cycle_key`, `target_cycle_key` | 원 context의 현재C와 실제T. 기존 CycleKey 형식 |
| `room_cycle_id`, `target_generation`, `expected_target_revision` | 대상 cycle/세대/CAS. revision은 기존 Version 범위 |
| `actor_cycle_member_id`, `expected_cycle_member_revision` | 실제T의 행위자·revision |
| `round_ids` | 위 선택 집합 |
| `context_token` | 불투명 token, 최대4096 UTF-8 bytes |

인증·명령 key 헤더·응답 크기1MiB·no-store·기존 오류 envelope를 재사용한다. 토큰 유효기간은 기존처럼 발급 후120초와 주차 종료 중 이른 시각이다. 새 버전 profile은 만들지 않는다. `group_policy_version=cycle-group-policy-1`, `participation_profile=remaining-active-1`, `contract_profile=beta-recruitment-1`의 기존 지원/필수 조건을 적용하고 새 네 경로의 query 허용·OpenAPI 선언을 실제 HTTP와 일치시킨다. 생략 가능 조건과 해당 세대의 필수 capability를 혼동하지 않는다. 토큰은 세 profile의 실제 사용 여부/값을 결합·검증한다.

### Context

응답은 기존 policy envelope의 선택적 group metadata, 기존 `scope`, 다음 `data`를 사용한다.

- `action`, `room_id`, `actor_cycle_member_id`, `actor_cycle_member_revision`, `round_ids`.
- `display`: `rounds`(선택 round별 round/item/raid ID·raid_name·difficulty ID/name·catalog_version), `assignments`(영향 범위의 assignment/round/membership/cycle_member/character ID·character_name·effect), `display_revision`(표시 자료 SHA256). effect는 `complete`, `cancel`, `preserve_completed`, `preserve_active` 중 하나다. 선택 목록에서 난이도를 숨겨도 DTO의 난이도 근거는 보존한다.
- `impact`: `completed_assignment_ids`, `cancelled_assignment_ids`, `preserved_completed_assignment_ids`, `preserved_active_assignment_ids`, `released_reservation_count`, `preserves_other_cycles=true`, `preserves_global_membership=true`.
- `departure`: 공대는 null, 개인은 `{effect, successor}`. effect는 기존 `leave/automatic_successor/close_completed/close_incomplete`, successor는 기존 Successor DTO 또는 null이다.
- `permission`: 기존 Permission. `confirmation`: 허용 시 기존 `{context_token, issued_at, expires_at}`, 불가 시 null.

공대의 assignment 집합은 해당 현재 세대/현재 round들의 전체 참가 범위, 개인은 본인 cycle member의 참가 범위다. 개인의 preserved_active는 항상 빈 배열, 공대의 cancelled는 항상 빈 배열이다. 집합별 assignment 최대40개(개인은5개), 모든 ID 목록은 중복 없이 오름차순이다. 서로 다른 effect 집합은 겹치지 않는다. 이미 취소/중단된 과거 참가를 현재 완료/보존 집합으로 합성하지 않는다. 현재 세대 자료의 귀속/상태를 설명할 수 없으면 기존 검토 필요 오류로 거절한다.

형식/범위/선택 자체가 유효하지 않으면 오류 응답을 반환한다. 유효 대상이나 시각·권한·후계자 조건으로 실행 불가하면 permission 거절과 confirmation=null을 반환한다. 불가 context의 impact는 예상 영향일 뿐 실행 근거가 아니다.

### ACK

응답은 같은 envelope/`scope`와 `data`를 사용한다. data 필드는 `command_id`(UUID4), `action`, `outcome=applied`, `executed_at`, `room_id`, `actor_cycle_member_id`, `round_ids`, `impact`, `departure`, `revisions`다. impact/departure는 실제 확정 효과를 반환한다. revisions에는 변경된 cycle/세대·plan/members·cycle member·round·assignment의 ID/최종 revision을 기존 revision 표기 방식에 맞춰 제공한다. scope 역시 실행 후 revision이다. Native는 원 context와 선택·효과 집합/탈퇴 결과를 대조하며 현재 GET을 원ACK로 대체하지 않는다.

[합성 예시](examples/batch-completion-proposal.json)는 공대 부분 완료/개인 부분 완료 후 탈퇴의 query·본문·예상/ACK 효과 발췌다. 전체 응답 fixture나 실제 서명 token이 아니다.

## 트랜잭션과 정책

`cycles.execute`의 기존 직렬화·인증·사전 reconcile/권한 가드·원ACK 우선 재생·최종 검사 흐름을 재사용한다. 사전 시각 효과는 명령 업무 효과의 rollback 범위와 구분한다. `recruitment-v2-`/`beta-v2-` 접두사와 새 operation을 조합하며 길이32 제한을 만족한다. 같은 key라도 기존 단건 operation과 혼용하거나 원ACK를 변환하지 않는다.

1. 잠금 안에서 전체 선택의 room/T/현재 generation·current round·active 상태와 actor 권한을 확인한다. 각 선택 round에 완료할 활성 참가가 있어야 한다. 다른 방/T/세대·누락·기존 완료 round는 전체 거절한다.
2. 원장·점유·예약·assignment 귀속 및 필요한 소유/자격·정책/일정·세대/멤버 revision을 검증하고 context digest를 재계산한다. 개인은 기존 `atomic_members` 자격/승계 규칙, 공대는 기존 완료 권한을 보존한다. 모든 대상 검증은 첫 업무 쓰기 전에 끝낸다.
3. 공대는 선택 활성 참가를 party 완료하고 선택 round만 completed로 전환한다. 기존 완료 원장 시각/난이도/party/manual 근거는 덮어쓰지 않는다. 미선택 활성 참가·round는 유지한다. 멤버 완료와 세대 종료는 전체 선택 적용 후 기존 조건으로 한 번 판정한다.
4. 개인은 본인 선택 활성 참가의 manual 완료·미선택 활성 취소·주차 탈퇴를 수행한다. 기존 완료 참가가 예전 캐릭터여도 원근거를 유지한다. 후보 승계/후계자 부재 거절을 보존하며 마지막1인의 종료 상태는 선택 전체와 기존 완료 근거를 반영한다. 타인 원장·다음T·지속 소속은 변경하지 않는다.
5. 점유/예약·참가/일정/제안 정리·감사 이벤트·revision·ACK를 단일 트랜잭션에 저장한다. 변경하지 않은 기존 완료의 revision은 인위적으로 올리지 않는다. 최종 시각/토큰/주차 검사가 실패하면 해당 업무 변경·성공 ACK 전체를 rollback한다.

HTTP400 `INVALID_REQUEST`(형식/선택 개수/중복), `TARGET_SCOPE_MISMATCH`/`CONTEXT_INVALID`(범위·토큰), 403 기존 권한 오류, 409 기존 `ROUND_NOT_ACTIVE`·`TARGET_CONTEXT_STALE`·`REVISION_CONFLICT`·시각/주차/만료·승계 오류, 503 기존 준비 오류를 사용한다. 정확한 오류 우선순위는 기존 guard 순서를 따른다. 새 code/details.reason은 만들지 않는다. 구형 서버 새 경로404/미지원은 지원 부재이며 단건 반복 호출·기존 pending 변경·자동 새 key 발급으로 우회하지 않는다.

기존 원장/이벤트 JSON/ACK 저장소를 쓰므로 migration 계획은 없다. 필요해지면 원인·최소 변경·백업 영향을 먼저 제안한다. 신규 업무는 outcomes, DTO는 schemas, HTTP는 api, 시험은 해당 기능 하위에 둔다. 공유는 트랜잭션 내부 도우미로 제한하고 단건 공개 command를 호출/반복 commit하지 않는다.

## 검증·합의·인계

- 격리 PostgreSQL: 8인×5개 전체/부분 공대 완료, 개인 전체/부분 완료·미선택 취소, 기존 완료/다음T/타인/지속 소속 보존.
- 다른 상태 전이: 일반 탈퇴·공대장 자동 승계·후계자 부재 전체 거절·마지막1인 전체 완료/부분 취소 종료. 같은 인원수만 늘린 중복 시험은 추가하지 않는다.
- 거절/rollback: 빈·중복·초과 선택, 외부 방/T/세대·누락·완료 대상, 위조/권한/profile 불일치, stale/만료/주차 경계, 중간 쓰기·ACK 저장/최종 검사 실패. 원장·점유·예약·관계·이벤트·ACK의 원자성을 확인한다.
- 경합/복구: 겹치는 두 batch, batch와 기존 단건/탈퇴/캐릭터 교체, 동일 key 원ACK·변경 본문 충돌·주차/권한 변경 후 원ACK 재생. 기존 단건 pending/DTO/ACK 회귀를 유지한다.
- HTTP/계약: 실제 query→context→POST→ACK, raw query와 OpenAPI 허용/선언 일치·프로필 조합·no-store, 두 전체 생성 계약 비교. 기본 계약 보존·two-cycle 합의 추가만 허용한다.

**다음 Native:** 새 네 경로·round 집합/정렬·context/ACK 효과 대조·profile·구형 서버 미지원 및 기존 단일 저장/복구 연결 가능 여부를 검토하고 같은 Issue에 수용/차이를 회신한다. Backend는 합의 후에만 코드/실행 OpenAPI를 구현한다. 계약안 검토에 기기 시험은 요청하지 않는다.

**후속 Backend:** 합의 → 구현/격리 검증 → 사용자 지시 범위의 게시/로컬 반영 → 고정 SHA·전체 OpenAPI 경로/hash·실제 지원/미반영 상태 인계. Native 연결/자동 검증·사용자 기기 인수·운영은 별도다. commit/push/merge·배포·자료 삭제·Issue 종료를 자동 실행하지 않는다.
