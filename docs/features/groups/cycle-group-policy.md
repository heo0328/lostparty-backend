# 실제 주차별 그룹 정책·승계 계약

2026-10-30 / feat/raid-group-policy. [Issue16 전체27 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521839291)·[전체28 Flutter 문서](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521897849), Flutter 문서78e53aa0 기준이다. [전체29 Backend 후보 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6522746434) 후 구현한 신규 소비 계약이다. 구현·격리 검증·실제 반영·Flutter 연결은 별도 상태이며 이번 문서는 서버 반영 완료가 아니다.

## 원본과 전환

0035_cycle_group_policy의 recruitment_cycle_group_policies(cycle_id,generation,scope,group_id,revision)가 실제 주차/세대의 원본이다. 일반은 public/null, 그룹은 group/UUID다. 기존 현재 세대는 기존 방 값으로 초기 반영하되 public+연결은 public/null로 정규화한다. 과거 세대/원origin/완료/명령 이력은 재작성하지 않는다. 알 수 없는 과거 정책은 unavailable이며 새 권한을 만들지 않는다.

새 그룹 정책을 소비하는 요청은 기존 beta contract_profile과 별도로 query `group_policy_version=cycle-group-policy-1`을 사용한다. 이는 구정책 병렬 운영이 아닌 클라이언트의 새 검토/전환 계약 소비 표시다. 0035의 미표시 쓰기는 원래 operation/key/body hash로 성공 ACK를 먼저 복구하고, 성공 ACK가 없으면 CLIENT_UPGRADE_REQUIRED409다. 이행 시 고정한 DB 함수 `cycle_group_policy_cutover_at()`과 기존 RequestResult.record_created_at을 비교하므로, 토큰 없는 옛 미완료 요청에 새query만 붙여도 실행하지 않는다. 생성시각을 모르는 옛 요청도 거절하며 기존 요청행/해시/ACK는 수정하지 않는다. 이행 후 만들어진 새요청의 정상 재시도는 허용한다. 원ACK에 새 필드를 합성하지 않는다. 구 토큰을 새 표시 요청에 자동 대입하지 않는다. 기본0023 계약은 보존한다. 0034에 새 표시를 보내면 GROUP_FEATURE_NOT_READY503이며 실제0035 반영 전 새 명령을 기기에서 시험하지 않는다. 이 버전 표시는 로컬 Backend의 cycle router 전환용이며 로그인/그룹 자체 API에 추가하지 않는다. 새 실행은 cycle router의 query 표시와 토큰 내부 버전이 모두 맞아야 한다. query 자체는 원래 멱등 digest/namespace에 추가하지 않는다. 원ACK 응답에는 선택적 신규 root 필드를 합성하지 않고 원래 저장 응답을 반환한다.

## 설정·확인

기존 실제T 설정 GET/PUT을 확장한다.

| 동작 | 경로 | 입력/결과 |
|---|---|---|
| 현재T 설정 | GET `/v2/me/raid-rooms/{room_id}/settings` | target_cycle_key; root.group_policy에 원본 revision |
| 그룹 변경 검토 | GET `/v2/raid-rooms/{room_id}/command-context` | command=edit_group_policy, target_cycle_key, 선택 target_group_id |
| 설정/그룹 변경 | PUT `/v2/raid-rooms/{room_id}/settings` | 기존 설정·CAS + 선택 group_policy/context_token, 기존 Idempotency-Key |
| 공통 제목 검토/변경 | GET common-context / PUT common-settings | 기존 G1 검토, 쓰기는 expected_cycle_key/expected_room_revision/context_token/title만 |

`target_group_id`를 생략하는 것은 명시적인 일반 전환 검토다. 그룹 변경을 하지 않는 기존 숙련도/전투력/신청방식 변경은 group_policy/context_token을 생략한다. 이 경우도 새 실행의 query 표시는 필요하며 구 요청을 표시만 붙여 재전송해서는 안 된다.

 command-context의 command=edit_group_policy에서 target_cycle_key와 명시적 target_group_id(UUID 또는 생략=일반)를 검토한다. 응답 root.group_policy_effect는 실제T/세대와 before(scope/group_id/revision), after(scope/group_id)를 준다. 그룹 대상은 현재 공대장의 유효 가입/한도와 그룹 revision·membership 근거를 토큰에 결합한다.

PUT settings는 기존 필드에 group_policy={scope,group_id,expected_revision}와 context_token을 추가한다. 선택T 공대장만 쓰며 제목/G1·반대T를 변경하지 않는다. 그룹 정책만 바꾸려면 나머지 기존 설정값을 검토한 그대로 전송한다. 수정 후 root.group_policy는 해당T 정책이며 ACK는 root.group_policy_effects에 확정 전후를 제공한다. 제목은 기존 common-settings의 title-only 명령으로 분리한다. GET current_settings는 title만 주며 scope/group_id를 방 공통값으로 안내하지 않는다. 그룹만 변경하면 policy/settings/target revision과 해당T directory가 갱신되며 room/plan/반대T revision은 보존한다. 일반 설정도 같이 바꾸면 기존 계획 갱신 규칙을 유지한다. 검토 토큰은 120초/주차 경계 중 빠른 시각까지이며 ACK 저장 후 최종 만료도 rollback한다.

그룹 교체/일반 전환으로 기존 참가·pending·편성·예약/일정·완료를 삭제하거나 재구성하지 않는다. 신규 접근·신청/승인은 현재T 정책을 적용하며 과거 public 신청은 가입 검사 우회 근거가 아니다.

## 승계·개방

기존 membership-actions·N취소·직접 위임·복구를 확장한다. 같은 그룹의 자격 있는 실제 참가자 우선/기존 joined_order 순이며 없으면 prospective public 상태에서 나머지 후보를 검사한다. 순서·소유권·예약 등 불명확한 후보에 권한을 부여하지 않는다. 같은 그룹 후임이 없으면 public/null 전환과 승계/탈퇴를 한 트랜잭션으로 처리한다. 기존 명령별 거절/복구 경계를 유지한다.

membership-actions context의 `data.options.{action}.impact.targets[].group_policy_effect`와 ACK의 `data.effects[].group_policy_effect`에 전환을 명시한다. N취소 context는 `data.successor.group_policy_effect`, 직접 위임 context는 `data.candidates[].group_policy_effect`로 후보별 결과를 준다. N취소/위임 ACK는 root.group_policy_effects를 준다. 개방 context는 data.group_policy_effect에 출발 정책→새T 정책을 주며, ACK root.group_policy_effects는 생성된 세대와 확정 revision을 준다. 아직 없는 N에는 root.group_policy가 없고 생성 예정 효과만 존재한다. 기존N이면 현재 정책의 무변경 검토와 noop다. 모두 탈퇴는 각T 독립 계산·전체 명령 원자성 유지다. 없는 N의 개방은 sourceT를 상속하고 개방자가 유효 그룹원이 아니면 public/null을 확인한다. 기존N은 덮지 않으며 자동개방은 없다.

## 읽기·갱신

include_group_state=true의 room_groups를 cycle_groups로 대체한다. 원소는 room_id,target_cycle_key,room_cycle_id,generation,scope,group_id,revision,state(known/unavailable)다. 과거 generation을 현재 정책으로 대체하지 않는다. 동일 방/주차가 과거·현재 세대로 여러 번 반환되면 cycle_groups도 세대별로 제공한다. 기본/신청상세 배지의 위치와 membership-actions 현재읽기의 content.data.members 위치는 유지한다. root.group_policy는 해당 응답 대상의 메타데이터이며 unavailable은 scope/group_id/revision이 null이다. group_states의 그룹 이름/active·ended·unavailable 의미는 유지한다. 모든 상세/설정/reader profile·카드/검색/그룹필터·배지·그룹 활성모집 판정은 실제T 원본을 사용한다.

일반 전환에는 group_id=null이며 배지/그룹 분류를 제거한다. 원origin은 과거 신청 근거다. 반대T의 참가만으로 비공개T를 공개하지 않으며, 정확한 대상 참가/이력의 기존 조회는 유지한다. 그룹 목록에는 해당 그룹T만 포함하고 불명확한 해산 차단 근거를0으로 처리하지 않는다. 새 정책이 있어야 하는 explicit/현재 세대의 원본이 누락되면 보수적으로 unavailable이며 차단 수는 null이다. 무관한 legacy_unknown 자료를 신규 정책 누락으로 일괄 간주하지 않는다.

성공 후 ACK 영향T의 상세·설정/검토context·목록/그룹필터·후보·그룹 활성모집을 갱신한다. 반대T 값·독립 초안·미확정 다른 요청은 보존한다. 후속 조회 실패는 재명령 사유가 아니다.

## 검증·게시

고정 wire 원본은 [two-cycle OpenAPI](../../../openapi/two-cycle.openapi.yaml), 합성 context/전환/과거 unavailable은 [대표 예시](cycle-group-policy.examples.json)를 따른다. 예시는 전체 명령의 대체 본문이 아니며 token은 재사용 불가능한 placeholder다. [검증 기록](cycle-group-policy-verification.json)에는 실제 실행·반복/고유 시나리오와 미실행을 구분한다. 대표 오류는 CLIENT_UPGRADE_REQUIRED409, TARGET_CONTEXT_STALE409, TARGET_LEADER_REQUIRED403, GROUP_MEMBERSHIP_REQUIRED403, GROUP_NOT_ACTIVE409, REVISION_CONFLICT409, ROOM_REVIEW_REQUIRED409, ROOM_NOT_FOUND404다. group_policy 조합/대상 불일치는 INVALID_REQUEST400 또는 TARGET_SCOPE_MISMATCH400이다. 현재 API/DB0034·실행source2602e45는 아직 유지한다.


## 개발환경 적용 순서 (이번 구간에서는 미실행)

검증된 코드/계약 SHA를 선택한 뒤 사용자 승인된 반영 구간에서 기존 API/worker의 쓰기를 중지하고 현재 DB가0034인지 확인한다. 같은 기존 DB에0035를 전진 적용하고 새 후보 API/worker를 시작한다. 신규 정책표의 현재세대 대응·public/null 정규화와 기존 업무표/이력 보존을 확인하고 두전체계약·readiness·실제 HTTP/읽기·worker 상태를 검증한 뒤 Flutter 새계약 사용을 안내한다. 새로운 별도DB·이중운영/복원리허설·자료초기화는 추가하지 않는다.

0035 이후에는 방 공통값이 최신T 정책을 반영하지 않는다. 따라서0034 구API만 다시 실행하는 단독롤백은 허용하지 않으며 실패 시 쓰기를 중지하고0035 원본을 보존한 전진 보완으로 처리한다. 개발 API 교체 승인과 운영배포·dev/main통합·자료삭제는 별도다. 실제반영 전에는 기존source2602e45·DB0034가 실행 중이라는 사실을 유지한다.
