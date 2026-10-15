# Issue #8 — 대표 빠른 선택 API 계약 제안

2026-10-15. [Flutter 확정 UX](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6183971014)·[사용자 cooldown 제거 결정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6183888735)을 반영한 계약이다. [Flutter 수용/독립 구현 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184322765)을 기준으로 구현·OpenAPI 반영을 완료했다. 아래 제안/미커밋 표현은 작성 당시 기록이며 현재 상태는 [실행 안내](ISSUE_8_REPRESENTATIVE_DEVELOPMENT.md)를 따른다. 생명주기 전체 계약과 별개로 수용/구현할 수 있으며 live 소멸/장비 증거 보류를 해제하지 않는다.

## 경로와 적용 범위

`GET /v1/me/game-accounts/{registration_id}/representative`

`PUT /v1/me/game-accounts/{registration_id}/representative`

새 /v1 경로2개를 additive로 제안한다. V2 생명주기 전체 도입을 기다리지 않는다. 앱 Bearer 본인 회원/세션 검증, 성공·오류 모두 Cache-Control:no-store. 외부 Lost Ark 호출/키 복호화 없음, 회원 Lost Ark 키 미등록이어도 저장자료 조건을 충족하면 사용 가능. 로그인/소유 인증 자체를 생성하지 않는다.

PUT은 **현재 메인 등록 원정대**에만 허용한다. 기존 부계정 설정 PUT은 기존 원정대별 범위를 유지하며 전체 cooldown만 제거한다. 이 명령은 메인 여부·활동 선택·표시 순서/개수·역할/빌드·파티 참가 캐릭터를 변경하지 않는다. 서버에는 기기 표시순서/숨김 상태가 없으므로 서버는 활동 선택을 검증하고, Flutter는 표시 캐릭터 subset과 유효 server ID mapping을 추가 제한한다. 이름·로컬 representativeId로 대상을 보내지 않는다.

## PUT 입력

헤더 `Idempotency-Key: UUIDv4` 필수. body의 아래5필드 모두 필수·null 불가·추가필드 금지. query는 받지 않으며 중복/알 수 없는 query는400이다.

```json
{
  "character_id": "11111111-1111-4111-8111-111111111111",
  "expected_registration_version": 3,
  "expected_settings_version": 4,
  "expected_ownership_revision": 1,
  "expected_roster_revision": 7
}
```

character_id는 UUID string, revision/version은 bool·string 자동변환 없는 엄격 integer>=1. body user_id/account_id/is_main·활동목록·nullable 해제 입력은 받지 않는다. 등록ID와 game_account_id는 구분한다.

registration version도 받아 알럿 이후 등록변경/메인 전환을 검출한다. 기존 main 변경은 양측 등록 version을 올리므로 메인이 바뀌었다 돌아온 경우도 stale version이면409다. label 수정으로 version이 바뀌어도409→GET→재확인한다. 별도 main revision 테이블을 추가하지 않는다.

## GET/PUT 성공 DTO

GET200과 PUT200은 같은 최소 객체를 사용한다. 아래 필드는 항상 존재하며 unknown field를 추가하지 않는 strict DTO로 합의한다.

| 필드 | 타입/nullable | 의미 |
|---|---|---|
| registration_id | UUID / nonnull | 경로의 본인 등록 |
| game_account_id | UUID / nonnull | 검증된 등록의 원정대 |
| is_main | boolean / nonnull | 해당 조회/명령 commit 시점 메인 여부 |
| registration_version | integer>=1 / nonnull | 등록 version |
| settings_version | integer>=1 / nonnull | 기존 전체설정과 공유하는 version |
| ownership_revision | integer>=1 / nonnull | 현재 원정대 소유 revision |
| roster_revision | integer>=1 / nonnull | 현재 roster revision |
| representative_character_id | UUID / nullable | 저장된 현재 대표. 초기/시스템 재구성 시null 가능 |
| configuration_state | unconfigured/configured/needs_reconfiguration / nonnull | 기존 설정 상태 |
| next_change_at | null / required | cooldown 폐지에 따라 항상null |

GET은 본인의 활성 등록·현재 소유권을 검사하고 **비메인으로 바뀐 기존 등록도 조회 가능**하다. is_main=false를 통해 현재 범위를 확인한다. 소유 미확인/상실은403 OWNERSHIP_REQUIRED, 삭제/타회원/없는 등록은404 REGISTRATION_NOT_FOUND. 설정행 미생성 시 저장 없이 기존 의미의 version1/unconfigured/대표null로 응답한다. GET은 행 생성·version증가·provider 호출을 하지 않는다.

대표 ID가 있다고 항상 사용 가능하다는 뜻은 아니다. GET은 서버 저장 대표 상태를 알려 주며, 대상 자격은 캐릭터 GET의 eligible/roster_status 및 전체 활동/settings를 함께 확인한다. 생명주기 V2가 구현되면 해당 state/revision도 사용한다. 초기 제안에 새 사용가능성 필드를 기존 DTO에 억지로 추가하지 않는다.

## 변경·no-op·원자성

새 PUT은 transaction 안에서 본인 회원/세션 → 활성 본인 등록 → 소유권 → 현재 메인 → 기대4version/revision → 설정/활동/캐릭터 자격을 검사하고 commit 시점까지 일관되게 유지한다. 기존 game mutation 직렬화 lock을 재사용한다. 네트워크 호출이 없으며 DB lock 동안 외부 작업을 하지 않는다.

- 대상이 같은 원정대 canonical ID이고 현재 본인 소유·활동 선택 상태이며 사용 가능해야 한다. preview/다른원정대/타인ID는 허용하지 않는다. 현행은 confirmed만 허용, suspect/missing 및 향후retired/충돌 상태는 거절한다.
- 기존 대표가 suspect/없음이어도 새 대상이 위 조건을 만족하면 변경 가능하다. 옛 대표의 현재 자격을 변경 조건으로 삼지 않는다.
- 실제 대표가 바뀌면 representative_id만 변경하고 settings_version+1, next_change_at=null. 등록/소유/roster revision은 바꾸지 않는다. Configuration.state·활동목록·다른 설정은 그대로 유지한다. needs_reconfiguration을 대표 변경만으로 configured로 올리지 않는다. 다른 부적격 활동까지 자동 수정하지 않는다.
- 같은 대표를 새key로 요청해도 **먼저 모든 기대 revision·자격을 검사**한다. 일치하면200/no-op·settings_version 유지·아무 자료도 변경하지 않는다. 같은 대상이어도 stale version은409다. Flutter는 현재 대표 왕관 재터치 요청을 보내지 않지만 서버 no-op은 정의한다.
- 설정 미생성/빈 활동은 자동 생성·자동 활동 추가 없이409다. 기존 전체설정 저장/활동 선택 흐름을 먼저 사용한다.
- 대표 변경과 멱등 성공 결과 기록은 같은 transaction, 실패 시 둘 다 rollback. 다른 전체설정 PUT/활동수정/메인전환/소유이전/roster변경과 경합하면 직렬 순서에 따른 한 요청만 기대revision을 만족한다. 먼저 성공한 대표를 옛 전체설정 draft로 덮어쓰지 못한다.

## 오류와 명확한 복구

기존 GameErrorOut `{error:{code,message,request_id,...}}`를 사용한다. 새 오류code는 계약 수용 시 OpenAPI에 추가한다. 검증 입력/토큰·타인 자료를 오류에 반환하지 않는다.

| HTTP/code | 조건 | Flutter 다음 행동 |
|---|---|---|
| 400 INVALID_REQUEST | UUID/필수값/엄격정수·body/query 오류 | 요청 수정, 자동 재전송 없음 |
| 기존 앱401/403 | 세션 만료·폐기/회원 정지 등 | 기존 앱 인증 처리 |
| 404 REGISTRATION_NOT_FOUND | 삭제/타회원/없는 등록 | 등록 목록GET, 기존 왕관 요청 폐기 |
| 403 OWNERSHIP_REQUIRED | 미인증/소유상실 | 서버 상태 재조회·기존 인증 안내, 자동인증 없음 |
| 409 MAIN_REGISTRATION_CHANGED | 본인 등록이 더 이상 메인이 아님 | 등록 목록GET으로 현재 메인 확인·새 후보/알럿. 다른 등록으로 명령 자동이식 금지 |
| 409 REVISION_CONFLICT | 기대4revision 중 차이 | 최신 등록·대표/캐릭터GET 후 재선택·newkey |
| 409 SETTINGS_NOT_CONFIGURED | 설정행/활동선택 미준비 | 기존 선택 설정 흐름 안내 |
| 404 CHARACTER_NOT_FOUND | 해당 원정대에 없는 ID/접근 불가ID | 캐릭터GET, 이름으로 fallback 금지 |
| 409 CHARACTER_NOT_ACTIVE | 대상이 현재 활동선택에 없음 | 활동설정 확인, 자동추가 금지 |
| 409 CHARACTER_UNUSABLE | suspect/missing/retired 등 | 현재 상태 확인·유효한 다른 후보 선택 |
| 기존409 멱등code | 진행중/입력충돌/기한만료 | 아래 멱등 규칙 |
| 429 RATE_LIMITED | 기존 앱 공통 제한이 적용되는 경우 | Retry-After 준수; 대표변경5분 제한을 재도입하지 않음 |
| 503 SERVICE_UNAVAILABLE | 분류 가능한 일시 DB/lock 장애 | 처리여부 불명확이면 같은key/body 복구. 외부 provider 장애라는 뜻이 아님 |

검사 순서는 신규명령에서 등록 존재→소유권→메인여부→기대revision→설정/대상 자격으로 고정해, 삭제는404·소유상실403·현재 비메인은MAIN_REGISTRATION_CHANGED·메인이 돌아왔지만version이 바뀐 경우REVISION_CONFLICT로 구분한다. 비정상 내부오류/통신단절은 확정실패라 단정하지 않고 현재GET/멱등복구를 사용한다. SERVICE_UNAVAILABLE 처리는 구현 시 해당 경계를 실제 분류하고 검증하며 임의로 모든 예외를 성공/실패로 바꾸지 않는다.

## 멱등·응답유실·현재GET

기존 UUIDv4·회원/operation/key scope·30초lease/generation·완료응답24시간/tombstone24시간을 사용한다. digest에는 등록 target와 위5필드가 포함된다. 다른body/target의 같은key는409 IDEMPOTENCY_CONFLICT, 진행중은409 REQUEST_IN_PROGRESS/Retry-After2, 만료는409 IDEMPOTENCY_EXPIRED. 실패한 새명령의 재시도는 기존 retryable lease 의미를 따른다.

완료 replay는 **처음 commit 당시 응답**이며 지금의 메인/대표/자격을 보증하지 않는다. 현재 앱회원/세션·본인등록 접근과 소유권은 다시 검증한다. 삭제면404/소유상실403으로 replay를 거절한다. 메인 전환만 일어났고 여전히 본인소유인 기존등록은 과거성공replay 가능하며, 이때 과거 is_main=true를 UI에 적용하지 않는다. 현재GET과 등록목록을 우선한다. 현재 메인조건/expected version을 다시검사해 성공을 재실행하지 않는다.

Flutter 복구 순서:
1. 알럿 확인 시 환경/회원/세션·등록ID·현재 메인/대상ID·기대revision을 고정하고 한명령 진행 중 다른 왕관을 잠근다.
2. 200 뒤에는 representative GET으로 현재 대표·settings_version·is_main 확인 후 표시한다. 필요하면 기존 캐릭터GET으로 전체 활동/settings를 동기화한다. GET 실패는 저장실패가 아니라 확인중이다.
3. 응답유실/불명확이면 같은key·body·기대revision으로 원래 결과를 복구하고 현재GET 확인. **GET만으로 특정 요청이 완료/미완료라고 단정하지 않는다.** GET이 예전 값을 반환해도 진행중 원래명령이 나중에 commit할 수 있어 완료/명확실패 전 다른 새명령을 보내지 않는다.
4. 처리완료가 확인됐지만 다른 기기 변경/메인 전환으로 현재값이 다르면 최신GET이 이긴다. 새대표를 자동 재저장하지 않는다. key보관기한을 넘겨 결과복구가 불가능하면 현재GET 후 사용자 재확인/newkey로 진행한다. 이미 만료된 옛 lease는 commit 불가여야 한다.
5. 서버성공·기기반영실패는 현재GET/기기반영만 복구한다. 앱회원/세션/요청세대가 달라진 늦은응답은 버리고 메인 범위가 바뀌면 새목록을 사용한다. 관리화면 draft는 임의폐기/덮어쓰기 없이 stale 안내/명시 재확인한다.

## 기존 API·DB·배포 영향

- 기존 character-settings PUT에서도 대표변경5분 판정을 제거한다. next_change_at을 생성/응답하지 않는 것이 아니라 **기존 requirednullable 필드를 항상null로 반환**한다. 기존 DB timestamp는 판정에 사용하지 않고 설정 write 시null로 정리할 수 있다. GET은 쓰지 않는다. 대량 자료정리/migration은 필요 없다.
- 이 제안은 기존 Configuration/Activity/Character/Registration/RequestResult를 사용하고 새테이블/column을 요구하지 않는다. settings_version은 기존 전체설정 PUT와 공유한다. no-op을 포함한 기존 settings 의미는 별도 변경 없이 유지하며, 일반 대표변경 cooldown 제거만 공통 반영한다.
- 인증/회원키/회원설정/전투력 DTO는 바꾸지 않는다. 새2경로/DTO/code 및 기존 next_change_at/cooldown 의미 변경을 OpenAPI와 함께 검증한다.
- 현재 live 장비 proof 보류로 소유인증·활동선택이 완료되지 않은 사용자에게는 왕관 변경이 열리지 않을 수 있다. 전용 API가 이를 우회 인증하지 않는다. 격리DB로 소유/선택 상태를 검증할 수 있지만 실제 운영사용 가능 사용자 범위는 구분한다. 원정대 소멸근거·이력·NameClaim 전환은 본 API 제공의 일괄 선행조건으로 묶지 않는다. 생명주기 공통 검증이 추가되면 이 API에도 동일 적용한다.

## 최소 검증·다음 단계

계약 수용 후 PostgreSQL 대상검증: 본인메인/활동대표변경·no-op·활동/다른설정보존·next_change_at항상null·기존PUT도즉시변경가능·신규vs전체PUT경합·메인전환/복귀ABA·삭제/소유상실·잘못된ID/비활동/suspect·기존대표불가복구·needs_reconfiguration보존·재시도/replay/expiry/rollback·GET read-only/세션·strictDTO/OpenAPI 일치. 외부호출0을 검증한다. Flutter는 왕관/알럿·draft충돌·응답유실/GET복구·회원/메인 late응답·사용자 확인을 담당한다. 기존 로그인/키/성공흐름 일괄 재시험은 요청하지 않는다.

Flutter에서 경로/DTO·4revision·GET복구·메인한정/활동조건 및 기존PUT와의호환을 대조해 수용/수정 의견을 같은 Issue로 회신해 주세요. 수용 후 구현/검증 단위를 진행하고 실제 구현/OpenAPI SHA·commit/push/로컬적용 상태를 별도 인계합니다. **현재 docs/character-lifecycle의 미커밋·미push 제안문서이며 기능·OpenAPI·DB·자동테스트 변경/새SHA는 없습니다.** #8 전체 생명주기 수용·배포·자료삭제로 확대하지 않습니다.

[계약안 Issue 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6184022477) 게시 완료.

## 구현 시 호환성 보완

기존 character-settings PUT의 과거 성공 저장값에 next_change_at이 남아 있더라도 replay 응답에서 해당 폐지 필드만null로 투영한다. DB 저장 이력/대표·settings_version 등은 변경하지 않고 과거 명령을 재실행하지 않는다. 새 대표 명령의 replay는 원래 성공 응답을 유지한다. 기존 next_change_at 항상null 계약을 만족하기 위한 보완이며 표적 테스트로 검증했다.
