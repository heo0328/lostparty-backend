# Issue #3 내 계정 API 실행·검증·Flutter 인계

상태: 로컬 구현·작업 브랜치 게시. 구현/계약 SHA `254cb5de125ab1bcb2aa084e091eae976e9a078a`. dev/main 미통합, 실provider·Flutter 인수 후속. 원본은 [OpenAPI](../openapi/openapi.yaml), 요구·수용은 [Issue #3](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159847616), 설계는 [구현 계획](ISSUE_3_IMPLEMENTATION_PLAN.md)이다. 실제 검증 결과와 브랜치/게시 상태는 [DEV_LOG](project/DEV_LOG.md), 다음 실행은 [NEXT_WORK](project/NEXT_WORK.md)를 확인한다.

## 제공 범위와 현재 실연동 경계

12개 업무 API를 자체 Bearer session으로 제공한다. 로그인만으로 등록·canonical 계정·활동을 만들지 않는다. Firebase 연결·이관이나 Flutter 로컬 데이터 변경은 없다. 조회/등록/인증/소유권/활동 상태를 분리한다.

서버 `LOSTARK_API_TOKEN`이 없으면 외부 조회가 필요한 요청은503 UPSTREAM_UNAVAILABLE다. 값은 안전한 로컬 `.env` 또는 실행환경에서만 준비하며 Issue/앱에 올리지 않는다. 현재 live adapter의 장비 schema/해제 표현은 미실증이므로 장비 비교가 일치해도 `pending + PROVIDER_EVIDENCE_PENDING`으로 소유권 확정을 보류한다. canonical roster 감소를 이용한 이전은 `ROSTER_EVIDENCE_PENDING`, refresh 누락은suspect이며 자동missing 확정은 하지 않는다. 서버의 실제 증거 검증 코드를 보완한 뒤 해당 분기를 좁힌다. 클라이언트가 verified/proof/owner를 제출하거나 mock으로 전환할 API는 없다.

DB·인증·소유권 transaction·활동/대표의 정상/실패 흐름은 격리 pytest의 dependency 교체로 검증한다. 이 결과는 실제 Lost Ark/장비/Flutter 인수와 별개다.

## 로컬 실행과 migration

기존 [인증 실행 안내](AUTH_DEVELOPMENT.md)의 키/DB 설정을 재사용한다. 개발 Compose만 대상으로 실행한다.

```bash
docker compose build api
docker compose run --rm --no-deps api alembic upgrade head
docker compose up -d --build --wait --wait-timeout 180
python3 scripts/check_openapi.py
```

`0002_game_accounts`는 업무11개 테이블을 추가하고 기존 auth/user 행을 수정·import하지 않는다. downgrade는 파괴 작업으로 거절한다. 앱 버전 복구 시 추가 테이블을 보존하며 volume 삭제/DB 초기화를 하지 않는다. 실행 중 이미지와 로컬 코드·원격 계약 버전을 구분한다. 운영 배포는 별도다.

격리 테스트:

```bash
docker compose build api
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
```

test DB는 tmpfs PostgreSQL17이고 기존 개발 DB를 사용하지 않는다. fixture는0001 적용→기존 회원 행 생성→0002 적용→행 동일성을 확인하고 매 테스트 격리한다. migration/실제DB 실패는 sqlite/mock으로 대체하지 않는다.

## 요청·응답·상태

mutation에는 `Idempotency-Key: UUIDv4`, DTO는 snake_case/unknown field 거절, 시각은 UTC Z다. 이름1~64자, label1~40자, live 등록20개, canonical 캐릭터 최대200, page50/100. TTL·quota·lease는 OpenAPI의 `x-game-account-policy`에도 기록한다.

등록 예시(이름은 합성값):

```json
{"lookup_character_name":"sample-character","label":"본계정","is_main":true}
```

등록 결과의 registration_id와 canonical game_account_id는 다르다. 미인증 캐릭터는 character_id=null/roster_status=preview/eligible=false다. 이전 owner에게 다른 owner의 설정·canonical 캐릭터 권한ID를 응답하지 않는다. 기존 본계정 변경은 원자 전환, 제거 후 자동 승격 없음. 제거는 소유권 포기와 다르며 canonical·다른 계정 설정은 보존한다.

캐릭터 GET의 characters.items/next_cursor는 현재page, settings는 항상 전체 활동 집합/대표다. 전체page의 roster_revision/settings_version/ownership_revision이 모두 같아야 draft를 만들고 부분 로딩/실패 중 save를 막는다. CURSOR_STALE 또는 save409는 최신 재조회 후 사용자가 확인한다. draft를 자동 덮어쓰기·재제출하지 않는다.

설정 PUT:

```json
{
  "activity_character_ids":["11111111-1111-4111-8111-111111111111"],
  "representative_character_id":"11111111-1111-4111-8111-111111111111",
  "expected_settings_version":1,
  "expected_ownership_revision":1,
  "expected_roster_revision":2
}
```

current owner/confirmed/같은 계정/최소1명/대표 포함·중복 없음과 세version을 한transaction에서 검사한다. 첫seed는 cooldown없음, 대표가 실제로 바뀐 다음부터5분. 같은대표 재전송은 시각을 바꾸지 않는다. 누락대표 복구도 cooldown우회 없음. 실패는 전체설정을 보존하고 GET next_change_at를 안내한다.

configuration_state(unconfigured/configured/needs_reconfiguration)와 ownership_status(unverified/owned/ownership_lost)를 구분한다. suspect/missing 기존ID/선택/대표를 보존하되 부적격ID를 반환하고 자격을 중지한다. 명시적인 유효 설정 저장만 복구하며 빈선택을 성공으로 처리하지 않는다.

## 멱등·응답 유실

scope=actor+operation, hash=정규화된 대상path/허용query/body·기본값·version조건이다. 새동작은 새key, 전송 재시도는 같은key/payload다. 같은key 다른대상/내용은409 IDEMPOTENCY_CONFLICT. lease30초/generation fencing, 처리중409 REQUEST_IN_PROGRESS+Retry-After2. 장애rollback·lease만료 후 같은key 재시도 가능, completed업무/응답은 동시에commit한다. 입력/권한실패도 기존key/hash를 다른payload로 전용하지 않는다.

성공결과24시간,추가24시간 expired tombstone. 청소시점과무관 TTL이 우선,48시간후key 기억보장 없음. 해당시점은 GET과사용자 확인 후 새동작. DELETE성공replay는live row 없이동일actor204를 반환하며타인정보를 노출하지 않는다. 권한폐기/정지된session의replay는거절한다.

start재전송은원challenge ID/원응답이며새pending이 아니다.현재상태는GET. confirm pending재전송은원관찰결과,다음명시확인은새key. verified재확인은동일결과이며추가이전없음. 만료/취소는409 VERIFICATION_EXPIRED/VERIFICATION_CANCELLED. app종료는가능하면cancel,TTL후자동confirm/재시작없음.

register/patch/delete/settings는같은key재시도와관련GET,confirm/cancel은challenge GET+내등록GET으로복구한다. 과거성공version과현재소유/설정은다를수있으며GET이현재기준이다.

## 오류·재시도 안내

| HTTP/code | 처리 |
|---|---|
| 400 INVALID_REQUEST/EQUIPMENT_INCOMPLETE/REGISTRATION_LIMIT/CHARACTER_LIMIT | 입력·장착·상한 안내, 자동 재시도하지 않음 |
| 400 EMPTY_ACTIVITY_SELECTION/REPRESENTATIVE_REQUIRED | draft 수정, DB/로컬 성공 확정 금지 |
| 401 기존 ACCESS_*/SESSION_* | #2 인증 계약대로 처리, 일반 오류를 무조건 refresh하지 않음 |
| 403 ACCOUNT_DISABLED/OWNERSHIP_REQUIRED | 반복 저장 금지, 현재 상태 재조회 |
| 404 REGISTRATION_NOT_FOUND/CHARACTER_NOT_FOUND/VERIFICATION_NOT_FOUND | 비노출/현재 상태 확인, 다른 회원 자료 추정 금지 |
| 409 REVISION_CONFLICT/CURSOR_STALE | 최신자료 재조회·사용자 확인 후 명시 save |
| 409 REGISTRATION_EXISTS/IDENTITY_CONFLICT | 중복/충돌 안내, 자동 병합/이전 금지 |
| 409 REPRESENTATIVE_COOLDOWN | 설정 보존, GET next_change_at 안내 |
| 409 REQUEST_IN_PROGRESS | 같은key/payload로 Retry-After 이후 복구 |
| 409 IDEMPOTENCY_CONFLICT/IDEMPOTENCY_EXPIRED | key 전용/무조건 새key재제출 금지, 상태 확인 |
| 409 VERIFICATION_EXPIRED/VERIFICATION_CANCELLED | 진행 종료, 자동confirm 없음 |
| 429 RATE_LIMITED | Retry-After(실남은초), polling폭주 금지 |
| 503 UPSTREAM_UNAVAILABLE | 정상빈roster/proof성공으로 처리하지 않음, 기존자료 보존 |
| 200 pending+result_code | 장비불일치 또는증거보류이며 verified 아님 |

provider 제한80/min은DB공통·rolling window이며 proof조회는siblings와Armory 각호출을계수한다. 실제quota/다른consumer영향은후속실증이필요하다. start3/min/actor,confirm12/min/actor·5초/challenge,manualrefresh10초. transport동시2는process단위,summary진행중요청은DBlease합류,proof는캐시성공판정 없음.

현재game DB쓰기transaction은전역advisory lock으로짧게직렬화한다. 네트워크는밖에서진행한다. 초기단계의경쟁안전성을우선하며독립계정처리량최적화는실사용근거에따라후속검토한다. auth동작에는이lock을추가하지않는다.

## Flutter가 인계 뒤 테스트할 항목

빈회원조회/미인증등록상태, 본·부전환/삭제/중복·오류,전체페이지draft·세version변경/409,같은key/응답유실/DELETE replay,challenge현재상태/종료,활동·대표한번저장/재조회/늦은응답,로컬캐릭터/빌드보존을확인한다. 사용할계약SHA/구현SHA·재현흐름·안전한code/request_id를Issue로남긴다.

key/schema실증전에는완전한실인증/이전을Flutter에서완료할수없다. 공개mock API를만들어우회하지않는다. Backend자동검증·가능한DTO/UI연결은먼저완료하고실장비/소유권·누락관찰은공동준비후검증한다. issue종료·운영준비완료와구분한다.
