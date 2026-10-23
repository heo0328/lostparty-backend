> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [registration](../../../../features/rosters/registration/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #4 서버 계정 등록 관리 연동 준비·검증 계획

> 서버 공용 키 관련 내용은 당시 계획 이력이다. 현재는 [Issue #7 회원별 키](ISSUE_7_DEVELOPMENT.md)로 전환했고 공용 JWT는 제거했다. 새 설정은 현재 안내를 따른다.


작성: 2026-10-14. 상태: **실응답 점검 도구·대상검증 완료, 빈 label 요청 구현·대상검증 통과, 새 계약 Flutter 적용 후속**.

근거: [Issue #4](https://github.com/heo0328/lostparty-backend/issues/4). #3의 [실행 안내](ISSUE_3_DEVELOPMENT.md)와 [등록 후속 계획](ISSUE_3_REGISTRATION_FOLLOWUP_PLAN.md)을 재사용한다. 이후 등록 구간의 준비/실검증/재현 차이/인계는 #4에 기록하며 기존 #3 자료와 완료된 보완을 다시 수행하지 않는다.

## 기준·역할·범위

- 작업 브랜치: `feat/4-registration-integration`, 기준 `dev`의 `e807a6f002222cdff7beb07bfbe5cae65b97df43`.
- 기존 #3 구현·문서와 lease 헤더 보완은 dev에 fast-forward 통합·원격 push 완료. main은 e6c72e4 유지. 이전 feat/3-account-restoration은 통합 확인 후 로컬/원격 삭제했다.
- 계약 SHA: `254cb5de125ab1bcb2aa084e091eae976e9a078a`; 보완 구현 SHA: `db0f3ae438021b4f5fa3738b76fd926687871b0d`. dev 통합은 계약/코드의 추가 변경이 아니다.
- Flutter dev69d3aaa8df63b7db19b1660d0fe6b2a6295fa1bc, 로그인·등록/캐릭터GET 및 메인→부계정→계정도구 디자인 유지 보고가 요청 근거다. Flutter 로컬 소스/기기는 직접 수정·조작하지 않는다.
- Backend는 실행조건/실provider 대조·재현된 서버 차이의 최소 수정·대상검증/인계를 담당한다. Flutter는 등록 UI/Repository·세션/동일요청복구를 연결한다. 사용자가 로컬key·시험대상을 준비하고 명시적인 등록/변경/제거를 수행한다.

이번 범위는 preview→등록→두GET→label/main 변경→refresh→명시삭제→재조회와 로컬 자료 보존 인수다. 장비challenge/소유권이전·활동/대표 Flutter쓰기는 이후 그룹이며 기존 증거보류를 유지한다. 공개mock·개발DB fixture삽입·Firebase이관·DB초기화·운영배포는 제외한다. #3은자동종료하지않는다.

## 준비 완료 근거와 후속 실행

| 구간 | 지금 확보한 근거 | 다음 실행·완료 기준 |
|---|---|---|
| 코드/계약 | 기존API 구현·원본계약 유지, dev통합/push 확인, 이번 OpenAPI 전체 비교 통과 | Flutter는 기존 계약·보완 구현을 소비. 버전/환경이 실제로 바뀌었을 때 필요한 부분만 재확인 |
| 기존 자동검증 | 이전전체114개, 이후lease대상10개통과/106개미실행 | 이번준비만으로전체116개통과라표시하지않음. 새버그/코드차이가있을때대상검증 |
| 실행/DB | 앞선로컬적용/health200·DB0002·인증건수보존 기록. 이번Git통합으로서버/DB변경없음 | 사용자환경/실행image가변하면source/계약/migration을읽기전용확인. DB초기화/임의등록없음 |
| 서버key | 사용자 설정 후 local/runtime 존재 true·접두사 false·health200,값미출력 | 설정/반영 및 사용자 실 siblings 성공 확인. 키 만료/향후 장애는 별도 |
| provider | 사용자 실제 siblings 4개·필드 타입 일치·parser passed | 해당 관찰 응답에 수정 불필요. Flutter 등록관리 테스트로 진행; null/전체성/소유권 실증은 별도 |
| Flutter연결 | 두GET/빈등록·로그아웃·로컬보존보고. 등록쓰기UI미연결 | 디자인유지하며기존쓰기API연결·같은key/payload·GET복구·503예상제한처리 |
| 공동인수 | 실제등록관리성공은아직미확인 | 사용자명시등록/변경/삭제로서버GET결과확인·Flutter로컬보존별도보고 |
| 차이보완 | 이번준비중새결함/계약차이없음 | 실제safe code/request_id·기대/실제/동작으로원인확인,영향부위만수정·대상회귀·변경SHA인계 |

key가없어도FlutterUI/오류처리와Backend의재현가능한독립보완은계속진행한다. 실장비소유증명의전체인수를등록관리의선행조건으로두지않는다. 제공된lease수정은완료로취급하고다시개발하지않는다.

## API별 테스트 조건

기존 원본OpenAPI의 필수입력·strict DTO·nullable·버전/멱등 규칙을 소비한다.

- preview: POST /v1/game-accounts/preview, character_name/Bearer, key필수아님. 정상siblings가필요하며장비proof불필요.
- register: POST /v1/me/game-accounts, lookup_character_name/label/is_main와UUIDv4 key. freshsiblings,미인증등록이며권한character ID는null.
- GET: 등록목록과등록/characters. 빈목록은정상. 등록후preview/canonical·전체settings/page/버전을분리.
- PATCH: expected_version+명시변경필드와key. 본계정최대1/원자전환. 등록이있으면외부API없이가능.
- refresh: POST 등록/refresh의{}+key. provider/key필요,manual10초제한·실패자료보존.
- DELETE: query expected_version+key,204와동일actor replay. 정상canonical/로컬자료/다른계정설정삭제가아님.

실유실/409/429/503 관찰과 격리 테스트 결과를 구분한다. 과거 성공 응답과 현재상태는GET으로구분하고 새로운key로자동중복쓰기를하지않는다.

## 로컬 준비와 자료 취급

Backend `.env`의LOSTARK_API_TOKEN을사용자 로컬편집기로설정한다. 기존권한유지,값/.env본문/Bearer/Googleproof를Issue·앱에전달하지않는다. Flutter개인key자동업로드나임의credential API를만들지않는다.

source/DB가이미기준과같으면key적용에API환경재생성만필요하다.

```bash
docker compose up -d --no-deps --force-recreate --wait --wait-timeout 180 api
```

실제시험캐릭터는사용자가앱에서입력한다. Backend는실명/rawJSON을게시하지않고필드형태/타입/null·개수상한/기대·실제상태와코드만인계한다. actualkey/provider 준비가없으면503제한과실검증미실행을명시한다.

## 완료·상태 기록

완료는준비버전/실행환경·key상태(값제외)·실provider근거와제한,사용자등록/변경/갱신/제거의GET반영,Flutter로컬보존보고를확인하는것이다. Backend독립작업완료와key/사용자시험대기를구분한다. 발견된서버차이없으면불필요한신규구현없이실검증결과로인계한다.

기존API 계약변경이필요하면Flutter영향/전환을합의해OpenAPI와함께수정한다. 새구현commit/push/추가통합은그때의승인범위를따른다. 이번에는dev통합/push·브랜치정리·새작업준비만수행한다. Issue #4 준비문서는새브랜치의로컬변경이며아직게시하지않았다.

## 실행 진척

실제siblings응답을한번조회해타입/null/개수/parser결과만출력하는수동CLI를구현했다. [실행 안내](ISSUE_4_LIVE_VALIDATION.md)를참고한다. 공개REST/DTO/DB동작변경없이모의대상13개검증통과,키없는로컬실행종료2·외부요청없음과최신image원본계약불변을확인했다. 이번진행에서key존재만확인했고값은출력하지않았다. 키가발급되는로아OpenAPI JWT인지에대한사용자질문에답변했고설정준비를요청했다. 실제provider/등록인수는key/사용자대상준비후진행하며동일자료요청으로독립작업을미루지않았다.

2026-10-14 사용자 로컬 수동진단 결과: 실제 siblings root array, 4행 모두 객체, 문자열 4개(ServerName/CharacterName/CharacterClassName/ItemAvgLevel), CharacterLevel integer 4개, null item_level 0개, parser passed. 해당 요청에서 key/provider 호출 성공과 parser 호환성을 확인했다. DB 등록/HTTP 업무 API/장비소유권/roster 전체성 검증과 구분하며 기존 계약/구현 수정 없이 Flutter 등록쓰기 연결·공동 인수로 진행한다.

## Flutter 연결·사용자 인수 순서

실 provider 관찰 통과 후 아래 순서로 진행한다. 모든 요청에 앱 로그인 Bearer가 필요하며 Lost Ark 키는 Backend에만 둔다. 값이 필요한 입력은 사용자가 앱에서 제공한다.

| 순서 | 요청·필수 형식 | 성공·재조회 기준 |
|---|---|---|
| 1 검색 | POST /v1/game-accounts/preview, `{character_name}` | 200, `characters`와 만료시각 표시. 검색만으로 등록/소유 인증하지 않음 |
| 2 등록 | POST /v1/me/game-accounts, `{lookup_character_name,label,is_main}`, UUIDv4 Idempotency-Key | 201의 registration_id/version 저장. 등록목록 GET에 해당 등록이 나타남 |
| 3 캐릭터 | GET /v1/me/game-accounts/{registration_id}/characters | 200의 `characters.items`/settings 사용. 미인증 character_id=null과 활동 불가를 정상 처리 |
| 4 표시명 | PATCH 등록 경로, `{expected_version,label}`, 새 사용자 동작의 key | 200의 version 갱신, 목록 GET에서 표시명 확인 |
| 5 본계정 | PATCH 등록 경로, `{expected_version,is_main:true}`, 새 동작의 key | 전환 시 다른 등록의 version도 바뀔 수 있어 목록 전체 GET. 비교는 사용자가 여러 등록을 준비한 경우 수행 |
| 6 갱신 | POST 등록/refresh, body `{}`, 새 동작의 key | 200의 `registration.version` 반영, 목록/캐릭터 GET 확인. 미인증 added_count=0은 preview 갱신 실패를 뜻하지 않음 |
| 7 제거 | DELETE 등록 경로?expected_version=최신값, key, body 없음 | 204 body를 JSON 파싱하지 않음. 목록 GET에서 제거 확인. 로컬 캐릭터/빌드 보존은 Flutter가 확인 |

페이지가 남으면 next_cursor로 조회한다. refresh/PATCH 후 기존 cursor와 version을 재사용하지 않는다. 소유권·활동 설정은 이 등록관리 그룹에서 변경하지 않는다.

응답 유실 재시도는 기존 method/target/query/body/key를 그대로 재전송한다. 새 사용자 동작에만 새 key를 만든다. `409 REQUEST_IN_PROGRESS`는 Retry-After를 따라 같은 요청을 복구하고, `409 REVISION_CONFLICT`는 GET 후 사용자의 새 결정을 받는다. `409 IDEMPOTENCY_CONFLICT`는 key를 다른 payload에 재사용한 클라이언트 오류로 확인한다. 429는 Retry-After, 503은 실패 안내와 기존 자료 보존을 확인한다. 정상 인수에서 오류를 강제로 발생시키거나 DB/네트워크를 조작하지 않으며 미관찰 오류는 기존 격리 검증 근거로 구분한다.

Flutter 답변은 적용 commit/계약 SHA, 연결한 흐름, 자동검증 결과, 사용자 실제 시험 여부/각 단계 결과, 로컬 자료 보존, 미실행 항목을 담는다. 서버 차이가 있으면 식별정보 없이 동작·기대/실제·HTTP status/error.code/request_id를 남긴다. 현재 Backend 선행 준비는 완료이며 Flutter 연결 후의 실제 등록관리 인수와 재현된 차이 보완이 남았다.

## 2026-10-14 최종 요청: 빈 이름 자동 표시 계약

[최종 요청](https://github.com/heo0328/lostparty-backend/issues/4#issuecomment-6163006876)을 사용자 작업 지시로 적용했다. custom_label/보존 migration 제안은 사용하지 않는다. 기존 label 문자열 필드에 빈값을 저장한다. 이 요청에서 DB/기존 자료를 직접 삭제하지 않았으며 데이터 초기화는 구현에 필요하지 않다.

- POST: label 생략 또는 `""`이면 저장/응답 `""`. 입력한 이름은 기존처럼 앞뒤 공백을 제거하고 최대40자까지 저장한다. 공백만 있으면 빈값이다. null/숫자/boolean/40자 초과는400.
- PATCH: label 생략은 이름 유지, `""`/공백만 있는 값은 자동으로 전환, 문자열은 사용자 이름으로 변경. null은400. expected_version·최소1개 변경필드·동일 key/payload 규칙 유지.
- 응답: 실제 저장 label을 반환한다. 빈값을 메인/부계정 이름으로 바꾸지 않는다. 새 필드/endpoint/DB migration 없음.
- 표시: Flutter가 label이 비어 있으면 is_main=true에 「메인 계정」, 나머지에 「부계정 N」을 계산한다. GET 전체 목록의 `(created_at ASC, registration_id ASC)` 순서에서 본계정을 제외한 모든 부계정을 센다. 사용자지정이름 계정도 번호에 포함한다. 페이지별 번호를 다시 시작하거나 label로 정렬하지 않는다. 순서 예: 빈값/사용자이름/빈값의 부계정은 「부계정 1」/사용자이름/「부계정 3」.
- 본계정 전환: 서버는 label을 교환/재작성하지 않는다. 전체 목록 재조회로 is_main/version과 표시 번호를 다시 계산한다. 본계정이 없어도 전체 부계정 순서로 번호를 센다.

원본 OpenAPI의 RegisterIn/PatchIn/RegistrationOut label과 x-game-account-policy.registration_label만 변경했다. 경로/인증계약/기타정책 유지. 이전 계약254cb5d는 이 변경의 기반이며 빈 이름 wire는 새 로컬 계약을 적용해야 한다. 아직 commit/push가 없어 새 계약/실제 구현 commit SHA는 미발급이다.

최신 API 이미지 기반 격리 PostgreSQL 대상16개 통과/27개 미실행(7.89초,기존 경고1개). 최초 이전 API 이미지에서는 새 동작5개가400으로 실패했고 최신 이미지 빌드 후 통과했다. 신규10개는 POST생략/빈값/공백/사용자이름의 DB 저장·GET·replay, PATCH명시clear/생략유지/본계정전환·stale version, 잘못된값 rollback, 지정이름 포함 페이지 안정순서를 검증한다. 기존6개는 strict/멱등/본계정/DELETE replay다. 실제 Flutter 빈이름 인수는 후속이다.

## 2026-10-14 게시 상태

사용자 승인으로 `feat/4-registration-integration`에 구현/새 label 계약/진단도구/검증/문서를 커밋·push했다. 실제 구현·계약 SHA: `d3cb697bb6ebb988b63bd99c588bc1b64a93650d`. 앞선 미커밋/새SHA미발급 설명은 게시 전 이력이며 현재 소비 기준은 이 SHA다. dev/main 추가병합·실제 Flutter 인수는 후속이다. 기존 대상16개·진단13개/실 siblings 4개 근거를 유지하며 이번 게시에서 테스트를 반복하지 않았다.

2026-10-14 사용자 승인 통합: #4 구현/계약·문서와 #2 후속 문서가 dev a6d25aa에 포함돼 push 완료. 완료 feat/4-registration-integration은 로컬/원격 삭제했다. 위 작업브랜치 게시/미통합 설명은 당시 이력이다. 실제 계약/구현 SHA d3cb697은 유지되며 Flutter 실인수·장비/활동 후속은 별도다. 현재 dev에서 사용자 지시로 대기한다.

## 2026-10-14 Flutter 결과 회신 확인

[기존등록결과6164864407](https://github.com/heo0328/lostparty-backend/issues/4#issuecomment-6164864407): 등록/삭제·동일회원 재로그인 캐릭터표시·갱신 실제보고 확인. [새계약구현6166099894](https://github.com/heo0328/lostparty-backend/issues/4#issuecomment-6166099894): d3cb697 소비,전체1193테스트·분석0·debug APK33.4초 성공 보고(Backend 재실행 아님). [사용자인수6166283832](https://github.com/heo0328/lostparty-backend/issues/4#issuecomment-6166283832): 미입력등록/지정이름/clear/본부전환·지정이름유지/지정이름포함번호 모두정상.

새 Backend 수정/추가테스트 요청없음. 같은자료·성공테스트 반복요청없음. Flutter feature/account-backend-registration 미커밋·미push/dev통합전·새적용SHA없음이며Git정리후인계예정. 삭제후로컬자료보존은기존미확인으로남고재설치/장비·소유권/활동·대표/전투력전체수집은별도후속. 기존Flutter인수대기설명은이최신기록으로대체하며#4OPEN유지.

## 2026-10-14 Flutter Git 인계 추가 확인·대기

[추가회신6166359575](https://github.com/heo0328/lostparty-backend/issues/4#issuecomment-6166359575)에서 Flutter 구현 `5fe636eee4725adf8a063e8a119be9742ecbcc82`, dev통합 `266a7e20f4f397981d61753084f88df881c0e377`,push완료·소비계약d3cb697을 확인했다(Flutter보고). 앞선 미커밋/Git대기는 해소됐다. 빈label연결·1193자동검증과사용자신규4흐름인수는 유지하고 반복검증없음. 삭제후로컬보존 등 다른미확인은별도후속이며새Backend요청없음. 전투력협업은다음설계후보일뿐미합의API를추가하지않는다. Backend결과문서를dev에게시후다음사용자지시를대기한다.
