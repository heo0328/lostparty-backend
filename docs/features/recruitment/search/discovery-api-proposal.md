# 모집 탐색 리마스터 — Issue50 Backend 계약 제안

2026-11-12 KST. [전체4번째 Native 수용](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6820418957)으로 기본/추가 계약을 고정했다. 현재 구현·검증·로컬 실행·게시 상태는 [구현 인계](discovery-implementation.md)를 따른다. 아래는 b03595a 기준 조사와 전체1/3 게시 당시 제안/추가 협의 원문이다. 원문의 미구현/Native 검토 대기 문구는 각 게시 시점이며 현재 상태를 대신하지 않는다.

## 현재 소스에서 확인한 사실

- [라우터](../../../../app/raid_rooms/api/cycle_router.py)의 POST `/v2/raid-rooms/search` → [cycle_queries.search](../../../../app/raid_rooms/reads/cycle_queries.py). GET `/v2/raid-rooms`도 같은 서비스의 adapter다. v1 검색은 별도 호환 경로다.
- Backend 입력은 이미 `limit` 정수 1..50, cursor 최대2048자다. Native 본문에 나온 limit20/rows<=20은 현재 소비 계약이다. 서버의 50개 신규 지원과 Native의 상한 변경을 혼동하지 않는다.
- [읽기 경계](../../../../app/raid_rooms/reads/queries.py)는 PostgreSQL REPEATABLE READ/READ ONLY 트랜잭션 하나에서 인증·권한과 서버 시각을 읽는다. 외부 provider 호출·예약·쓰기는 없다.
- 실제T/세대·가시성·그룹/회원/캐릭터·레이드/난도·자리·숙련도·본인 실제 참가 제외와 베타 날짜/상태 조건을 SQL에서 정렬/페이지 이전 적용한다. 방별 활성 assignment lease의 distinct membership 수를 인원 정렬/자리 계산에 사용한다. README의 '지속 회원 인원' 설명보다 현재 코드/생성 계약의 실제T 인원 정의가 정확하다.
- 정렬은 member_count ASC/DESC, 동률 created_at DESC/room_id DESC다. 서명된 offset cursor로 limit+1행을 조회한다. keyset 페이징은 현재 구현이 아니다.
- 현재 응답은 scope와 data(items/directory_revision/filter_scope_digest/next_cursor/evaluated_at). 전체 count 쿼리는 없다. 인원수용 상관 count와 전체 검색결과 count는 다르다.
- [cycle_card_batch.load](../../../../app/raid_rooms/reads/cycle_card_batch.py)가 선택된 행의 대표/인원/항목/일정 등을 일괄 조회한다. 다만 [beta_output.enrich](../../../../app/raid_rooms/common/beta_output.py)의 카드별 RoomCycle 조회·beta_schedule 생성과 그룹 projection 등은 별도 비용이며 전체 경로가 N+1 없이 일정 쿼리 수라고 단정하지 않는다.
- cursor는 회원/세션·실제T·profile, 정규화 조건(limit 포함)·context·그룹권한 revision·directory head·베타 시각 전이 due 집합을 결합한다. scope 위조/교차는400 INVALID_REQUEST, 같은 scope의 revision 변경은409 CURSOR_STALE다. filter_scope_digest는 그룹 context digest로, 전체 결과의 재검증 토큰이 아니다.

## 추천 구조와 대안

추천은 **기존 POST `/v2/raid-rooms/search`에 `response_profile=discovery-1` query를 추가하는 단계 전환**이다. 생략은 기존 strict 응답 그대로, 미지원 값은400 INVALID_REQUEST다. 기존 `contract_profile=beta-recruitment-1`은 업무/일정 정책 선택이며 response_profile과 역할이 다르다. 기존 beta/group 정책 선택을 유지하고 응답 모양만 명시적으로 고른다. 별도 discovery/search·count·재검증 endpoint는 만들지 않는다. 이전 로컬 초안의 별도 탐색 endpoint 우선 추천은 철회한다.

| 기존 API | 처리·이유 |
|---|---|
| POST /v2/raid-rooms/search | 개선 대상. 기존 필터/권한 SQL을 공통으로 쓰고 새 profile에 전체 count와 최소 카드 projection 추가 |
| GET /v2/raid-rooms | 기존 목록 adapter 유지. 새 탐색은 POST를 사용하며 GET에 신규 기능 중복 추가 없음 |
| GET /v2/me/raid-room-filter-context | 그룹원 참조·권한 context 제공 역할로 유지 |
| GET /v2/groups/{group_id}/raid-room-character-candidates | 캐릭터 후보와 검증 token 제공 역할로 유지 |
| 그룹원 projection API | Native 사용 화면/목적 확인. 새 탐색의 필수 반복 호출로 추가하지 않음 |
| 기존 상세/신청/관리/reader | 재사용. 카드별 상세 선조회 없음 |
| v1/기존 응답 분기 | 이번 삭제 없음. 소비 종료·구버전 지원 종료를 확인한 범위만 후속 정리 |

기존 검색을 호출해 풍부한 카드를 생성한 뒤 버리는 방식 대신 조건 정규화/권한/필터 query를 공통화하고 profile별 count/카드 projection을 만든다. 새 DB 테이블/검색 스냅샷 저장소는 만들지 않는다. 새 endpoint는 피하지만 응답 profile/DTO·검증 분기 비용은 발생한다. 기존 응답 일괄 교체안은 옵션 없이 단순해지는 대신 운영 중 strict 소비자의 동시 전환이 필요하므로 단계 전환을 추천한다. API가 존재한다는 이유만으로 영구 보존하지 않으며 실제 사용처와 구버전 지원 근거로 정리한다.

## 공개 DTO 초안

요청은 현재 BetaSearchRequest의 조건을 그대로 재사용한다. 필수 category/admission_scope(null 허용)/group_ids/filter_context_token(null 허용)/member_conditions/raid_ids/difficulty_ids/target_cycle_key/limit/cursor(null 허용), 선택 sort/remaining_slot_counts/experience_levels/group_character_candidates_token/departure_windows/schedule_states를 유지한다. 무필터 배열/생략/null 규칙도 현재 검증과 같게 한다. limit은 필수 1..50, 첫 요청 cursor=null, 추가 요청은 같은 limit·적용조건을 사용한다. sort 생략/null은 member_count descending으로 정규화한다. 조건 배열의 집합 정규화 후 digest를 만든다. 후보 token은 기존 수명/권한 검증을 그대로 거친다.

시간 구간은 최대16개, 상태는 최대9개, 구간 시작포함/끝제외·UTC 정수분·양수/최대24시간·선택 주차 내부를 유지한다. 자정은 날짜가 다른 양끝으로 명시하고 중첩/인접 구간은 서버가 병합한다. 현재 서버는 주차 밖 구간을400으로 거절한다. UI에서 주차에 맞게 clipping한 구간을 보내는 정책과 서버가 묵시적으로 clipping하는 동작을 혼동하지 않는다. 그룹OR·회원AND·동일 회원 캐릭터OR, context/member_ref와 후보 token, 본인 선택T participating/review_required 제외를 보존한다.

응답 envelope는 기존 scope(실제 current/target 주차·server_now·phase·policy_version 등)와 아래 data다. 새 필드는 모두 필수이며 명시한 필드만 null을 허용한다. unknown 필드는 거절한다.

| data 필드 | 형식·의미 |
|---|---|
| items | DiscoveryCard 배열, 0..요청 limit(최대50) |
| total_count | strict integer 0..9007199254740991, offset/limit 적용 전 전체 일치 **방 수** |
| directory_revision | 기존 실제T head Version 1..2147483647 |
| filter_scope_digest | 기존 그룹 context digest(64자) 또는 null |
| result_revision | 새 opaque SHA256 hex 64자, 회원/권한·실제T·정규화 조건·profile/검색 의미·관측세대 결합. 그룹 digest/head 단독 대체 불가 |
| next_cursor | 최대2048자 opaque 서명 cursor 또는 null |
| evaluated_at | 이 요청의 DB 관측 UTC 시각. 페이지마다 달라질 수 있음 |

discovery-1의 DiscoveryCard는 기존 BCard 타입 정의를 투영한다. 필수 non-null은 room_id(UUID), revision(Version), title(string), scope(public/group), admission_mode(기존 enum), app_capacity(기존 enum), app_member_count(0..8), items(BCardItem[]), combat_requirement(BCombat), continuation_enabled(bool), room_cycle_id(UUID), target_cycle_key(실제T), target_generation(Version), target_revision(Version), target_state(기존 enum), restricted(bool), schedule_summary(기존 summary)다. group_id(UUID|null), experience_level(기존 enum|null), leader_display(기존 표시 dict|null)는 필수 nullable다. 각 하위 타입의 필수/null/값·배열 상한은 현재 BCardItem/BCombat/summary 계약을 재사용하며 임의 변경하지 않는다.

베타 일정 표시는 `schedule` 필수 nullable object로 축소 제안한다. 베타 방은 coordination_state(기존8상태), effective_starts_at/effective_ends_at/admission_deadline(UTC datetime) 필수 non-null, confirmed_starts_at/confirmed_ends_at(UTC datetime|null) 필수다. legacy는 schedule=null이며 schedule_summary를 사용한다. Flutter가 시각만으로 상태/마감 정책을 재판정하지 않는다.

중복 game_items, leadership·my_target_role·permissions·전체 beta_schedule·참가자/신청자·모집 비밀번호는 목록에서 제외한다. 카드 선택은 room_id/target_cycle_key로 기존 상세 조회, 신청 시 최신 context/정원/자격 검증을 사용한다. Native가 카드에 추가 상태/그룹 표시를 실제 사용하는지 협의하고 필요한 최소 필드만 확정한다. 그룹 표시가 필요하면 기존 include_group_state의 권한/표시 정책과 메타데이터를 재사용하며 result_revision/cursor에도 결합한다. Native가 실제 사용하는 그룹 표시를 확인 없이 제거하지 않는다.

## 개수·추가 페이지·변동 경계

1. 정규화된 공통 filtered query에서 count와 페이지를 파생한다. 같은 READ ONLY REPEATABLE READ 안에서 count(distinct room_id)와 정렬/offset/limit+1, 카드 projection을 실행한다. 중간 쓰기가 섞인 별도 count 호출을 앱에 요구하지 않는다. 0개도 count=0/items=[]/next_cursor=null로 반환한다.
2. 매 페이지 count를 다시 계산하는 단순안을 우선한다. 같은 result_revision이면 total_count와 결과 집합/정렬 의미가 유지되어야 한다. 각 페이지가 첫 트랜잭션의 MVCC 스냅샷을 장시간 유지하는 방식은 아니다. evaluated_at을 첫 시각으로 위조하지 않는다. 첫 수신 캐시 TTL은 Flutter가 보관하며 추가 페이지로 연장하지 않는다.
3. head/권한·본인참가·context·실제 주차·필터·시간 전이 등 결과에 영향을 주는 변경은 CURSOR_STALE로 중단한다. 새 응답 profile의 cursor에는 기존과 다른 namespace를 쓰고 전체 조건 digest/limit과 세대를 서명 결합한다. result_revision에는 시각 원값 대신 결정적 시간 전이 상태를 결합한다.
4. 구현 시 실제 결과/정렬/카드 상태를 바꾸는 모든 명령과 worker의 head 갱신, worker 이전 clock projection을 대조해야 한다. 현재 head가 완전하다고 조사만으로 보증하지 않는다. 누락은 관련 touch/epoch 의존성을 보완하고 동시성 시험으로 검증한다. 무관 변경도 보수적으로 stale될 수 있음을 공개한다.
5. 추가 조회 stale 시 기존 페이지에 새 첫 페이지를 append하지 않는다. 첫 페이지를 새 결과로 교체하고 기존 추가 페이지·count·cursor를 함께 폐기한다. 최신 상세는 별도 조회이며 목록 스냅샷이 신청 가능성을 보증하지 않는다. 변동이 없을 때 안정 정렬로 중복/누락 없이 순회, 변동 시 재시작하는 경계다.

## 오류·캐시·재시도

- 400 INVALID_REQUEST: 불량 조건/상한/구간·위조 cursor·다른 회원/세션/실제T/endpoint scope. 같은 scope의 조건/limit/관측세대 변경은409 CURSOR_STALE. 외국 cursor를 자동 유효화하지 않는다.
- 401: 유효하지 않은 세션/인증 필요. 명시 그룹 접근 상실은 기존404 GROUP_NOT_FOUND 등 정책에 따라 존재를 숨긴다. 일반 목록은 최신 가시성으로 축소된다. 인증·권한 검증을 cursor 검증보다 먼저 수행한다.
- FILTER_CONTEXT_STALE409/후보 stale: 기존 오류 계약대로 최신 context/후보를 갱신한다. 사라진 선택을 Flutter가 임의 권한 판정해 대체하지 않는다. 실제 코드별 candidate 오류 목록은 구현 계약에서 기존 응답 정의를 고정한다.
- 503 등 일시 실패는 동일 읽기 요청 재시도 가능. stale/조건 오류를 무한 재시도하지 않는다. 기존 응답/성공 명령을 실패로 되돌리지 않으며 서버의 표준 오류 envelope를 재사용한다.
- HTTP no-store 유지, Flutter의 제한된 메모리 캐시는 별도 수명이다. 회원/세션·환경·실제T 변경은 관련 캐시와 진행 응답을 격리한다. 60초 재검증은 새 첫 페이지 200 전체 응답을 기본으로 권고한다. polling을 추가하지 않는다.
- directory_revision 단독 비교는 권한/시각/context 변경을 놓치므로 재사용 판정에 쓰지 않는다. 조건부 조회는 향후 별도 signed 검증 token 설계가 필요하고 POST304를 도입하지 않는다. 전체 query/권한을 재검증해야 하는 현재 구조에서 절감 효과가 측정되지 않아 이번 선행조건으로 두지 않는다.
- 본인 참가/탈퇴·방 생성/설정/완료/일정·그룹 권한 변화 등 결과에 영향 주는 명령 성공 시 관련 T/그룹의 결과를 무효화한다. 영향 범위가 불명확하면 동일 회원·환경의 최근5개를 보수적으로 비운다. 확정 거절은 정책/권한 변화 여부에 따라 관련 상태를 재조회한다. 결과불명 명령은 원ACK 복구를 먼저 수행한다.
- Flutter는 적용조건과 편집조건, 요청세대/무효화세대를 분리한다. 새 검색/refresh 진행 중 명령 성공·권한 변경이 있으면 늦게 도착한 옛 응답을 캐시에 다시 넣지 않는다. 권한 상실을 알게 된 상세/그룹자료는 즉시 폐기하고 새 접근 결과를 따른다. 필터 편집 자체로 기존 표시를 바꾸지 않는다.

## 비용과 검증 계획

현재는 상관 인원 count·권한/캐릭터 EXISTS·정렬·offset, 선택 페이지 batch와 베타 enrich 비용이 있다. 전체 count는 모든 일치 후보를 평가해야 하므로 추가 비용이다. 50개 직렬화는20개보다 클 수 있고 offset 깊이에 따라 느려질 수 있다. 전용 최소 DTO는 전송/일부 projection을 줄일 의도이나 성능 개선 수치는 아직 없다.

합의 후 격리 PostgreSQL의 합성 자료로 동일 조건/분포·페이지 깊이에서20/50개와0개·선택도 높은 필터·그룹/캐릭터/시간 조건을 비교한다. 총 처리시간(p50/p95·반복 수·warm/cold), SQL 수/소요시간, count 단독 비용(EXPLAIN ANALYZE/BUFFERS), 카드 projection/직렬화 시간·UTF-8 응답 bytes를 분리 기록한다. 운영 DB를 성능 시험용으로 쓰거나 실제 회원 자료를 출력하지 않는다. 실측 후 병목이 남을 때 keyset/인덱스 대안을 별도로 평가한다.

필수 검증은 0/1/50/51/100+·마지막/첫/추가, count와 전체 페이지 방 ID 집합 일치, 모든 필터·가시성/본인참가 제외의 페이지 전 적용, 동일 인원 동률·세대/반대T, 회원/세션/권한/주차/조건/limit/token/cursor 위조, 모집 생성/탈퇴/참가/완료/그룹권한·일정 worker/clock 전이 중 stale, count와 페이지 사이 동시 쓰기의 스냅샷 일관성이다. 만료/수동 refresh·늦은 응답 무효화는 Backend 계약 시험과 Native 소비 시험을 구분한다. 기본/two-cycle 전체 OpenAPI 비교와 기존 route strict 응답 회귀도 필요하다.

현재 수행은 소스/계약 정적 조사뿐이다. 검색시간/응답크기/count 실측·새 응답 profile 자동 시험·로컬 서버 연결·실회원/기기 인수는 미실행이다. 문서 검증 결과는 DEV_LOG에 기록한다.

## Native 기본 수용·카드 보완 검토

[전체2번째 Native](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6820005683)는 동일 POST/profile·count/result_revision·stale/캐시 규칙을 수용했다. 그룹 표시/조율 표시 보완과 candidate 오류·profile 조합은 아래 추가안으로 협의한다. 기본 수용과 전체 계약 고정/구현 완료를 구분한다. 기존 GET/v1/projection의 소비 종료는 확인되지 않았으므로 일괄 삭제하지 않는다.

## 카드 표시·오류·profile 조합 보완안

[전체3번째 Backend 게시 원본](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6820247507). 실제 댓글 목록 재조회로 순번3·본문 일치를 확인했다.

[전체2번째 Native 소비 대조](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6820005683)를 확인했습니다. 기본 방향 수용을 반영하고 아래 카드 계약을 보완 제안합니다. 조사 소스는 기존 `b03595a8999d3bbd66a93443048d1a7f85536a1d`, 브랜치는 `feat/recruitment-discovery`입니다. **아직 공개 DTO/OpenAPI·업무 구현은 변경하지 않았으며**, 아래 추가 필드/조합의 Native 수용 후 계약을 고정합니다. 이미 수용한 기본 방향·캐시 규칙을 다시 확인 요청하지 않습니다.

### 1. 그룹 표시 — 기존 메타데이터 재사용

`include_group_state=true`에서 새 profile도 기존 목록의 **envelope 최상위** `group_states`와 `cycle_groups`를 반환합니다. data.items의 `group_id`만으로 그룹명을 추정하거나 카드별 그룹 GET을 추가하지 않습니다.

- `group_states`: 필수 배열. 각 원소는 `group_id: UUID`, `name: string|null`, `state: active|ended|unavailable` 모두 필수입니다. 페이지의 승인된 실제 그룹 참조를 중복 제거해 반환합니다. 현재 Group이 있으면 name과 active/ended, 없으면 name=null/state=unavailable입니다. 빈 페이지·그룹 참조가 없으면 `[]`입니다.
- `cycle_groups`: 필수 배열. 기존 Metadata 그대로 `room_id: UUID`, `target_cycle_key: date`, `room_cycle_id: UUID`, `generation: integer|null`, `scope: public|group|null`, `group_id: UUID|null`, `revision: integer|null`, `state: known|unavailable`을 모두 반환합니다. 검색 결과의 room_cycle_id/target_generation에 해당하는 매핑이며 다른 주차/세대로 대체하지 않습니다.
- `state=known, scope=public, group_id=null`은 공개 모집입니다. `state=known, scope=group`은 해당 group_id의 group_states로 그룹명·해산을 표시합니다. 정책 매핑 unavailable과 그룹자료 unavailable은 각각 확인불가이며 '공개'로 합성하지 않습니다. ended는 그룹 해산 표시이고 모집 종료/권한 부여로 해석하지 않습니다. public은 Metadata.state의 새 enum이 아니라 scope 값입니다.
- 검색 허용을 먼저 판정한 결과에만 메타데이터를 붙이며 그룹 표시가 그룹 열람 권한을 부여하지 않습니다. 기존 `cycle_group_policy.metadata`/`group_list_display` 정책을 재사용합니다.
- 새 profile의 그룹 표시 켜짐은 현재 실제T 그룹정책이 제공되는 실행을 대상으로 합니다. 준비되지 않은 환경은503 GROUP_FEATURE_NOT_READY로 거절하며 room_groups/옛 전역 매핑으로 조용히 대체하지 않습니다. 기존 응답의 호환 경로는 변경하지 않습니다.
- `include_group_state=false`/생략은 두 필드를 **생략**합니다(null 아님). true에서는 두 배열이 필수이며 `room_groups`는 넣지 않습니다. 그룹표시 선택·group directory revision도 result_revision/cursor에 결합합니다.

### 2. 조율 표시 — 서버 소유 최소 요약

기존 schedule 필드에 **필수 non-null object `coordination_progress`**를 추가합니다. schedule 자체는 기존 제안처럼 베타 표시가 없는 경우 null입니다.

```json
{"status":"waiting_members","missing_members":2}
```

두 필드는 항상 필수이며 unknown field는 거절합니다.

| 조건 | status | missing_members | 표시 의미 |
|---|---|---|---|
| coordination_state=coordinating, 기준 인원 미달 | waiting_members | 정수1..8 | N명 더 모이면 조율 |
| coordination_state=coordinating, 기준 인원 충족 | coordinating | null | 공통 시간 조율 중 |
| 그 외 베타 상태 | not_applicable | null | 이 요약 문구를 표시하지 않음 |

서버에서 **같은 카드의 실제T/세대 app_member_count**를 사용해 `max(0, early_additional_members + 1 - app_member_count)`를 계산합니다. early_additional_members는 방장 외 조율 개시 기준 인원(1..7)이며 정원·현재 선택 캐릭터 수가 아닙니다. 기존 Native 표시의 인원 기준을 보존합니다. coordinating인데 early 설정이 null 등 저장 불변식이 깨지면 의미를 추정하지 않고503 SERVICE_UNAVAILABLE로 처리합니다. 0은 missing_members로 내보내지 않습니다.

이는 **현재 인원 기준의 표시 요약**입니다. 공통 시간 후보 존재/자동확정 가능/모든 참가자의 가용시간 입력 완료를 뜻하지 않습니다. 비싼 전체 시간 후보 계산·가용시간/예약 선조회나 기존 상세용 coordination_wait를 검색 카드마다 실행하지 않습니다. Flutter는 이 status와 missing_members를 표시하며 시각·정원으로 정책을 재판정하지 않습니다.

schedule의 기존 제안 필드는 유지합니다: coordination_state(기존8상태), effective_starts_at/effective_ends_at/admission_deadline(UTC datetime, 필수 non-null), confirmed_starts_at/confirmed_ends_at(UTC datetime|null, 필수). schedule=null인 legacy는 기존 schedule_summary를 사용합니다.

### 3. restricted / canView 대응

카드의 `restricted: boolean`을 유지하고 **필수 `view_detail_permission`**을 추가합니다. 기존 permissions 전체 대신 기존 view_detail의 `allowed: boolean`, `reason: string|null`, `next_change_at: UTC datetime|null` 세 필드를 모두 필수로 투영합니다. 현재 정책상 인증된 가시 방은 allowed=true/reason=null/next_change_at=null, 비로그인 공개 검색은 allowed=false/reason=AUTH_REQUIRED/next_change_at=null입니다. 기존 restricted와 권한은 별개입니다.

Native의 canView는 allowed를 소비하고 restricted 표시를 유지합니다. 제목·항목/난도·숙련도·출발/마감·인원·참가 방식·leader_display 등 앞선 최소 카드는 유지합니다. 이 값은 조회 시점 표시이며 상세/신청 시 최신 권한·정원·자격을 다시 검증합니다.

### 4. 정확한 query 조합

기존 POST `/v2/raid-rooms/search`에서만 다음을 제안합니다.

| query | 허용/의미 |
|---|---|
| response_profile | 생략=기존 strict 응답, discovery-1=새 응답, 다른 값/빈 값/null 문자열=400 |
| contract_profile | 기존대로 생략 또는 beta-recruitment-1. discovery-1이 베타 정책을 묵시적으로 켜지 않음 |
| group_policy_version | 기존대로 생략 또는 cycle-group-policy-1. 지정 시 기존 준비상태 검증/marker 유지 |
| include_group_state | 생략/false/true. discovery-1의 true는 위 group_states/cycle_groups 필수, false는 둘 다 생략 |

Native의 현재 베타·그룹표시 소비에 대한 권고 조합:

```text
POST /v2/raid-rooms/search?response_profile=discovery-1&contract_profile=beta-recruitment-1&group_policy_version=cycle-group-policy-1&include_group_state=true
```

같은 요청 body의 기존 필터/후보 증거를 그대로 사용합니다. contract_profile 생략+discovery-1도 베타 전용 필터를 보내지 않는 기존 조건 검색으로 허용하되 schedule=null입니다. beta 전용 필터에 profile이 없으면 기존대로400입니다. group_policy_version 지정과 include_group_state는 각각 정책 선택/표시 선택이며 서로를 자동 활성화하지 않습니다. 중복 query key와 알 수 없는 query는 기존 strict 검증대로400, `include_coordination_wait`는 검색 POST에서 허용하지 않습니다. response_profile은 GET 목록·context·candidate·상세 endpoint로 전파하지 않습니다. 다른 기존 profile의 허용 범위/의미를 이번에 확장하지 않습니다.

### 5. 후보/context 오류와 복구 순서

현재 `character_candidates.get/validate_search`, `filter_context`, cursor 검증에 따른 업무 오류입니다. 인증 파싱·세션 만료/차단은 기존 공통 오류를 유지합니다.

| 경계 | HTTP/code | 처리 |
|---|---|---|
| 인증 없이 context/후보 또는 인증 필요한 그룹 검색 | 401 AUTH_REQUIRED | 인증 복구, 이전 회원 cache/token 재사용 금지 |
| 지정 그룹 부재/해산/현재 비그룹원 | 404 GROUP_NOT_FOUND | 해당 선택/context/후보 폐기, 현재 접근 상태 재조회 |
| 현재 그룹 context와 filter_context_token 불일치 | 409 FILTER_CONTEXT_STALE | context 먼저 갱신, 필요 후보 재조회·선택 대조 후 첫 검색 |
| 유효 형식 candidate token과 현재 회원/세션/그룹·활동/소유/후보자료 증거 불일치 | 409 GROUP_CHARACTER_CANDIDATES_STALE | 현재 context/후보 재조회 후 명시 선택 대조, 옛 검색 페이지와 합치지 않음 |
| 후보 token 형식 불량, 단일 그룹/context 없는 후보 token, 잘못된 member_ref/중복·후보 밖 캐릭터 | 400 INVALID_REQUEST | 불량 요청 수정, 같은 요청 무한 재시도 금지 |
| 후보 또는 검색 cursor 위조/다른 scope | 400 INVALID_REQUEST | cursor 폐기, 교차회원/세션/주차 재사용 금지 |
| 같은 scope의 후보/검색 cursor 세대 변경 | 409 CURSOR_STALE | 해당 목록 첫 페이지부터 교체; 후보는 context stale이 먼저면 context부터 복구 |
| 후보 offset 범위 초과 | 400 INVALID_REQUEST | cursor 폐기/첫 후보 조회 |
| 후보 응답 1MiB 초과 | 413 RESPONSE_TOO_LARGE | 상한 내 더 작은 limit으로 첫 후보 조회; 후보 자체 분할 불가 등 지속 실패는 오류 보고 |
| DB/필수 head 미준비·읽기 실패 | 503 SERVICE_UNAVAILABLE | 제한적 재시도, 기존 결과를 새 성공으로 합성하지 않음 |
| 명시 그룹정책/그룹표시 기능 미준비 | 503 GROUP_FEATURE_NOT_READY | 환경 준비 필요, 권한/보호 우회 없음 |
| 베타 기능 미준비 | 503 RECRUITMENT_COMMAND_NOT_READY | 환경 준비 필요 |

candidate token은 유효 형식이어도 위조/다른 회원·세션이면 현재 token과 달라 **409 GROUP_CHARACTER_CANDIDATES_STALE**입니다. 서명 cursor의 scope 위조400과 구분합니다. 검색에서 token 검증은 페이지 처리 전이며 후보 전체 증거를 사용합니다. 새 candidate 오류명이나 후보 전용 endpoint를 추가하지 않습니다. 권한/context 검사가 먼저 거절하면 cursor stale보다 그 오류를 우선합니다.

### 6. 추가 검증·다음 담당

같은 result_revision이면 **total_count 일치**를 서버 시험과 Native 응답 무결성 검증에 명시합니다. 다르면 페이지를 append/캐시 갱신하지 않고 해당 결과를 무효화해 첫 페이지를 재조회하며 계약 위반으로 보고합니다. 실제 결과 변경을 감지하면 서버는 새 revision 또는409를 반환해야 합니다.

추가 시험은 그룹 known-public/known-group/해산/자료없음·빈 페이지·세대 교차/권한 상실, 조율 기준 미달/정확히 충족/초과와 다른 모든 일정 상태·legacy, app_member_count와 요약의 동일 스냅샷, 비로그인/로그인 view_detail_permission, profile 조합/중복/미지원값·기존 strict 응답 보존, context→candidate→cursor 오류 우선순위·401/403/404/409/413/503 경계입니다. 비용 측정에는 그룹 메타데이터·요약 projection을 포함하고 실제 후보 시간계산 비용과 혼동하지 않습니다. 성능/실제 API 시험은 아직 미실행입니다.

**다음 Native:** 위 추가 그룹 DTO/coordination_progress/view_detail_permission·query 조합·오류/복구 경계의 소비 가능 여부와 실제 충돌만 회신해 주세요. 기존 기본 방향을 반복 검토하거나 사용자 기기 시험을 요청하는 단계가 아닙니다. 수용 후 Backend가 고정 계약으로 구현/격리검증하고 소스 SHA/OpenAPI·dev 로컬 연결 상태를 인계합니다. 문서 미커밋·미push, 운영/DB/키/배포 변경 및 Issue 종료는 없습니다.
