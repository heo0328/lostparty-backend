# Issue #13 — 본인 완료 정정·완료 방 보관 계약 제안1

2026-10-23 / Backend / feat/raid-recruitment / **제안 당시 검토안 기록**.

현재는 [Flutter127](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6358680312)이 수용했고 [개발 인계](ISSUE_13_COMPLETION_CORRECTION_DEVELOPMENT.md)의 구현/실행 OpenAPI·예시가 기준이다. 아래 미합의·미구현 표현은 제안 당시 상태를 보존한 것이다.

요청 원본은 [전체124번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6358203104), 독립 수정 결과는 [전체125번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6358397626)다. 소비 구현은 29408243192ed3a37a347ade046db26ad2d918b9이며 이 문서는 실행 OpenAPI가 아니다. 기존 endpoint의 의미를 조용히 바꾸지 않고 아래 소비 변경을 먼저 협의한다.

## 1. 확인된 현재 동작

- `cycle_outcomes.manual`의 completed=false는 manual 시각/난이도만 해제한다. party 시각/방/난이도는 남는다. playable 검사가 앞에 있어 C/수10시 제한도 적용된다. 기존 `clear_manual_completion` permission과 일치하지만 새 요구는 충족하지 않는다.
- `cycle_lists.memberships(state=current)`의 SQL 조건은 **지속 Member.ended_at IS NULL**이다. 실제T의 CycleMember 참여/주차 개방 조건이 아니다. 그래서 completed/stopped/not_selected/legacy 관계도 반환될 수 있다. 실제 디바이스 원본/특정 방 DB를 조회한 원인 확정은 아니고 코드상 포함 경로 확인이다.
- 검색 `cycle_queries.search`는 Room.ended_at IS NULL·선택T RoomCycle.state=open을 SQL에서 검사한다. 정상적으로 closed가 된 완료T는 이미 검색에서 제외한다. 다만 카드 state/phase는 Room.ended_at 기준이어서 주차 완료와 방의 서비스상 활성 표시가 다를 수 있다. 0명 방은 일부 미완료·종료상태 불일치 등도 가능하므로 인원0만으로 전체완료를 추정하지 않는다.
- 완료 execute는 Assignment/CycleMember·Round/Generation·예약/점유/세션 정리 및 불변 CycleOutcome을 기록한다. 지속 Member/Room 전체 종료와는 별개다. 개인완료로 실제 active assignment가 없어져 generation이 completed가 되어도 Round 상태는 active일 수 있으므로 전체완료 판정에서 함께 검토해야 한다.

## 2. 본인 완료 해제 — 별도 명령 제안

### 범위·시각·권한

- 대상은 **현재 인증회원이 현재 소유를 검증한 본인 캐릭터 + 명시 실제T + raid**의 현재 유효한 manual/party 완료 양쪽이다. 두 출처가 있으면 한 명령에서 함께 해제한다. 다른 회원/다른 캐릭터/raid/T는 변경하지 않는다.
- 실제T는 정규 ISO 수요일 날짜이며 **T <= 현재C**를 허용한다. 과거주차도 만료 제한 없이 허용하고 현재C의 수06~10시도 취소 가능하다. 미래T는 거절한다. 과거T를 C로 치환하지 않는다. 기존 C/N용 `cycles.target`이나 완료생성 `playable` 제한을 새 명령에 재사용하지 않는다.
- 정상 세션/현재 소유검증/ownership·lifecycle revision CAS는 필수다. 소유이전된 캐릭터나 다른 회원의 예전 기록을 현 소유자가 지우지 않는다. 활동 비활성·은퇴/완료 후 레벨·역할·전투력 변화는 본인 기록 정정의 차단 사유로 삼지 않는다. 소유 관계 자체가 없어졌으면 기존 보안상 비노출 오류를 유지한다. 기존 owned_character는 retired를 거절하므로 이 정정 전용 경로에서 현재 등록/Account.owner_id·verified_at·대상 WeeklyState.user_id와 두 revision을 직접 검증한다. 은퇴캐릭터의 현재 이름 claim 유무로 과거 기록 정정을 막지 않되, 같은 이름의 새 character_id나 타인 자료로 연결하지 않는다. 기존 소유/다른 쓰기의 검증을 완화하지 않는다.
- 방 회원/공대장·그룹 가입 권한이나 방 활성 여부는 필요하지 않다. 보관된 방의 완료 출처도 정정 가능하다. raid가 현재 비활성이어도 저장된 본인 완료 기록으로 정정 가능하다. 현재 카탈로그의 활성/버전·전투력·참가조건을 정정 전제에 넣지 않는다.
- 완료를 새로 만드는 기존 경로의 C/수10시·소유/활동·카탈로그·참가 제약은 유지한다. 정정은 새 완료 생성/방 복구 권한이 아니다.

### 제안 경로와 닫힌 DTO

모든 새 객체는 additionalProperties=false, 모든 표 필드는 required이며 nullable만 명시적으로 null을 허용한다. 문자열/정수/불리언 간 강제변환은 없다. UUID는 표준 UUID 문자열, revision은 1..2147483647 정수, 모든 시각은 offset이 있는 ISO datetime이다. 대상 raid_id는 1..64자 문자열이다.

| 경로 | 입력·결과 |
|---|---|
| GET `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-correction-context?target_cycle_key=T` | 인증 필수·읽기전용·Key 불필요. 아래 Context200. 대상T는 과거/현재 지원 |
| POST `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-corrections` | 인증·UUID4 Idempotency-Key 필수. 아래 Command→Result200 |

Context200의 최상위는 `{server_now,current_cycle_key,data}`다. C/N 전용 기존 `scope`를 과거T에 억지로 사용하지 않는다.

`data`의 정확한 필드:

| 필드 | 타입/의미 |
|---|---|
| character_id / raid_id / target_cycle_key | UUID / 문자열 / 실제 수요일 날짜 문자열 |
| weekly_revision / ownership_revision / lifecycle_revision | revision |
| completion_sources | 기존 SummaryCompletionSource와 같은 닫힌 객체 배열, 0..2개, manual→party 순, source 중복 없음 |
| permission | `{allowed:boolean,reason:string|null,next_change_at:datetime|null}`. 허용 시 reason/null, next_change_at/null |
| confirmation | `{context_token:string,issued_at:datetime,expires_at:datetime}` 또는 null |

source 객체는 `{source:'manual'|'party',completed_at:datetime,difficulty_id:string|null,party_id:UUID|null}`다. 기존 자료의 null 가능성은 현재 SummaryCompletionSource와 같게 유지한다. 현재 raid 카탈로그에서 제거된 id라도 본인 저장 기록이 있으면 표시한다. 저장 기록도 카탈로그 항목도 없으면 RAID_NOT_FOUND404, 카탈로그는 있지만 완료가 없으면 sources=[]/permission=false·COMPLETION_NOT_FOUND/confirmation=null이다. 현재 소유검증이 불가능하면 정상 인증된 본인 범위에서 OWNERSHIP_REQUIRED403, 그 외 소유 비노출/세션 오류는 기존 규칙을 유지한다.

Command의 정확한 필드:

```json
{
  "target_cycle_key": "2026-10-21",
  "expected_cycle_key": "2026-10-21",
  "expected_weekly_revision": 4,
  "expected_ownership_revision": 2,
  "expected_lifecycle_revision": 3,
  "correction_context_token": "<opaque token>"
}
```

expected_cycle_key는 읽은 **현재C**다. target은 과거T일 수 있다. 다른 본문 필드/명시null은 거절한다. token은 비어 있지 않은 문자열·최대4096 UTF-8 bytes이며 actor/character/raid/T/currentC·세 revision·현재 source 전체를 묶는다. 최대120초 유효, 서버 수06시 C 변경까지로 제한한다. 확인 중 rollover면 새 context로 재확인한다. 취소 가능 시각을 제한하는 것이 아니라 stale 확인을 다시 받는 것이다.

Result200 최상위는 `{server_now,current_cycle_key,data}`이며 data의 정확한 필드는 다음과 같다.

| 필드 | 타입/의미 |
|---|---|
| command_id | 요청 Idempotency-Key UUID4 |
| outcome | literal `applied` |
| correction_id | 새 불변 정정 기록 UUID |
| character_id / raid_id / target_cycle_key | Context와 동일 실제 대상 |
| weekly_revision | 정정 후 revision |
| completion_sources | 빈 배열 `[]` |
| participation_restored | literal false |

위 결과는 새 명령 전용 ACK다. 기존 room command Ack로 캐스팅하지 않는다. 실패/결과불명은 원 method/path/body/key/token을 재송한다. 원성공 응답은 현재 token 만료·T/C 변경·완료 재생성에 앞서 **동일 인증회원의 유효 세션** 하에서 복구하고 다시 해제하지 않는다. 같은key 다른본문은 기존 IDEMPOTENCY_CONFLICT409, 처리중은 기존 REQUEST_IN_PROGRESS409/Retry-After 2초다. 원성공 복구는 기존 완료 후24시간 범위이며 이후 IDEMPOTENCY_EXPIRED409이고 새key로 자동 쓰기를 만들지 않는다. 결과불명 장기보류는 실제T context/현재 완료 상태로 재확인한다.

### 정정의 원자성·감사·동시성

- 본인 WeeklyState의 manual/party 완료 투영만 함께 비우고 weekly_revision을 정확히 1 증가시킨다. 출처가 없어진 뒤 다른 새key로 예전확인을 제출하면 CAS/context 충돌이며 성공 noop를 꾸미지 않는다.
- 별도 불변 정정 기록에 actor/대상/T·정정 전 source·revision/정정 후 revision·command_id/시각을 남긴다. 완료 원본 Outcome/Assignment/Round의 completed 상태와 완료 당시 증거·타인 상태는 바꾸지 않는다. 완료 당시 사건과 현재 개인 주간 투영은 구분된다. 같은T 재완료가 발생하면 새 근거/증가한 revision으로 정상 표시하고, 과거 정정이 미래 근거까지 영구 억제하지 않는다.
- 현재 공통 game-mutations-v1 직렬화와 같은 원자 트랜잭션 경계를 사용하고, 모든 완료/참가 쓰기와 동일 WeeklyState CAS를 검사한다. 완료가 먼저면 이전 context 정정은 충돌·재확인, 정정이 먼저면 이전 revision의 완료/참가 명령은 충돌한다. 경합으로 타인의 최신 완료를 지우거나 source 일부만 반영하지 않는다.
- 기록정정/투영/원성공ACK 저장은 한 트랜잭션이다. 감사 저장이나 최종 만료/C경계 검사 실패는 전부 rollback한다. 별도 migration이 필요할 경우 합의 후 격리DB에서 검증하고 실제 DB 적용 여부를 인계에서 구분한다.
- 완료 해제 자체로 Assignment/Round/CycleMember·방·좌석/점유·세션/동의/예약을 복원하거나 N을 열지 않는다. 재참가는 새 명령의 자격/주차/해당방 상태 검증을 거친다. 기존 completed 관계로 과거 방에 자동 재진입할 수 있다는 의미가 아니다.

### Summary·구호환·오류·크기

- 기존 Summary의 `clear_manual_completion` 및 기존 manual-completion completed=false는 manual 전용으로 유지한다. 새 Flutter의 “완료 취소”는 source 존재 시 새 context/command를 사용한다. 기존 false endpoint로 fallback해 가짜성공을 만들지 않는다.
- 새 ACK 후 실제T Summary를 재조회한다(C/N일 때). 과거T는 새 context를 재조회해 sources=[]/증가 revision을 읽는다. 기존 summary에 과거T 지원을 몰래 추가하지 않는다. 재조회 실패가 원ACK 성공을 취소하거나 새 쓰기를 만들지 않는다.
- 새 경로: INVALID_REQUEST400(형식/미래T), CONTEXT_INVALID400(변조/actor·flow·대상 불일치), COMMAND_CONTEXT_EXPIRED409(만료), CYCLE_CHANGED409, REVISION_CONFLICT409(weekly/소유/lifecycle), COMPLETION_CONTEXT_CHANGED409(출처변경), COMPLETION_NOT_FOUND409(새명령 시 완료없음), 기존 인증401/소유비노출404/OWNERSHIP_REQUIRED403·SERVICE_UNAVAILABLE503를 구분한다. 세부 우선순위는 현재인증/공통Key·본문검사→원ACK→현재소유/대상→revision/context→실행권한/완료→적용/최종경계다. 원ACK 복구도 현재 인증을 생략하지 않는다.
- 두 새 경로와 오류는 no-store, 요청 전체32KiB/응답전체1MiB·초과413, 절단/fallback 없음. GET context는 원장/감사/기기/회원자료를 쓰지 않는다.

## 3. 완료 방의 서비스상 보관·선택T 목록

### 전체완료와 N 독립

- 논리 보관은 명시적 두주차 자료의 **전 레이드 완료 증거**를 조건으로 한다. 현재 generation completed만 보거나 인원0만 보지 않는다. 각 현재 item Round가 completed이거나, 해당 Round의 실제 참여 assignment가 존재하고 남은 active/stopped_incomplete 없이 완료 증거로 종료됐음을 확인한다. removed/cancelled 과거 관계를 새 완료 근거로 만들지 않는다. 개인완료들로 모든 raid가 끝난 경우도 포함하고 일부raid 완료·stopped/불명확자료는 제외한다.
- 전체완료된 마지막 실제T보다 뒤에 열린 실제 주차가 없을 때 서비스상 보관한다. 실제 다음N이 open 또는 review_required이면 보관하지 않고 N의 참가/리더/일정·제출·동의·권한을 그대로 보존한다. 단순 continuation_enabled·legacy_intent/희망만으로 N이 열렸다고 간주하지 않는다. N이 cancelled/closed라면 열린 다음주 보존 조건에 해당하지 않는다.
- 보관 조건을 SQL/공통 판정으로 재사용하고 GET은 쓰지 않는다. 기존 완료자료도 같은 보관 조건으로 조회에서 제외해 물리삭제/기존자료 일괄종료 없이 요구를 만족한다. 정상 새 완료·N취소/개방 쓰기에서 같은 판정을 재검사하고 디렉터리/멤버목록 cursor revision을 무효화한다. 과거 미정/legacy 자료는 자동 종료 추정하지 않는다.
- 완료 기록 정정은 위 “당시 방 전체완료” 증거를 취소하지 않는다. 개인 주간 source를 비웠다고 보관된 방이 되살아나지 않는다. N개방과 최종완료의 경합도 공통 쓰기 잠금에서 직렬화해 먼저 확정된 상태를 재검사한다. N개방이 먼저면 N보존, 보관 성립이 먼저면 과거방 N개방 거절/새방 생성 안내다.

### 목록·상세·재개 계약 제안

- `GET /v2/me/raid-room-memberships?target_cycle_key=T&state=current`의 의미를 **선택T의 실제 활성 관계**로 정정한다. SQL pagination 전에 Member미종료 + 보관되지 않은 Room + 해당T open/review_required + 현재 generation 실제 CycleMember participating/review_required를 검사한다. legacy generation 미확정은 명시 CycleMember review_required 근거가 있는 경우만 회복용으로 남기고 `recovery_only=true`를 유지한다. 단순 legacy_intent/not_selected·completed/stopped/cancelled/removed는 제외한다.
- `state=all`은 기존 관계/기록을 보존한다. `state=ended`는 기존 지속회원 종료 관계에 더해 선택T의 실제 completed/stopped/cancelled/removed 관계와 보관방 관계를 포함한다. 단순 not_selected는 ended 참여이력으로 꾸미지 않고 all에만 남긴다. 기존 row.state/history_only는 지속관계 필드 의미를 보존하고 target_participation_state가 실제T 상태를 설명한다. 이는 state query의 의미 변경이므로 Flutter 대조 후 적용한다.
- 명시적 incomplete closure의 stopped 방은 current/활성 검색에서 제외하되 all/ended와 상세에서 기존 현재주 재개 진입을 유지한다. 완료 보관과 stopped 재개 가능성을 섞지 않는다.
- 활성 검색은 기존 T open 조건에 서비스상 보관 제외를 공통 적용한다. N이 열렸으면 C완료라도 **N 검색/현재N 참여목록은 유지**, C완료 카드만 활성 목록에서 제외한다. 카드의 target_state=completed 등은 보존하고 보관방은 기존 room.state/phase=ended로 표현한다. 새 enum을 추측해 추가하지 않는다.
- 보관방 직접 공개 카드 조회는 ROOM_NOT_FOUND404로 비노출한다. 기존 방 회원은 기록용 상세/plan을 읽을 수 있으나 새 참가/모집·편집·이전·N개방·현재주 재개는 ROOM_NOT_ACTIVE409로 차단한다. 기록 열람 범위는 기존 C/N 조회 경계 그대로다(과거 방 전체 이력 API 신설 아님). 기등록 command 원ACK 복구와 본인 완료정정은 허용한다. 멤버/Assignment/Outcome/원장/제출/동의/예약 원문 삭제는 없다.
- 방 보관은 암묵 참가취소/타인 완료해제가 아니다. 실기기 특정방이 새 전체완료 조건에 맞는지는 구현 검증/인수 때 확인한다. 운영 DB 변경/물리삭제는 범위 밖이다.

## 4. 합의 후 구현·검증 및 다음 담당

현재 실행 코드/OpenAPI·서버/DB/키는 바꾸지 않았다. 아래 소비 대조가 필요한 **계약 제안**이며 테스트/구현 인계가 아니다.

Flutter 확인 항목은 두 가지다.

1. 별도 context/정정 명령·과거T 허용/현재C 수06~10시 취소·현재소유/revision·새 ACK와 기존 manual 경로 보존을 소비할 수 있는가? “언제든”을 위 시각 의미로 충족하며 방/참가/예약 자동복구 없음에 차이가 있는가?
2. current/ended/all 필터 의미와 보관방 기록열람·쓰기차단/N보존·stopped 재개 분리를 위와 같이 적용할 수 있는가? 신규 enum 없이 기존 row/target 상태로 표시하는 데 구체 차이가 있는가?

같은 기존 mock/정책 재확인은 요청하지 않는다. Backend는 피드백을 반영해 합의 구간을 구현하고, 다음 경계를 격리검증→구간commit/push·원격확인→정확한 실행 OpenAPI/소비SHA/개발반영 여부 인계한다.

- manual만/party만/둘다/없음·본인과타인/소유이전/비활성/비활성raid·현재수06~10시/과거T/미래거절
- token변조·만료/최종만료·C변경·CAS/동시완료/참가·동일key재송/다른본문·감사/ACK rollback·새완료재생성·원ACK우선
- 다중raid 일부/전체·개인완료만으로전체/빈방과stopped 구별·Nopen/review/cancelled·N개방경합·기존완료자료·current/ended/all SQL페이지/cursor·검색/상세/쓰기권한·완료정정후방비복원
- 기존 manual/기본summary/일정/원ACK·F6-C·C/N 격리·출처/감사보존 회귀와 실행 OpenAPI 전체비교

이 작업은 같은 모집 기능의 실기기 인수 보완 두 구간(개인 완료 정정, 방/목록 수명)으로 #13에서 추적한다. 통계#19·앱종료 pending영속복구·시간선택 UI 등 독립 기능은 확장하지 않는다. Issue OPEN·dev/main통합/운영배포/실데이터정리 없음이다.
