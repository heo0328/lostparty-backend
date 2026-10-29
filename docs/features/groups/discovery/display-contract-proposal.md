# 그룹 표시·활동 캐릭터·요청 집계 계약 제안

2026-10-28 / Backend / `feat/group-management` / G-DISPLAY 1차 설계.

게시: 설계 고정 `92c1702` push·원격일치 후 [전체20번째 Backend · 계약 제안](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6464713065) 게시·실제순번 확인. 다음 Flutter 소비/정책차이대조·Backend 명세보완이며 구현/기기 인수는 미완료다.

**사용자 승인으로 핵심 표시·활동·집계의 Backend 구현을 진행했다.** 현재 계약은 두 OpenAPI의 실제 DTO를 기준으로 한다. 신규 기능은 DB0034에서만 실행하며 기존0023/0033은 새기능503·기본응답보존이다. 격리 검증/게시 결과는 [구현 기록](../implementation-2026-10-28.md)을 따른다. 개발서버 반영·Flutter 연결/기기 인수는 미완료다.

## Native 검토 회신

[#12 전체21번째 Flutter · 제안 검토](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6464852611)에서 opt-in profile/현재 membership·역할별성공과현재오류·nullable/과거subject연결금지·배지합집합·실제쓰기활동시각에 현재 제품 차단 충돌이 없음을 확인했다. 계약제안접수이며 최종DTO/구현/실행OpenAPI·기기인수 완료는 아니다.

기존 카드의 gemValidationSnapshot과 활동캐릭터 integrity displayLabels의 동등표시는 아직 미확정이다. 실제 DTO 인계 때 필요한 코드/차이를 대조하며 저장없는 보석정상 합성·개인정보확대는 하지 않는다. 이 대조는 독립 조회/집계 전체의 차단조건이 아니다. Native Penpot1차/Flutter기록7eeca229은 자체보고이며 사용자검토전·기능구현/기기인수아니다.

## 기준과 현재 차이

- 요청: [Issue12 전체19번째 Flutter · 명세/개발 요청](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6464116834). 이전 전체18의 계약확인 전용 단계는 최신 요청으로 대체됐다.
- 제품 원문: [Flutter 설계39 f04f482e](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/backend-migration/39-group-flutter-integration-design.md), 같은 커밋의 [그룹 제품 계약](https://github.com/heo0328/LostParty_flutter/blob/f04f482e/docs/product/GROUP_PRODUCT_FLOW.md). 원격 문서만 참조하며 Flutter 로컬 소스를 읽거나 수정하지 않는다.
- Backend 기준: main/dev `1b6f57b`, 그룹 준비 `ea52e56`. 현재 GroupMember는 membership/역할/이름·서버·직업/가입일/is_me, JoinSubject는 표시명/누적 신청 횟수/차단 상태만 제공한다. 목록은 총수를 제공하지 않으며 그룹 활동시각 필드가 없다.
- 재사용: `groups.http_service.members`, `groups.admissions.relation_list/blocked_list`의 권한·순서, `admission_core.relation_state`의 유효 pending, 저장 Character summary·역할 분석 head/last-success. 모집 후보 조회는 내부 선별 논리만 검토하며 그 토큰/HTTP 권한을 그룹 열람에 전용하지 않는다.

사용자가 현재 그룹 카드와 활동 캐릭터를 볼 수 있게 하되 개인 원정대 전체·개인 설정을 공개하지 않는다. 표시 실패로 카드/멤버 자체를 누락하거나 숫자0·정상 보석 상태를 합성하지 않는다.

## 핵심 사용 흐름과 기존 모집 계약 연결

[#12 전체22번째 Flutter · 사용자 목적/우선순위](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6465156288)에 따라 **초대/가입 → 활동 캐릭터 확인 → 기존 모집 필터 → 기존 상세/참가/신청**을 우선한다. 관리/복구 전체를 선행조건으로 두지 않으며 확정된 관리정책·필수권한/동시성 검증을 폐기하지 않는다.

1. 기존 초대수락/신청승인/코드가입 성공 후 현재 membership·내그룹/멤버·요청/사용량을 갱신한다. Relation 승인응답과 GroupDetail 수락/코드가입 응답을 구분하며 ACK를 현재membership으로 쓰지 않는다.
2. 이 명세의 그룹표시/활동캐릭터 GET은 현재 membership_id와 canonical character_id로 확인자료를 제공한다. 모집검색 권한token을 새로 발급하거나 일반열람자격과 혼용하지 않는다.
3. 검색 진입시 기존 `GET /v2/me/raid-room-filter-context`의 최신 그룹/alias를 받고, 필요한 그룹의 `GET /v2/groups/{group_id}/raid-room-character-candidates`를 현재 filter context로 조회한다. 표시조회에서 확인한 membership_id는 후보의 alias.group_membership_id와, 선택캐릭터는 현재 후보 canonical character_id와 대조한다. 이름/전역 user_id로 매칭하지 않으며 이미무효인 선택을 다른캐릭터로 대체하지 않는다.
4. 기존 `POST /v2/raid-rooms/search`의 member_ref/character_ids와 context/candidate 증거를 사용한다. 그룹OR·그룹원AND·같은그룹원캐릭터OR 등 기존논리와 실제T/세대·페이지전필터/본인실제참가방제외를 유지한다. 표시스냅샷·cursor는 모집context/token을 대신하지 않는다.
5. 검색결과는 기존실제T 상세/후보·참가/신청context와 명령으로 이어진다. 검색조건은 원하는조합을 찾는 조건이지 슬롯예약·자동조합/대리참가·새공개범위 권한이 아니다.

가입/탈퇴/추방/해산·회원/환경 변경 후에는 해당 그룹표시/활동캐릭터와 모집group/filter/candidate context를 함께 무효화하고 현재membership에서 재조회한다. 늦은응답/이전세션 cursor를 합치지 않으며 권한검증은 최종명령에서 반복한다. 기존참가방 접근은 신규그룹검색/참가와 분리해 보존한다. 다른기기변경은 기존명시재조회·stale회복을 쓰며 새상시polling/웹소켓은 없다.

구현인계는 위 핵심흐름의 표시/집계·기존모집연결과 직접경계 검증을 먼저 묶고, 그룹관리 독립기능을 이어간다. 보석snapshot/labels 매핑은 실제DTO대조 항목으로 남기며 전체연결을 막지 않는다. 현재는 이 연결의 설계인계이며 신규HTTP/Flutter연결 완료가 아니다.

## 인터페이스와 호환성

다음 경로와 DTO는 제안이다. 기존 GET에 `reader_profile=group-display-1`을 명시한 경우에만 새 shape를 반환한다. 생략 시 현재 shape·정렬·기본 동작을 그대로 유지하며 알 수 없는 프로필·중복/불허 query는400이다. 쓰기 DTO와 과거 ACK는 확장하지 않는다.

| 조회 | 제안 변경·권한 |
|---|---|
| `GET /v1/groups/{group_id}/members?reader_profile=group-display-1` | 현재 그룹원. 기존 page/items에 profile·evaluated_at·snapshot_revision, 각 item에 `character_spec` 추가 |
| `GET /v1/groups/{group_id}/members/{membership_id}/activity-characters` | 신규 전용 GET. 현재 조회자/대상 모두 같은 활성 그룹의 유효 membership이어야 함. limit/cursor만 허용 |
| `GET /v1/groups/{group_id}/blocked-subjects?reader_profile=group-display-1` | 현재 그룹장. 각 subject에 character_spec 추가; subject_id/누적 횟수/차단 의미 유지 |
| `GET /v1/me/groups?reader_profile=group-display-1` | 본인. 각 GroupDetail에 `last_activity_at` 추가, page에 profile/evaluated_at/snapshot_revision 추가 |
| `GET /v1/me/groups/{group_id}?reader_profile=group-display-1` | 현재 그룹원. 기존 GroupDetail과 last_activity_at·profile/evaluated_at/snapshot_revision |
| `GET /v1/me/group-request-counts` | 본인 수신 초대/보낸 신청/현재 그룹장 관리대상 집계. 본문/query 없음 |
| `GET /v1/groups/{group_id}/join-request-counts` | 현재 그룹장. 해당 그룹의 유효 신청/초대 집계. 본문/query 없음 |

페이지 기본20/최대50·서명 cursor·no-store를 유지한다. 활동 캐릭터는 최대50개씩, 응답 JSON 최대1MiB(기존 모집 후보 상한과 동일)를 적용한다. 상한을 넘으면503 SERVICE_UNAVAILABLE이며 조용한 잘림/가짜 마지막 페이지는 금지한다. 이 경로는 캐릭터 조회이지 신규 모집 참가자격 보증이 아니다.

## 표시 DTO와 데이터 출처

`character_spec`는 항상 객체이며 다음 필드를 가진다. 실제 숫자는 기존 계약처럼 음수가 아닌 유한 Decimal 문자열이다. UUID는 서버 canonical UUID, 시각은 UTC RFC3339다.

| 필드 | 타입·의미 |
|---|---|
| `character_id` | UUID 또는 null. 현재 권한 내에서 안전하게 연결된 캐릭터만 반환 |
| `state` | `available / partial / unavailable` |
| `reason` | null 또는 `CHARACTER_REFERENCE_UNAVAILABLE / CHARACTER_NOT_CURRENTLY_ELIGIBLE / CHARACTER_DATA_UNAVAILABLE / ROLE_ANALYSIS_UNAVAILABLE` |
| `item_level` | 문자열 또는 null. Character.summary.item_level의 원본 유효값 |
| `item_level_source` | `stored_character_summary / unavailable` |
| `summary_fetched_at` | 실제 summary 관측시각 또는 null. 이번 GET 시각으로 대체하지 않음 |
| `dealer`, `support` | 아래 역할 표시 객체. 한 역할을 다른 역할이나 최대값으로 대체하지 않음 |

state 판정: 현재 연결이 불가하면 unavailable이다. 연결이 있고 아이템레벨과 하나 이상의 유효 역할 전투력이 있으면 available, 그 밖의 일부 표시값만 있으면 partial이다. 보석 원본 미지원 자체를 정상으로 간주하지 않으며 state는 참가자격 판정이 아니다. available의 reason은 null, partial은 아이템레벨 없음이면 CHARACTER_DATA_UNAVAILABLE, 그 외에는 ROLE_ANALYSIS_UNAVAILABLE이다. 연결은 있으나 모든 표시값이 없으면 unavailable/CHARACTER_DATA_UNAVAILABLE이다.

각 역할 객체: `combat_power: string|null`, `source: stored_role_success|unavailable`, `trust: client_submitted|null`, `observed_at: datetime|null`, `saved_at: datetime|null`, `power_revision: int|null`, `analysis: object|null`, `reason: null|ROLE_ANALYSIS_UNAVAILABLE|ROLE_ANALYSIS_INVALID`.

analysis는 현재 유효한 RoleSummary head의 `version/saved_at/analyzed_at/integrity_status/issues[{code,severity}]`만 제공한다. 전투력은 같은 회원·캐릭터·소유세대·역할의 last-success를 사용하며 현재 head 오류와 과거 성공값을 구분한다. lifecycle_revision이 현재 캐릭터와 맞지 않거나 저장값 검증에 실패한 부분은 null/사유로 반환한다. last-success가 없더라도 유효한 현재 분석 오류는 표시할 수 있다. API 키·등록 ID·owner user_id·전체 summary JSON·개인 preferences는 공개하지 않는다.

보석 개별 세팅/장착 원본은 현재 RoleSummary에 없으므로 필드를 발명하지 않는다. 저장된 issues/integrity만 제공하며 이것이 게임 API로 재검증된 보석 결과가 아님을 계약에 명시한다. 기존 카드가 요구하는 표시에 부족하면 Flutter가 필요한 코드/표시 차이를 #12에 구체화한다. 전체 조회/다른 독립 구현을 차단하는 질문은 아니다.

### 멤버와 활동 캐릭터의 범위

- 카드 display는 기존 membership snapshot을 유지한다. 선택 캐릭터가 현재 유효하지 않아도 membership/카드는 유지하고 spec만 unavailable로 반환한다.
- 스펙의 현재 연결은 활성 회원·현재 본인 인증 소유·유효 registration/configuration·선택된 Activity·confirmed/active lifecycle·현재 NameClaim 일치를 모두 검사한다. 원정대 전체나 단순 이름 재검색으로 연결하지 않는다.
- 활동 캐릭터 조회는 대상 membership.user_id의 위 유효집합만 반환한다. 여러 등록에 겹친 같은 canonical UUID는 한 번만 반환한다. 조회자 본인도 같은 계약을 쓴다.
- 활동 목록 item: `character_id/display/character_spec`. 회원 전역 ID·원정대 등록/개인설정은 노출하지 않는다. 응답 루트는 `group_id/membership_id/group_revision/members_revision/evaluated_at/snapshot_revision/items/next_cursor`다.
- 정렬은 유효 item_level 내림차순/null 뒤, 동일하면 character UUID 오름차순이다. 대상 membership 종료/그룹 소멸은404 GROUP_TARGET_UNAVAILABLE; 조회자 탈퇴는403 GROUP_MEMBERSHIP_REQUIRED. 비공개 그룹 여부의 기존404 정책은 유지한다.

### 차단 subject의 표시

과거 subject.display는 이름/서버/직업 snapshot뿐이며 character_id가 없다. 이름으로 현재 캐릭터나 새 소유자를 찾아 붙이지 않는다. 구현 시 신규 subject 표시 변경에만 canonical 참조·관측 당시 ownership/lifecycle 근거를 함께 저장하는 group_subject_character_references 확장 테이블을 도입한다. 과거행을 이름 매칭으로 backfill하지 않는다.

현재 target_user_id와 저장된 참조/세대·소유가 일치하고 현재 자격을 만족하면 해당 캐릭터 스펙만 제공한다. 참조 없음은 CHARACTER_REFERENCE_UNAVAILABLE, 세대/소유/활동 상실은 CHARACTER_NOT_CURRENTLY_ELIGIBLE이다. 기존 표시명·application_count는 그대로 유지한다. 차단당한 회원의 다른 캐릭터/원정대를 찾아 대체하지 않는다.

## 정확한 요청 집계

집계와 목록은 같은 `relation_state`와 현재 역할 판단을 공유한다. 저장 state=pending만 세지 않고 `expires_at > evaluated_at`, 유효 발신 membership, 활성 그룹 및 현재 조회권한을 적용한다. 승인/취소 등 완료 관계는 제외한다. 조회가 만료행을 UPDATE하지 않는다.

개인 응답: `evaluated_at/counts_revision/valid_until/received_invitations/sent_applications/managed_applications/managed_invitations/action_required`.

- received_invitations: 본인 수신 유효 초대 수.
- sent_applications: 본인이 보낸 유효 신청 수. 상대 처리 대기이며 action_required에 더하지 않는다.
- managed_applications: 현재 그룹장인 모든 활성 그룹의 유효 신청 수.
- managed_invitations: 같은 그룹들의 유효 초대 수. 취소 가능한 관리 현황이며 필수 처리 숫자에 더하지 않는다.
- action_required: 본인 수신 초대와 그룹장 처리대상 신청의 **relation_id 합집합** 크기다. 단순 합산 중복을 만들지 않는다.

그룹 응답: `group_id/group_revision/members_revision/evaluated_at/counts_revision/valid_until/pending_applications/pending_invitations/action_required`. 그룹 action_required는 pending_applications다. 개인/그룹 숫자를 다시 더해 전역 배지를 만들지 않는다.

counts_revision은 권한 범위·포함 relation ID/revision/실효 state의 digest다. valid_until은 포함된 유효 pending의 가장 빠른 expires_at이며 없으면 null이다. 미래 변경을 예측하는 보장이 아니므로 그룹장 이전/가입·탈퇴/관계 명령·화면 복귀 때 재조회한다. 다른 기기 실시간 푸시/상시 polling은 추가하지 않는다.

집계는 DB 전체 대상에서 정확히 계산하며 pagination 전 count다. 처리 가능한 그룹이 없다는 사실은0이고, DB/권한 원본 조회 실패는503이다. 실패한 화면에서 임시0을 반환하지 않는다.

## 활동시각·cursor·쓰기 후 갱신

기존 Group 모델의 DB0023 호환을 위해 group_activity_heads 확장 테이블의 last_activity_at으로 제공한다. 새 그룹 생성은 생성시각, 기존 그룹은 null 유지, 이후 실제 성공한 변경에만 서버시각을 기록한다. 이름/대표·가입/탈퇴/추방·초대/신청/차단·코드관리·이전/해산·연결 레이드 생성/공개범위 변경을 포함한다. no-op·과거ACK replay·GET·실패/rollback은 갱신하지 않는다. 최종 변경 후 과거시각으로 퇴행하지 않게 한다. 일반 레이드 전체 활동/운영정리·TTL은 이번 범위가 아니다.

같은 REPEATABLE READ/READ ONLY 스냅샷에서 권한과 표시 자료를 묶어 읽는다. 그룹/members revision만으로는 다른 회원의 활동/분석 변경을 알 수 없으므로 snapshot_revision에 대상 membership·현재 소유/설정/claim/lifecycle·표시값/분석 revision과 활동시각을 결합한다. cursor는 actor/session·경로/profile·group·대상membership·limit·snapshot_revision에 묶는다. 값이 바뀌면409 CURSOR_STALE로 첫 페이지를 재조회하고, 권한이 사라졌다면 권한 거절을 먼저 적용한다. GET은 없는 기본행/토큰/관측 이력을 만들지 않는다.

| 성공 변경 | 필요한 갱신 |
|---|---|
| 가입/탈퇴/추방/해산 | 내 그룹/사용량·상세/멤버/활동목록·관리·요청집계·모집 group context |
| 초대/신청/승인/거절/취소/차단 | 해당 관계/목록·개인/그룹 집계·차단목록·변경된 활동시각 |
| 이전 | 상세/멤버/관리·집계/관리목록·코드 원문 접근권한 |
| 대표/이름·활동선택/소유/분석 변경 | 영향을 받은 그룹 표시·활동목록 snapshot/cursor. 검색 공개정보의 공개범위를 확장하지 않음 |

명령 성공 후 조회 실패는 명령 실패가 아니다. 원 key/body를 재실행하기보다 현재 GET 갱신을 재시도한다.

## 대표 예시

아래는 신규 개인 집계 GET의 **합성 예시**다. 실제 회원 응답/인수 결과가 아니다.

```json
{
  "evaluated_at": "2026-10-28T09:00:00Z",
  "counts_revision": "example-counts-digest",
  "valid_until": "2026-10-28T10:00:00Z",
  "received_invitations": 2,
  "sent_applications": 3,
  "managed_applications": 4,
  "managed_invitations": 1,
  "action_required": 6
}
```

레거시 차단 subject의 character_spec 예시:

```json
{
  "character_id": null,
  "state": "unavailable",
  "reason": "CHARACTER_REFERENCE_UNAVAILABLE",
  "item_level": null,
  "item_level_source": "unavailable",
  "summary_fetched_at": null,
  "dealer": {"combat_power": null, "source": "unavailable", "trust": null, "observed_at": null, "saved_at": null, "power_revision": null, "analysis": null, "reason": "ROLE_ANALYSIS_UNAVAILABLE"},
  "support": {"combat_power": null, "source": "unavailable", "trust": null, "observed_at": null, "saved_at": null, "power_revision": null, "analysis": null, "reason": "ROLE_ANALYSIS_UNAVAILABLE"}
}
```

## 검증·담당·완료 조건

이번 실행 검증은문서/링크/JSON예시·git diff 검사뿐이다. 다음은 **구현 시 실행할 시험**이며 통과 보고가 아니다.

- 권한: 현재멤버/그룹장/비멤버/탈퇴자/타그룹 membership·subject 위조/다른 회원·세션 cursor.
- 표시: null/잘못된 Decimal·분석 없음/오류/이전 성공, 역할/ownership/lifecycle 불일치, 비활동/소유이전/retired·동명이인·참조없는 과거subject, 개인설정/원정대정보 유출 없음.
- 집계: 페이지20개 초과, 만료 정확경계/발신자탈퇴/그룹종료, 리더이전 직후 범위·합집합 중복/보낸신청 구분·조회실패503.
- 수명: 표시만 바뀌어도 cursor stale, GET SQL쓰기0/provider호출0, page상한/응답상한·권한소멸 우선, no-op/ACK/rollback 활동시각 보존.
- 호환: profile 생략 시 기존 G1/G2/ACK shape 동일·strict query, 기본/실행 두 OpenAPI의 구현 전체일치(구현 때만 실행).

다음 Backend는 이 제안을 #12에 게시하고 기술 차이에 대응하며 확정 계약을 구현한다. Flutter는 필요한 표시 코드/소비상 충돌만 회신한다. 시안/단순 소비회신이나 G-RECOVERY 미결정으로 독립 구현 전체를 보류하지 않는다. API 구현·개발환경 반영·Flutter 연결/기기 인수 완료는 각각 별도다.


## 2026-10-29 — 초대 후보 표시 프로필 확장

[#12 전체29 Flutter 검색 수정 요청](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6495682192)·[전체30 Flutter 전투력 경로 확인](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6496105720)에 따라 [구현 전 계약제안](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6496315881)을 게시했다. 후보 endpoint의 opt-in `reader_profile=group-display-1`도 기존 CharacterSpec 형식을 재사용한다. [초대 후보 계약](../joining/README.md)의 profile/evaluated_at/items·기존 후보필드+character_spec을 따르며 기존 기본DTO/단일combat_power는 유지한다.

공통 내부함수는 caller가 이미 권한을 검증한 character/owner의 저장 역할자료만 일괄 표시한다. 활동펼침은 현재활동 자격, 초대후보는 기존초대 자격을 각각 적용한다. 일반활동의 자격을 후보에 강제하거나 후보검색을 타회원 활동/개인설정 공개로 확대하지 않는다. 현재 역할분석과 이전성공 수치·소유/생명주기 근거는 같은 규칙을 사용하며 GET쓰기/provider/중복저장/migration은 없다. 신규 프로필은0034 필요·기본0023/0033은 보존한다. 구현후 검증/게시와 개발반영/기기인수는 별도다.
