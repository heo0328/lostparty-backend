# Issue #8 — 캐릭터 생명주기 계약 검토안

2026-10-15. [요청](https://github.com/heo0328/lostparty-backend/issues/8)의 A/B/C 검토 회신용 **제안**. 사용자 확정 정책은 수용하되 아래 wire/물리 모델은 Flutter 대조 후 구현 단위를 합의한다. 기능/OpenAPI/migration/실자료 변경은 수행하지 않았다. 코드 기준은 dev821c758(기능9e1a255와 동일). 기존 #7 종료 결과 미커밋 문서는 보존한다.

## A. 증거와 상태

### 확인된 사실과 아직 얻지 못한 사실

- `observations.py`는 list 1~200, 필수 문자열/수치·중복 없음·조회 이름 정확히1개를 검사한다. 이는 형태/내부 일관성 검사이며 전체성 검증이 아니다. 현재 live Observation의 `proof_validated`/`disappearance_validated`는 false다.
- [공식 changelog](https://developer-lostark.game.onstove.com/changelog)는 siblings를 계정의 모든 캐릭터 프로필 반환으로 설명한다. 이번 조사에서 API 상세 페이지는 접근 실패했다. 확인한 공식 설명과 현재 adapter에는 전체성 증명·응답 snapshot revision·영구 캐릭터/원정대 ID가 없다. 이 사실을 provider 전체 제품에 해당 필드가 절대 없다는 주장으로 확대하지 않는다.
- HTTP200·빈 응답 아님·JSON 전부 수신·앱의 전체 페이지 수집은 각각 transport/형태/앱 저장자료의 완결성이다. provider가 원본 일부만 반환하지 않았다는 증거는 아니다. 현재 siblings adapter에는 페이지 순회가 없으며 임의 pagination 프로토콜을 가정하지 않는다.
- JWT는 외부 호출 자격증명이지 게임 원정대 소유 증명이 아니다. 이름/직업/레벨/동일 목록·N회 재조회·일정 시간 경과로 동일 개체나 소멸 확정을 증명하지 않는다. 조회 사이 동일 이름/동일 원정대에서 삭제·재생성된 경우 영구 ID/생성 세대 없이는 구분 불가하다. 이 한계를 수용하지 않으면 해당 자동 판정은 제공할 수 없다.

### 제안 상태와 허용 범위

| lifecycle_state | 의미 | 신규 자격 | 자료 처리 |
|---|---|---|---|
| active | 현재 인증된 원정대에 연결되고 이상 미관찰 | 소유/활동/기타 조건을 추가 검증한 뒤 사용 가능 | 유지 |
| suspect | 유효한 관찰에 누락/다른 원정대 이름 충돌 등 구체적 불일치가 있으나 소멸 확정 불가 | 즉시 차단 | 값/ID/개인자료 유지, 재선택 필요 표시 |
| retired | 신뢰 가능한 전체 관찰·원정대 연속성으로 소멸 확정한 종료 세대 | 영구 차단 | 간략 이력/최소 표식만 남기고 정리 |

`active`는 provider가 보장한 영구 동일성을 뜻하지 않는다. 기존 confirmed에 대응하는 사용 상태다. 새 V2 DTO의 `usable`은 현재 서버 자격(본인 소유·active 등)을 반영하며 최종 명령에서도 재검증한다. 레이드/일정 자격 전체를 GET의 usable 하나로 보장하지 않는다.

네트워크 실패/404/빈 배열/잘못된 JSON/키 오류는 특정 캐릭터 이상 확정으로 사용하지 않고 이전 roster/상태를 보존한다. 일부 누락이 있는 형식상 정상 응답은 신뢰된 원정대 연결 안에서 suspect로만 낮출 수 있다. 등록 preview는 이력/소유/새 canonical ID를 만들지 않고 비권위 관찰로 유지한다.

suspect 해제는 단순 이름 재출현으로 하지 않는다. 같은 기존 원정대/동일 캐릭터 세대라는 신뢰된 관찰, 미해결 충돌 없음, 최신 revision에서만 active로 복구한다. 영구 식별 근거가 없으면 회복도 확인 필요로 보류한다. retired는 해제하지 않으며 이후 같은 이름의 등장도 신규 ID다. 정리 전 자동 재선택/대표 복구는 하지 않는다.

### 관찰의 권한과 보류 경계

내부 관찰 결과를 transport_valid / account_binding_validated / completeness_validated / identity_continuity_validated로 나누고 근거 종류·관찰시각·대상 원정대 revision을 기록한다. 클라이언트 boolean이나 임의 관리자 플래그로 검증 상태를 만들지 않는다. 캐시에는 근거를 보존하되 캐시된 전체 관찰을 새 소멸 확정 사건으로 사용하지 않는다.

확정 소멸은 신선한 외부 관찰 + 검증된 전체성 + 기존 원정대 연속성 + 현재 ownership/roster revision 일치가 모두 있어야 한다. 후속 검토로 신규 추가에는 소멸용 전체성을 일괄 요구하지 않는다. 긍정 관찰·검증된 원정대 연결·claim 충돌 없음·revision 일치로 새 ID를 만들도록 제안을 축소했다. live 연결 근거가 미확보인 분기는 보류한다. 현재 live adapter는 이 조건을 충족하지 못하므로 자동 소멸/정리와 증거가 필요한 추가·복구 분기는 닫아 둔다. 내부 adapter와 모의 입력으로 상태/transaction 검증은 독립 구현 가능하다. 기존 장비 proof/ROSTER_EVIDENCE_PENDING은 유지한다.

Backend가 다음 단계에서 공식 상세 schema/응답 의미·제공 가능한 영구 식별/전체성 근거를 확인한다. 새 자료가 현재 모델로 증명하지 못하면 공급자 확인 또는 별도 검증 방식 합의가 필요하다. 반복 실키 호출/사용자 키원문/고의 한도 소진은 요구하지 않는다.

조회 기준 이름404는 등록 전체 소멸이 아니다. 복구 후보는 현재 등록의 살아 있는 알려진 캐릭터 또는 명시 입력 이름으로 제한하며, 무제한 자동 탐색은 하지 않는다. 아래 lookup-recovery 명령은 기존 원정대 연결 증거를 확인한 뒤 lookup_name만 변경한다. 겹치는 이름 하나만으로 연결하지 않는다. 모든 기존 이름이 사라져 연결 근거가 없으면 409 ACCOUNT_BINDING_EVIDENCE_PENDING으로 보류하고 별도 검증 흐름을 안내한다. 새 이름 입력 자체는 인증 성공이 아니다.

## B. ID·점유·이력·조회 순서

### 최소 모델 제안

1. Character의 UUID는 재사용 불가한 **서버가 부여한 세대 ID**다. lifecycle_state/revision·전이시각을 추가하고 기존 ID를 새 이름이나 다른 원정대에 이식하지 않는다. 현재 전역(server,name) unique를 단순 삭제하지 않는다.
2. 현재 이름 점유는 별도 NameClaim(server,name PK, character_id unique FK, revision)으로 관리한다. suspect까지 기존 claim을 유지하고, retired 확정 transaction에서만 해제한다. 종료 ID는 동일 이름의 새 claim과 별개다. 종료된 ID의 최소 행은 FK용으로 유지하되 summary/개인 빌드 등 운영 payload는 정리한다.
3. CharacterRetirement은 character_id unique FK, history_id UUID, 당시 user_id/account_id, server_name/character_name/class_name, 마지막 정상 combat_power/item_level nullable string, 각 값 관찰시각 nullable, retired_at UTC, lifecycle_revision, retirement 근거 유형을 둔다. retired ID가 이전 ID 표식이며 a→b 연결·successor_id는 만들지 않는다. 이력은 당시 회원에 귀속하고 후속 원정대 소유권 이전으로 새 소유자에게 노출하지 않는다.
4. 역할별 마지막 전투력/Snapshot은 이력5값에 합치지 않는다. combat_power는 서버가 관찰한 마지막 정상 profile 표시값이다. 역할별 Snapshot이 미래 별도 저장될 때 보존/삭제 경계는 그 계약에서 정한다. 확인 못 한 수치는 null, 실패는 기존 정상값 보존, 0은 실제 관찰일 때만 허용. 이력을 클라이언트 개인 Snapshot으로 채우지 않는다.
5. 현재 캐릭터 빌드/선호/주간 개인설정 서버 테이블은 없다. 이번 설계가 기존 서버에 없는 자료를 삭제했다고 표시하지 않는다. 현재 실제 정리 대상은 활동 FK/대표와 이름 기반 preview/power/진행 캐시 등이며, 미래 종속자료에는 character_id 세대 FK/정리 규칙을 의무화한다.

이력 보관은 이번 제안에서 자동 만료/사용자 삭제 API 없이 유지한다. 무기한 보관을 운영 정책 확정으로 보지 않으며 공개 전 AUTH-F01/F02와 함께 보관기간·탈퇴 시 제거/익명화·Snapshot 최소 참조 정책을 확정한다. 원문 provider/body/키를 이력에 넣지 않는다.

### 소유 추론과 경합

현재 canonical_candidate는 이름 중첩으로 account 후보를 찾고, reconcile는 같은 이름이면 옛 ID를 복구한다. 둘 다 변경 대상이다. 이름 중첩은 충돌 후보 탐지에만 사용하며 소유/동일 원정대/이전의 충분조건으로 사용하지 않는다. 이름만 같은 경우 새 원정대를 기존 account에 붙이거나 소유권을 이전하지 않는다. 소유권 이전은 향후 독립 검증 계약 없이는 완료하지 않는다.

- A 소멸 확정 먼저: A의 종료/이력/claim 해제 완료 후 B의 독립 인증·전체성/연결 근거로 새 ID/claim 생성. A 이력·membership·권한·점유·빌드를 B에게 연결하지 않는다.
- B 관찰 먼저: A claim과 충돌하면 B canonical 생성/이전 보류(409 IDENTITY_CONFLICT). 단순 B 조회만으로 A를 퇴역시키지 않는다. 신뢰할 수 있는 불일치 증거가 서버 상태로 성립하는 경우에만 A를 suspect로 차단한다. 여러 원정대에 걸친 명령 전체를 rollback하면서 차단까지 소실시키지 않도록 해당 증거 전이는 독립된 검증 transaction으로 기록하고 명령 실패와 구분한다. 연결 증거 없으면 어느 쪽도 추정 확정하지 않는다.
- 동시 처리: 초기에는 기존 game mutation 직렬화 lock을 재사용하고 claim PK/unique 및 account/claim 행 lock으로 원자성 보강. 새 lock 순서(회원/세션→account UUID순→claim 서버/이름순→ID→설정→멱등결과)를 모든 관련 writer에 적용한다. 네트워크는 lock 밖. 서로 다른 사용자가 같은 이름을 차지하려 해도 한 claim만 성공하며 나머지는 보류/충돌이다.
- A 같은 이름 재등장: 아직 suspect인 ID는 위 연속성 검증 없이는 복구하지 않는다. retired라면 새 ID. 다른 원정대의 claim이 있으면 충돌 보류. 관찰 사이 구분 불가한 재생성까지 탐지했다는 보장은 하지 않는다.

### 캐시와 진행 중 결과

인증된 캐릭터 power는 (회원, character_id, lifecycle_revision, credential_version)로 재사용/lease 범위를 정의한다. 비인증 preview는 (회원, 등록ID/등록version 또는 preview generation, 서버, 이름, 키version) 범위로 분리한다. 이름만으로 preview와 canonical power를 overlay하지 않는다. 현 PowerCache의 (actor,server,name)는 기존 캐릭터 세대의 값 증거로 사용하지 않는다. 과거 정상값의 출처를 증명 못 하면 새 세대에는 null로 시작한다.

신선한 lifecycle 관찰은 이전 summary 캐시 hit로 대체하지 않는다. 이미 진행된 preview/summary/Armory/power/challenge는 commit 전 요청 시작 당시 등록/소유/roster/lifecycle/claim/credential revision을 대조하고 다르면 반영0. 종료된 ID에 이름 기반 결과를 연결하지 않는다. 삭제 이전에 시작한 worker는 기존 기한/generation fencing에 더해 ID 세대까지 일치해야 한다. 오래된 proof challenge도 무효화/409로 끝내고 새 관찰이 필요하다.

## C. 원자성·API 초안·구현 단위

### Transaction과 설정

확정 퇴역1건당 다음을 한 transaction으로 처리한다: 관찰 근거·revision 재검사 → 이력 unique 삽입 → ID retired/운영 payload 제거 → claim 해제 → 활성 Activity 제거/대표null → settings needs_reconfiguration/version 증가 → roster/등록/lifecycle revision 증가 → 기존 캐시/lease 세대 무효화 → 멱등 성공 기록. roster 전체 적용은 한 transaction이며 일부만 정리하지 않는다. 중간 실패는 모두 rollback한다. provider limiter의 독립 관찰은 기존 #7처럼 업무 transaction과 별개다.

활동/대표가 영향을 받으면 유효한 기존 선택은 남기되 state=needs_reconfiguration, 사라진 대표는null, 자동 대체 없음. 전부 없어도 시스템 전이에 따른 빈 상태를 허용하고 기존 사용자 PUT의 최소1명 규칙은 유지한다. 사용자 후속 결정으로 대표 변경5분 cooldown을 전체 제거한다. 기존 복구 한정 예외 제안은 폐기한다. 내 계정에 표시한 사용 선택 캐릭터의 아이콘 터치로 대표만 바꾸는 UX와 전용 API를 분리한다. [Flutter UI/UX 설계 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6183888735) 후 범위/상태표현을 대조해 API 계약을 확정한다. 현재 서버는 아직 기존5분 동작이다.

과거 완료/참가 Snapshot은 수정/연쇄삭제하지 않는다. 미래 미완료 파티는 회원 membership을 유지하고 suspect부터 확인필요를 표시한다. create/apply/join/approve/replace/group 명령은 최신 ID 사용 가능 여부 재검사. 교체/탈퇴는 옛 ID 소유가 아닌 본인 회원 membership+revision으로 허용하며 새 대상의 본·부계정 소유·레이드/역할/수치/구성/일정과 회원별 시간점유를 검증한다. 한 회원 한 파티 한 자리 및 회원 단위 동시간 확정점유는 DB 제약/transaction에서 보장한다. 교체는 옛/새 점유·slot·snapshot·변경내역 원자 갱신, 완료경합은 동일 파티 revision의 한 순서만 성공. 파티장/마지막1인/반복방 기존 제품정책은 미래 파티 계약에서 대조하며 이번에는 코드/테이블을 만들지 않는다.

### REST 초안 — 합의 전 OpenAPI 미반영

기존 strict DTO에 필드/enum을 바로 추가하지 않기 위해 **별도 V2 생명주기 경로**를 제안한다. /v2는 아직 없는 신규 버전 제안이며 서비스 전체 강제 이전이 아니다. 공통 App Bearer/no-store, UUIDv4 멱등key·lease30초/성공24시간/tombstone24시간은 기존 의미를 따른다. 아래 모든 명령의 unknown field/query/null 규칙은 strict다. GET은 외부 호출/자료 삭제 없음.

| 경로 제안 | 입력/성공 | 의미 |
|---|---|---|
| GET /v2/me/game-accounts/{registration_id}/characters | cursor optional; 200 `{items,next_cursor,registration_version,ownership_revision,roster_revision,settings}` | 캐릭터 최신 운영 목록. items=기존 CharacterOut 의미+필수 lifecycle_revision/int·lifecycle_state enum·usable/bool·blocked_reason string|null. retired는 운영 목록 제외. preview는 character_id/lifecycle_revision null·state preview·usable false. 페이지 최대50. settings는 기존 SettingsOut 형태, ownership_revision은 미인증 시null |
| POST /v2/me/game-accounts/{registration_id}/refresh | 멱등key; `{expected_registration_version,expected_ownership_revision,expected_roster_revision}`(후자2개 미인증시 필수null); 200 `{registration_version,ownership_revision,roster_revision,added_count,suspect_count,retired_count,evidence_status}` | 원자적 lifecycle 적용. evidence_status=validated/observation_only/pending. 성립 가능한 suspect는200/observation_only, 확정근거 부족은retired_count0/pending. 실패/충돌은400/409/503이며 자료소멸0 |
| POST /v2/me/game-accounts/{registration_id}/lookup-recovery | 멱등key; 위 revision3개+`lookup_character_name`; 200 `{registration_version,lookup_character_name}` | 전체성/원정대 연결 증거 검사 뒤 기준 이름 변경. 증거부족409. 클라이언트가 account_id를 지정하여 소유를 주장하지 않음 |
| GET /v2/me/character-retirements | cursor optional; 200 `{items,next_cursor,history_revision}` | 본인 이력/기기정리 재적용 원본. items는 아래 고정필드. 계정단위 필터는 초기 제외 |

이력 item 필드는 필수이며 nullable를 명시한다: history_id/character_id/game_account_id UUID, server_name/character_name/class_name string, combat_power/item_level string|null, power_fetched_at/item_level_fetched_at UTC|null, retired_at UTC, lifecycle_revision int>=1. 회원ID는 Bearer scope로 제한하고 응답에 중복 노출하지 않는다. 원래5값 외 메타데이터는 식별/정리/시각용이다. 이력의 공개 evidence 원문은 반환하지 않는다. cursor는 HMAC 서명·회원/경로/snapshot revision+offset에 묶고 max50·history revision 변경 시409 CURSOR_STALE. next_cursor는 항상 필수 string|null. 시각은 UTC, 값 없는 시각/수치는 필수null이다.

정리 ACK API는 초기 제외한다. 서버는 이력을 GET할 때마다 유지하며 Flutter는 로컬에 (Backend환경,회원,character_id,lifecycle_revision) 적용표를 두고 같은 정리를 안전하게 재적용한다. 정리 전 서버 전체 페이지 수집·revision 일치, 기기 transaction으로 이력 표시/매핑된 운영자료 정리/적용표를 함께 갱신하고 실패 시 rollback/재조회한다. 기기 적용 실패는 서버 퇴역을 rollback하지 않는다. 이름만 같은 로컬 캐릭터를 삭제하지 않는다. 기존 기기 행에 서버 ID mapping이 없으면 자동 파괴 정리를 하지 않고 확인필요로 남긴다. 이 mapping 전환은 Flutter 구현 단위이며 사용자 자료를 이름으로 일괄 연결하지 않는다.

### 오류·replay·호환성

기존 `{error:{code,message,request_id,...retry}}`, 앱401/403·키409/503·429/Retry-After 유지. 추가 제안: 409 CHARACTER_UNUSABLE(종료/차단 대상 사용), ACCOUNT_BINDING_EVIDENCE_PENDING, ROSTER_EVIDENCE_PENDING, IDENTITY_CONFLICT(기존), REVISION_CONFLICT(기존), CURSOR_STALE(기존). HTTP404 lookup은 현재 provider가 UPSTREAM_UNAVAILABLE로 축약하므로 별도 내부 not-found 관찰 구분이 필요하다. 클라이언트 오류는503 UPSTREAM_UNAVAILABLE 유지 가능하며 그 자체로 자료삭제/상태전이는 없다. 근거부족 lookup-recovery는409, 불량/부분을 정상으로 오인하지 못한 응답은503, 형식이 유효한 관찰의 확정증거 부족은200/pending으로 구별한다.

완료 멱등 replay는 당시 성공 결과이며 최신 자격 허가증이 아니다. 현재 회원/세션/리소스 접근 검사는 유지하고 외부 재호출/정리 재실행 없음. 기존 종료 ID가 replay DTO에 보이더라도 클라이언트는 최신 GET 우선, 최종 서버 명령은 현재 상태 재검사. 새 명령 stale revision은409→GET→사용자 재결정/newkey. 자동 덮어쓰기 없음.

V1 DTO는 초기에 wire를 보존한다. 신규 V2의 requirednullable·enum과 미선택 대표null/빈 활동을 Flutter strict parser에 명시 적용한다. 이력5값에는 character_level 등 V1 필수필드가 없어 retired 투영 제안을 폐기한다. 퇴역은 V1/V2 운영 목록/count/대표요약에서 제외하고 별도 이력으로 제공하는 의미 전환안을 Flutter와 합의한다. old mutation/proof/power도 동일 사용차단/fencing을 거쳐 우회가 없어야 한다. V1 행동 변화는 staged rollout 필요하며 최종 V1 유지/전환 시점을 Flutter와 합의하기 전 배포하지 않는다. 새 필드를 추가하지 않아도 이 의미 변화는 계약 변경이다.

### Migration 및 독립 구현 순서 제안

1. **계약 수용/제품 선택 확인**: 증거부족 시 자동 확정/복구 보류, V2/구버전 전환, cooldown 제거/대표 전용 API의 Flutter UI/UX, ID매핑 없는 기기자료 자동정리 금지의 영향을 Flutter가 대조. 이력 운영 보관정책은 공개 전 별도 결정.
2. **ID·상태·차단 기반**: lifecycle columns/claim/retirement+회원 history revision 및 FK 추가, 기존 Character ID 보존·claim backfill·충돌 사전진단, 이름 전역 unique는 새 제약 검증 후 교체. 기존 missing을 자동retired로 이관하지 않음. suspect차단/canonical 보류·기존 전 경로/캐시세대/fencing·V2 read를 한 구간으로 구현/격리검증. 기존 이름cache는 보존하되 새캐시로 재사용하지 않는다. 기존 live 소멸정리는 닫혀 있음.
3. **신뢰 관찰 적용·복구 명령**: evidence adapter·revision 검증·원자 퇴역/이력/설정정리·replay·lookup-recovery·이력cursor 구현과 mock 전체경계 검증. live 근거 확보된 분기만 활성화하며 mock으로 실제 전체성을 선언하지 않는다. 공개 증거 우회 API 없음.
4. **Flutter 연결·실인수**: 게시된 계약 SHA로 strict DTO/상태/재선택/이력/ID mapping/기기정리 복구를 연결. 필요 변경/성공 실패를 같은 Issue로 회신. 구현 인계 전 해당 구간 검증·commit/push/원격확인. 실제 additive migration 적용·기존 종속자료 정리는 대상/영향과 별도 승인 후 수행.
5. **향후 파티/그룹**: 본 계약의 사용불가/회원membership/점유/과거snapshot 보존을 소비. 이번 구현 완료 조건에 파티 기능 전체를 넣지 않는다.

최소 검증은 PostgreSQL에서 전체성/연결근거 실패 삭제0, 실패/404 보존, 신규1/퇴역1·이력unique·replay·중간rollback, suspect 해제근거/retired부활0, 같은이름 A먼저/B먼저/동시claim경합, 이름만으로 소유이전0, 기준이름 복구의 잘못된 원정대 거절, 활동/대표 재구성, oldcache/late worker/challenge/key/회원 전환, V1 우회차단/strict V2/cursor를 포함한다. 기기정리 실패 재적용은 Flutter 담당이다. 미래 파티는 8인 대표 사례와 파티장/마지막1인/완료경합만 해당 구현 시 검증한다.

## 이번 결과와 다음 인계

문서 검토만 완료. 구현/OpenAPI 새SHA·migration·자동 테스트·실provider 검증 결과는 없다. docs/character-lifecycle의 로컬 미커밋·미push 문서이며 dev 미반영이다. Issue 댓글에 필수 계약 내용을 직접 게시해 원격에서 읽을 수 없는 로컬 문서만 참조하지 않게 한다. 다음은 Flutter의 A/B/C 대조 및 구현 단위 수용 회신이다. 이 검토만으로 기능 구현에 착수하지 않는다.

[전체 검토안 Issue 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6183753309) 게시 완료. 이후 계약 대조·구간 수용 회신을 기다린다.

2026-10-15 사용자 결정: 대표 변경 cooldown 전체 폐지·내 계정 표시 캐릭터의 빠른 대표 선택/대표 전용 API 제공 방향. [네이티브 UI/UX 설계 의뢰](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6183888735) 게시 완료. 현행 원정대별 대표 범위와 새 화면의 범위는 Flutter가 명시하도록 요청했다. live 증거 및 연결 전환 질문은 Backend 보완 과제로 남는다.

## 보완 회신 — 앞선 제안과 다를 경우 이 보완안을 우선한다

[Issue 전체 보완 답변](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6183941103). 아래 내용은 아직 계약 수용/구현 완료가 아니다.

## Backend 보완 회신 — live 가능 범위·증거 조건 분리·최소 연결 전환

6183781483의 1번/3번 보완 답변입니다. 2번은 사용자 후속 결정에 따라 **대표 변경 cooldown 전체 폐지·빠른 대표 선택 전용 API 분리**로 정리했고, 6183888735에서 Flutter UI/UX 설계를 요청했습니다. 복구에만 cooldown 예외를 주는 이전 제안은 폐기합니다. 아래는 검토안 보완이며 기능 구현/전체 계약 수용을 뜻하지 않습니다.

### 1. 신규 추가에는 소멸용 전체성 증거를 일괄 요구하지 않도록 정정합니다

이전 검토안에서 신규 추가에도 전체성을 필수로 둔 부분은 과도했습니다. **목록에 실제로 나타난 새 캐릭터의 소속 확인(긍정 증거)**과 **목록에 없다는 이유로 기존 캐릭터 소멸을 확정하는 것(부재 증거)**은 분리할 수 있습니다.

신규 canonical 추가의 더 작은 조건은 다음과 같습니다.
- 서버가 검증한 기존 원정대 연결/연속성이 있고, 신선한 siblings 응답 안에 새 캐릭터의 서버/이름 및 필수 필드가 정상적으로 나타남.
- 기존 ID/이름 claim과 미해결 충돌이 없고, commit 전 회원/세션·키version·등록/소유/roster revision을 재검증함.
- 기존 ID 재사용/자동 개명 연결 없이 새 UUID·빈 개인 빌드로 생성함. 활동/대표는 자동 선택하지 않음.
- 이 조건으로 추가하더라도 같은 응답의 누락을 자동 소멸로 해석하지 않음. **소멸용 전체성 증거는 신규 추가의 필수조건에서 제외**하고, 원정대 연결 증거는 유지함.

이는 사용자 정책의 ‘정상 전체 조회’에서 소멸 검증과 동일한 강도의 증거까지 요구한 Backend 제안을 축소한 안입니다. 일부임을 아는 응답을 ‘전체’라고 표시하거나 현재 live에서 소속 검증이 끝났다고 선언하지 않습니다. 이 긍정 증거 기준으로 구현 단위를 분리하는 방향을 Flutter에서 대조해 주세요.

한편 **기존 이름 하나의 중첩, JWT 보유, 사용자 입력만으로 기존 인증 원정대 연결을 검증하지 않습니다.** 따라서 전체성 요구를 낮춰도 현재 adapter의 원정대 연결 증거 부족이 자동으로 해결되는 것은 아닙니다.

| 사용자 흐름 | 현재 코드/live 상태 | 제안 구현 후 열 수 있는 조건 / 계속 닫히는 부분 |
|---|---|---|
| 로그인·키·등록 preview·저장자료 조회 | 기존 계약으로 가능 | 기존 흐름 유지. preview가 canonical/소유 인증은 아님 |
| 미인증 preview에 새 관찰 표시 | 현재 refresh로 가능 | 비권위 목록 갱신 가능. 소유ID/퇴역 이력/개인자료 자동정리 없음 |
| 이미 등록된 캐릭터의 표시용 profile 전투력 | 현재 가능 | 새 캐시/ID 전환 후에도 현재 등록 범위·키·상태 검사로 가능. profile 성공을 소유 증명으로 사용하지 않음 |
| 인증 원정대에서 새 canonical ID 추가 | 현재 reconcile는 목록만으로 추가하므로 새 설계의 증거 수준과 다름 | 긍정 관찰+검증된 원정대 연결이면 전체성 증거와 독립 가능. **현 live 연결 검증이 확보되지 않은 분기는 보류** |
| 누락을 suspect로 낮추고 신규 사용 차단 | 현 reconcile의 suspect/eligible=false 일부 구현됨. 전 경로 차단 완료는 아님 | 신뢰할 수 있는 기존 원정대 연결 안의 구체적 불일치일 때 가능. 404/키/네트워크/빈/파싱실패만으로 전이하지 않음 |
| suspect의 동일 ID 복구 | 현 코드는 이름 재출현으로 confirmed 복구 | 새 설계에서는 해당 세대 연속성·원정대 연결·충돌없음 필요. 이름만 재출현이면 보류 |
| 소멸 확정·이력/종속자료 정리·이름 claim 해제 | 현 live disappearance_validated=false | 전체성+원정대 연속성+신선한 관찰 근거 확보 전 비활성. mock 성공만으로 활성화하지 않음 |
| lookup 기준 이름 변경 | 현행은 고정 lookup_name이며 전용 복구 API 없음 | 기존 원정대 연결을 새 조회 대상으로 검증할 때만 변경. 전부 개명/삭제돼 연결 근거 없으면 보류 |
| 새 원정대의 옛 이름 재사용 | 전역 unique/canonical 추론 개선 필요 | 옛 ID 종료/claim 해제+새 원정대 독립 검증 후 새 ID. 먼저 관찰되면 충돌 보류, 이름만으로 이전 금지 |
| 대표 빠른 변경 | 전용 API 없음·기존 설정 PUT은5분 정책 | 사용자 결정에 맞춘 독립 API/앱 연결 후 사용 가능. 새 lifecycle 소멸 증거를 기다릴 이유는 없으며 현재 유효한 본인 사용선택 캐릭터를 검증. UI/UX 회신 후 계약 확정 |

‘제안 구현 후 가능’은 지금 구현됐다는 뜻이 아닙니다. 현재 live에서 장비 proof가 보류 중이므로 신규 인증 원정대 생성/이전의 실서비스 완료도 아직 아닙니다. 기존 #3 장비 보류는 유지합니다.

### 2. 공식 근거 조사 담당·종료 조건과 대안

Backend가 다음을 담당합니다. 이미 확인한 자료: [공식 changelog](https://developer-lostark.game.onstove.com/changelog)는 siblings를 계정 전체 캐릭터 프로필 반환으로 설명합니다. [시작 안내](https://developer-lostark.game.onstove.com/getting-started/)는 JWT를 API client의 호출 자격증명으로 설명합니다. 이번 추가 조회에서도 API 상세 경로는 접근 실패했고, 공식 페이지의 CHARACTERS 링크는 시작 안내로 연결돼 상세 schema 원문을 확보하지 못했습니다. 이는 필드가 없다는 증명이 아닙니다. 실키/응답원문/공급자 접촉은 이번에 수행하지 않았습니다.

| 조사 대상 | 확보할 결과 | 종료 조건·미확보 시 처리 |
|---|---|---|
| 공식 Characters/Armory OpenAPI schema·문서의 버전과 응답 의미 | 전체성/빈·404 의미/서버 범위·영구 character/account 식별자·갱신/생성 세대 보장 여부를 필드별 표로 기록 | 해당 버전 원문·근거 링크를 확보하거나 접근불가/관련 보장 미기재를 명시해 조사 결과 회신. schema만으로 의미가 불명확하면 ‘검증됨’으로 올리지 않음 |
| 원정대 연결·소유 증거 adapter | 어떤 관찰이 기존 account/캐릭터 세대에 결부되는지, 기존 장비 proof의 미확인 schema/갱신 의미 | 증거가 실제 판정 조건을 충족하는 adapter 계약·대상 검증 또는 명시적 불가 판정. 이름 목록 중첩만으로 대체하지 않음 |
| 실제 관찰이 필요한 부분 | 승인된 최소 단건 관찰로 필드 형태/오류 매핑 확인 | 관찰 범위·결과만 기록. 정상 예시1건은 전체성/영구 동일성 보장이 아님. 키원문 공유/한도소진/자료삭제 요구 없음 |

종료 조건은 ‘근거를 확보할 때까지 무기한 대기’가 아니라 **확보한 보장/미기재/접근불가와 각 사용자 흐름의 제공 가능/불가를 판정해 회신하는 것**입니다. 공식 schema의 보장 없이 반복 호출로 전체성을 추정하지 않습니다. 공급자 답변이 필요한 경우 질문 초안을 마련할 수 있지만 외부 문의는 별도 지시 없이 보내지 않습니다. 현재 조사 결과만으로 자동 소멸·동일 ID 복구·모든 이름이 사라진 원정대 재연결을 제공 가능하다고 확정할 수 없습니다.

근거가 끝내 없을 때의 대안은 **후속 선택지이며 현재 승인된 계약이 아닙니다.**
- preview/표시만 갱신하고 suspect/충돌은 보류: 기존 자료·ID 유지, 자동 추가/복구/삭제 및 이름 claim 해제를 보장하지 못함.
- 새 이름으로 독립 검증하여 **새 ID** 등록: 새 대상의 현재 제어/소속을 확인할 수 있을 때만 가능. 옛 캐릭터와 동일 개체라는 보증, 옛 빌드/권한 승계는 없음. 옛 claim 충돌은 별도로 해결해야 함.
- 사용자 명시 확인으로 본인 앱 자료를 보관/제거: 제품 정책을 따로 합의한다면 가능하지만 ‘게임 캐릭터 소멸 확인’으로 표시하지 않음. 타인 소유 판정/권한 이전/전역 claim 자동 해제의 증거로 쓰지 않음. 과거 공동 Snapshot/회원 membership은 보존.

현재 정책 그대로 **자동 개명 승계는 제공하지 않으며**, 전체 원정대가 개명/삭제돼 연결을 잃은 경우의 자동 복구, 부재만으로 자동 정리, suspect 동일 ID 자동 해소는 근거 확보 없이 제공할 수 없습니다. 위 대안을 이번 댓글로 채택하지 않습니다.

### 3. V1/V2·strict DTO·ID/캐시 전환의 최소 범위

아래는 **구현 구간 제안**입니다. 현재 코드/OpenAPI/migration은 그대로이고 endpoint/필드 확정 SHA는 없습니다. 모든 구간을 한 번에 배포하지 않습니다.

| 순서 | Backend 변경 | Flutter 연결·현재 live 가능 범위 |
|---|---|---|
| P0 계약 대조 | 아래 목록·V1 의미변화·nullable/enum·ID매핑 기준과 대표 UX 계약 확정 | 이번 검토 단계. 기능 전환 없음 |
| P1 ID/캐시 기반 | 기존 UUID 보존·lifecycle revision/NameClaim/이력 revision 기반, claim 충돌 사전진단·backfill. power에 canonical ID세대/preview등록세대 분리, 전 경로 최신 revision fencing | 서버 ID가 있는 본인 캐릭터를 저장자료 GET으로 식별 가능. 기능별 wire는 V1 유지. 실DB 적용은 별도 승인/검증 후. 자동 소멸/동일ID 복구는 닫힘 |
| P2 V2 읽기·안전한 명령과 차단 | V2 characters/이력 read·refresh/lookup-recovery 근거별 pending, V1 writer/proof/profile 우회 방지. 기존 동작 제한이 생기는 지점은 Flutter와 같은 전환 구간에 반영 | V2 strict DTO·상태/충돌/ID mapping/cache 연결, 사용할 수 있는 조회·대표 변경 등을 먼저 제공. live 증거가 없는 분기는 pending/거절로 안내 |
| P3 증거 기반 퇴역/복구 | 근거 adapter와 원자 이력/정리/claim해제, 해당 근거를 충족하는 분기만 활성화 | 증거 없는 live 자동처리는 계속 비활성. 기기 정리 재적용은 서버 ID매핑된 행만. 미완료 파티 전체 구현은 제외 |

P1도 단독으로 과거 이름 cache를 새ID에 연결하거나 기존 ID를 부활시켜서는 안 됩니다. **ID/claim/fencing/cache 범위를 함께 검증한 뒤** 연결용 게시 단위로 인계합니다. V1→V2 전체 복제나 인증 버전 변경은 필요 없습니다.

#### 구체적인 영향 목록

- **인증6 API, 회원설정 GET/PUT, 회원키 GET/PUT/DELETE/restore:** 경로·DTO·오류 그대로. lifecycle 기능을 이유로 새 로그인을 요구하거나 키를 재등록하지 않음.
- **V1 preview·등록 POST/PATCH/DELETE·등록 GET:** 기존 wire/strict DTO는 유지. preview는 여전히 canonical ID가 없음. 본부전환/label 의미도 유지. 다만 대표 요약/선택/캐릭터 수가 lifecycle에 따라 달라지는 시점은 P2 계약/앱 전환에 묶음. 이름으로 타 원정대 소유를 추론하는 기존 등록/challenge 경로는 공통 검증에서 차단.
- **V1 characters GET:** `character_id`, 기존 `settings_version/ownership_revision/roster_revision`을 초기 매핑에 활용. 기존 strict DTO에 lifecycle 필드를 몰래 추가하지 않음. V2에서만 lifecycle_state/revision/usable/blocked_reason과 새 읽기 envelope를 명시 적용. preview의 lifecycle_revision은 **필수 nullable**, canonical은 필수 integer>=1. 전 답변의 ‘필수int’와 preview null을 이 의미로 정정.
- **V1 refresh POST:** P2 전환 후 legacy 응답은 기존 RefreshOut 그대로. 공통 reconcile에 같은 차단/fencing을 적용하고, V1을 통해 새 소멸 기능이 우회 실행되지 않음. V2 refresh는 expected revisions와 evidence_status/retired_count 등 새 DTO. 증거가 부족하면 pending/retired_count0이며 실패를 소멸로 변환하지 않음. 단순 field 추가가 아니라 의미 변화이므로 OpenAPI와 앱 적용 구간을 같이 인계.
- **V1 character-settings PUT:** 활동 목록/대표를 함께 저장하는 기존 DTO는 초기 유지. 사용자 결정에 따라 cooldown 판정은 기존 경로에서도 제거하고 `next_change_at` 필드는 strict 호환을 위해 **필수nullable null**로 유지. 새 대표 전용 명령도 같은 settings_version을 사용해 기존 전체저장과 경합 시 한 승자만 성공하도록 제안. 활동 목록은 대표 전용 명령이 변경하지 않음. 대표 범위/구체 endpoint는 Flutter UX 회신 뒤 확정. 기능 인계 전에는 기존5분 동작 그대로.
- **V1 profile 전투력 POST와 CharacterOut/representative_summary의 power overlay:** 새 lifecycle 필드를 기존 응답에 추가하지 않음. 기존 이름 입력은 현재 등록의 ID/preview generation에 **유일하게 매핑될 때만** 수용. suspect/retired·충돌·다른 generation에 과거값을 연결하지 않으며 canonical 사용불가 대상은 공통 오류로 차단. 더 세밀한 ID입력/혼합batch별결과가 필요하면 V2 power DTO를 명시 제안하고 기존200batch에 새 required필드를 몰래 넣지 않음. 유효한 기존 캐릭터 표시용 profile은 계속 가능하며 소유권을 생성하지 않음.
- **장비 challenge start/confirm:** 경로·기존 DTO는 유지하되 proof/연속성 근거·ID/claim revision 불일치에 공통409/기존 pending을 사용. lifecycle/claim 변경 이전 challenge 결과로 옛 ID/소유를 되살리지 않음. 기존 proof 보류를 해제하지 않음.
- **퇴역 후 V1 읽기:** 전 제안의 ‘이력5값으로 기존 CharacterOut을 투영’은 부족했습니다. CharacterOut에는 character_level 등 이력에 없는 required필드가 있어 임의값으로 만들지 않겠습니다. 퇴역된 캐릭터를 V1/V2 **운영 목록·count·대표요약에서 제외**하고 전용 이력 GET으로 제공하는 전환안을 제안합니다. 이 목록 의미 변화는 P3 활성화 전 Flutter 수용 필요. 과거 raw summary를 영구 보존하는 우회는 하지 않음. 소멸 확정 전 suspect는 기존 V1 roster_status=suspect/eligible=false로 표현하고 자료는 보존합니다.

추가 code/enum·오류 상태도 계약에 먼저 열거하고 Flutter의 error 처리와 대조합니다. ‘DTO 필드가 같다’는 이유로 무조건 호환이라고 보지 않습니다.

#### 초기 ID mapping과 캐시의 선행 조건

1. P1은 기존 canonical UUID를 유지한다. Flutter는 **동일 Backend 환경·현재 회원·등록/소유/roster revision**에 묶인 전체 페이지를 수집하며 CURSOR_STALE이면 처음부터 다시 받는다. 서버 GET은 저장자료일 뿐 새 소유 검증이 아님.
2. 이미 server character_id를 가진 기기 행만 동일 scope에서 연결한다. 이름만 같은 로컬 전용/역할 Snapshot 행은 자동 ID매핑·삭제하지 않는다. 연결 근거 없는 행은 로컬/미연결 상태 유지, 명시 연결 UX는 필요 시 별도 합의한다. V2 출시 자체로 기존 로컬 자료가 전부 서버 ID를 갖게 되지는 않음.
3. canonical cache/lease는 회원·character_id·lifecycle_revision·키version, preview는 회원·등록ID/preview세대·서버/이름·키version으로 분리. **기존 이름cache를 새세대 최초값/퇴역이력의 증거로 복사하지 않음.** 출처를 증명한 현재 캐릭터 저장값만 보존하고 새ID는null. credential 변경 및 종료 전에 시작된 worker/challenge/replay도 generation/revision 검사.
4. Flutter의 서버 표시 캐시도 환경·회원·server ID세대에 묶는다. 서버 profile 마지막 전투력은 서버 관찰값이며 로컬 선호역할 Snapshot의 마지막 빌드값이라고 표시/덮어쓰지 않음. 미연결 로컬 캐릭터 표시와 canonical 캐시를 이름만으로 혼합하지 않음.
5. V2 이력의 매핑된 ID만 기기 transaction에서 정리/적용표에 기록. 실패 시 재조회/재적용 가능, 이름만으로 다른 로컬 빌드 삭제0. 서버 이력 유지/페이지 revision과 기기 적용표로 복구하며 두 저장소를 하나의 transaction이라 하지 않음.

### 다음 실행·검증 경계

Flutter는 긍정증거 기준의 신규 추가 분리와 위 전환 순서/legacy 의미변화 및 이미 의뢰한 대표 UI/UX를 대조해 주세요. Backend는 공식 schema/근거 표를 위 종료 조건으로 정리하고 수용된 구현 구간을 구체화합니다. 현재는 **문서·계약 검토만 수행, docs/character-lifecycle 미커밋/미push·dev 미반영, 새 기능/OpenAPI SHA·migration·자동 테스트·실provider 검증 결과 없음**입니다. 기존 로그인/등록/키 정상 시험이나 원문키·한도소진 시험은 요청하지 않습니다. 새 설계를 코드·실DB에 적용하거나 Issue를 종료하지 않았습니다.

## 대표 API 독립 구간 수용/구현

[Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184322765)으로 대표GET/PUT·5분제한 제거만 독립 구현했다. feat/representative-selection으로 기존 작업 브랜치 이름을 변경하고 문서/기존 #7 종료 기록을 보존했다. [대표 구현/검증 안내](../account/ISSUE_8_REPRESENTATIVE_DEVELOPMENT.md). 이 수용은 본 문서의 전체 lifecycle/NameClaim/V2/정리 계약 수용이 아니다.

## 공식 schema 조사 완료 — 이전 접근불가 기록 보완

[실제 원문 확보/판정](ISSUE_8_PROVIDER_EVIDENCE_REVIEW.md)·[Issue 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184587789). 공식 시작안내 HTML에서 Swagger 소문자 경로를 확인해 Characters/Armories JSON을 확보했다. 이전 문서접근 실패는 최종 조사 결과가 아니다. 필드형태는 확인했으나 영구ID/생성세대/전체성인증/장비해제 의미보장은 미기재, FAQ도 데이터반영지연을 안내한다. 증거없는 자동소멸/같은ID복구는 현재합의대로 보류한다. L1비활성기반구현은 별도구간수용을 기다린다.
