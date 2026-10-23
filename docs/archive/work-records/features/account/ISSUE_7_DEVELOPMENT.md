> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [api-keys](../../../../features/login-account/api-keys/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 회원별 Lost Ark 키 실행·인계

2026-10-15. [Issue #7](https://github.com/heo0328/lostparty-backend/issues/7)·[수용된 계약](ISSUE_7_LOSTARK_KEY_CONTRACT_DRAFT.md) 기준. 회원 공통 설정과 관련된 기존 `feat/member-settings`에서 이어 구현했다. 회원별 키와 모든 외부 REST 호출 전환을 한 구간으로 인계한다. 기능/OpenAPI9e1a255·dev 통합772b90e·결과 기록72f6301 게시 완료. 아래 단계별 기록은 당시 상태이며 현재 완료/종료 상태는 마지막 절을 따른다.

## 공개 계약

`GET /v1/me/lostark-api-key`는 앱 Bearer로 `{configured:boolean,version:integer>=1,updated_at:UTC|null}`만 반환한다. 초기 false/1/null, 행 생성·복호화·외부 호출 없음. metadata GET은 원문을 반환하지 않는다. 추가합의로 본인 기기복원은 별도 POST restore에서 제공한다.

`PUT`은 앱 Bearer·UUIDv4 Idempotency-Key·엄격 `{token:string,expected_version:integer>=1}`. compact JWT 3구간 ASCII base64url 문자·최대16KiB, 공백/개행/Bearer 접두사 불가. 형식 검사 후 암호화 저장만 하며 provider 유효성/서명/claims/exp를 검증하지 않는다. 모든 새 PUT은 같은 token이어도 version+1, 첫 PUT은2.

`DELETE`는 앱 Bearer·UUIDv4 key·query expected_version, body 없음. 성공200은 동일 metadata. 등록 상태 삭제는 version+1·현재 비밀 제거, 미등록 no-op은 버전 유지. stale version은 no-op에도409. 로그아웃/같은회원 새세션은 보존. 현재 키 삭제를 등록/캐릭터 데이터 삭제와 혼동하지 않는다.

기존 멱등24시간 원래 응답 replay·24시간 tombstone·30초 lease/generation·409 REQUEST_IN_PROGRESS/Retry-After2 재사용. 다른 입력 같은key409 IDEMPOTENCY_CONFLICT, 보관기한후 IDEMPOTENCY_EXPIRED. 과거 PUT replay는 키를 다시 저장하지 않는다. 현재값은GET. PUT용 멱등에는 원문을 넣지 않고 전용 HMAC fingerprint만 사용한다. 새key의 stale version은409 REVISION_CONFLICT→GET→사용자 명시 결정/newkey.

외부조회 필요 명령의 미등록은409 LOSTARK_KEY_NOT_CONFIGURED, provider401/403은409 LOSTARK_KEY_REJECTED, 진행중 키 교체/삭제는409 LOSTARK_KEY_CHANGED, 암호화 설정/복호화 실패는503 LOSTARK_KEY_UNAVAILABLE. 앱 인증401과 별개이며 키 거절로 로그아웃하지 않는다. 저장자료 GET은 키 없이 유지한다. 전투력 batch의 외부 거절/429는 failed item reason과 미시작 deferred reason으로 표현하고 정상 과거 숫자/시각은 보존한다. 키 변경은 batch409·옛 결과 미반영. 서버 quota는 token별80/min·부족시 기존 RATE_LIMITED/deferred, transport 동시2/process 유지. local 직접 호출은 서버 budget에 포함되지 않아 외부429 가능.

## 저장·캐시

AES-256-GCM·새nonce12byte·회원/version/key_id AAD. 독립32byte 암호화/HMAC 파일. SQL 예외 parameter 숨김·원문없는 DTO repr/오류/멱등결과, 원본/비밀 로그 없음. `0005_lostark_credentials`: 최소 credential 1테이블, 회원/version별 preview와 fetchlease 2테이블, 기존 powercache에 nullable credential_version 추가. 기존 공용 cache/lease는 개인 조회에 재사용하지 않고 보존한다. 기존 power 값/fetched_at은 유지하되 새 키 버전에서 fresh hit로 재사용하지 않는다. 전용 캐시는 기존 cleanup90분에 포함된다.

모든 preview/siblings·등록/refresh·proof start/confirm·profile 호출에 회원 snapshot을 주입한다. 네트워크 동안 DB lock 없음. 호출전·캐시완료/업무반영 전 현재세션/credential version 재검증. 진행 중 HTTP 취소 또는 키 교체 직전 transport 시작까지 완전히 막는 보장은 없지만 옛 결과는 최종commit에서 차단한다. 삭제 뒤 새 명령은 옛 키를 읽지 않는다. 장비 proof 보류 정책은 유지한다.

## 로컬 준비와 적용

서버 공용 LOSTARK_API_TOKEN은 `.env`와 Compose에서 제거했다. 값·환경본문을 게시하지 않았다. 실행환경에도 공용 JWT 없음, 기존 키 자동 회원 등록 없음. 발급 client/키 폐기는 하지 않았다. diagnostic CLI는 환경키 자동 사용 없이 실제 terminal에서 키·캐릭터명을 각각 hidden prompt로 직접 받아 1회 관찰한다.

새 환경에서만 dedicated 파일을 생성한다. 기존 파일이 하나라도 있으면 overwrite하지 않고 중단한다. 현재 개발 환경은 생성 완료이므로 다음 명령을 반복 실행하지 않는다.

```bash
docker compose build api
docker compose run --rm --no-deps -T -e AUTH_SECRET_DIR=/key-setup \
  -v "$PWD/.secrets:/key-setup:rw" api python -m app.lostark_keys.setup_keys
docker compose run --rm --no-deps -T api alembic upgrade head
docker compose up -d --no-deps --force-recreate --wait --wait-timeout 180 api
python3 scripts/check_openapi.py
```

API는 원래 `/run/secrets:ro`로 읽는다. 생성 시 API 사용자 권한으로 별도 일회성 `/key-setup:rw` 마운트를 사용한다. 기존 디렉터리·인증/서명 키를 바꾸지 않는다. encryption/HMAC 파일은 DB와 별도 복구 대상으로 관리하며 재시작시 새 생성 금지. 암호화 rotation/구키 재암호화, HMAC rotation은 별도 계획 대상이다. 키 파일 값은 채팅/Issue로 요청하지 않는다.

## 검증 결과와 남은 확인

격리 PostgreSQL 직접 영향 대상 **180 passed, 기존경고1, 44.55초**. 새 키 API·ciphertext/nonce/회원AAD·명시 등록/교체/삭제·버전/멱등/fencing·두회원 다른키·같은token quota 공유/다른token 분리·공용 cache 존재해도 미등록 차단·전체 REST token주입·교체/삭제중 preview/power 결과 차단·과거power 보존·키거절 앱세션 유지·회원설정/계정/장비proof/전투력 회귀·provider/diagnostic·OpenAPI/metadata/migration 확인. Google/provider는 mock이고 실제 개인 키 사용을 증명한 결과가 아니다. 초기 old API 이미지 기반 collection 실패와 중간 flush/테스트 fixture 보완 후 최신 이미지로 통과했다.

최종 JWT 형식 OpenAPI 명시/GET·DELETE body 거절 후 새 키/스키마 대상27개 추가 통과(10.27초, 기존경고1). 기존180개 결과와 구분하며 전체207개 단일 실행으로 표현하지 않는다.

로컬 migration0005·기존20테이블 건수 보존·새 credential0 확인. API healthy/계약전체 일치PASS. 공용 JWT 설정/실행환경 없음, encryption/HMAC 각각32byte 읽기 준비 true. 최초생성의 root DAC/read-only mount 오류는 API 사용자·별도쓰기 mount로 해결했다. 테스트DB 중지. DB 초기화/개발 fixture/캐릭터 삭제·자료이관 없음.

다음은 Flutter가 게시 SHA/OpenAPI를 소비하고 상태/명시등록·교체·삭제/키오류·재시도·회원 격리를 연결하는 일이다. 이후 사용자가 자신의 키를 앱에서 명시 등록해 실제 서버 조회를 확인한다. 로컬직접조회와 서버등록 UX는 Flutter/사용자 협의로 유지한다. 실제 provider/사용자 인수·전체빌드자동갱신은 미확인/미구현이며 동일 등록/이름/전투력 테스트를 일괄 재요청하지 않는다.

## 추가 합의 — 본인 키 복원·호출 제한 시간

[수용 회신](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6172746952)·[정확한 추가 계약](ISSUE_7_RETRY_RESTORE_CONTRACT_DRAFT.md)을 구현했다. 기존 metadataGET/PUT/DELETE와캐릭터GET DTO는유지한다.

POST /v1/me/lostark-api-key/restore: 앱Bearer·엄격 `{expected_version:integer>=1}`, 200 `{token:string,version:integer>=1}`. 같은locked회원행에서복호화·no-store·readonly·외부호출/버전증가없음. Idempotency-Key불필요/RequestResult에원문저장없음. absent409 NOT_CONFIGURED,stale409 CHANGED, unreadable503 UNAVAILABLE,앱401/403기존. 원문은Flutter보안저장에만사용하고등록화면/로그에표시하지않는다. 전기기실시간동기화보장없음,회원/서버/세션/버전/generation late응답차단은Flutter담당이다.

외부429 또는성공200Remaining0은token별limiter에절대deadline max기록. UNIX초Reset이관찰시점기준미래300초이내면사용,누락/invalid/past/과도미래는관찰+60초. 같은token재등록/다른회원도대기공유·새token독립. 로컬차단만으로deadline연장없음. 성공200은성공유지/이후새호출보류,정상cache/저장GET유지. 늦은worker의control observer는독립limiter만기록·업무자료는기한/fencing그대로다.

GameErrorDetail은optionalnullable retry_after_seconds/retry_at,제한오류엔필수쌍,단건Retry-After와초값동일. PowerResult는requirednullable두필드추가·그외reason은null쌍·200batch전체Retry-After없음. seconds는max(1,ceil(deadline-DBnow)),retry_at은UTC절대시각. 서버80/min과upstream대기가겹치면deadline max/upstream활성시codeUPSTREAM_RATE_LIMITED. 실패cache10초로만료된upstream대기를숨기지않음.

**현재 Flutter strict ServerPowerResult와 새 required필드 응답은 비호환**이다. 새게시OpenAPI소비/DTO·오류·복원/대기연결후사용자확인해야하며Backend게시만으로현재앱정상인수라고보고하지않는다. 새입력계약으로복원된키를로그/Issue에보내지않는다. 기존공용키제거확인을반복요청하지않고추가복원/대기구간만인계한다.


추가구간 검증: 대상151개 통과47.44초(기존경고1),동일조회대기자·local/upstreammax후24개 통과7.04초,제한만료시cache우회최종국소4개 통과3.88초. 각각별도실행이며전체179개단일실행으로확대하지않는다. 정상/누락/invalid/past/ms모양/과도미래Reset·Remaining0성공·token격리/max/기간만료·단건503/429헤더JSON일치·부분결과시간/replay·late관찰옛token만반영/업무값미쓰기·restore본인/세션/형식/키교체삭제/무결성·no-store/원문미로그/멱등미저장·직접영향계정/전투력/member설정/스키마migration검증. 초기mock예외/테스트간limiter상태잔존은수정후통과했다. provider와Google증거는mock이며실한도소진/실키복원은미실행.

로컬DB0006_provider_limits·새limiter1테이블만추가/기존23테이블건수보존·새행0확인. 최신APIhealth정상/원본OpenAPI전체일치PASS·test-db중지. 기존credential/암호화키/공용JWT제거상태보존,자료초기화/fixture·키파일변경/실provider호출없음. 게시구간은검증후작업브랜치에1회commit/push/원격확인하고Issue7의실제새SHA로인계한다. Flutter연결/실사용후속·dev/main미병합.


## Flutter 연결 결과 확인

[회신](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6173350024)에서 Backend9e1a255 소비·회원 키 등록/교체/삭제·GET/restore/보안저장·회원/세션/버전 late응답·서버/기기 부분성공·호출대기/명시retry/strictDTO 연결 완료를 확인했다. 직접조회는 복원한 기기 키 사용, 자동 업로드/공용 배정 없음 보고다.

Flutter 전체1246개PASS 후 국소보완12개PASS·최종분석0·debugAPK 성공 보고이며 표적58개도 별도 결과다. 실제provider/개인 키·기기 설치/조작·재설치/별도기기는 미실행이다. feature/member-lostark-key 변경은 미커밋·미push·dev 미반영으로 적용 SHA 미정이다. Backend 추가 수정/재시험 요청 없음. 사용자 새 빌드 인수 결과와 Flutter Git 게시 회신을 기다리며 기존 성공 시험을 반복 요청하지 않는다.


## 현재 구간 사용자 정상 동작 확인

[최종 사용자 결과](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6173934017)에서 키 등록/삭제에 이어 캐릭터 검색 등 현재 구현 구간이 정상 동작한다고 보고했다. Flutter의 코드 연결 재확인상 로그인 회원의 직접 검색/상세는 restore로 기기에 저장한 회원 키로 Lost Ark를 직접 호출하고, 서버 원정대/전투력 갱신은 앱 Bearer→Backend 회원 키 선택 경로다. 이는 Flutter 코드 확인/사용자 일반 동작 보고이며 실제 패킷/원문 키 관찰이나 모든 API 경로 실인수로 확대하지 않는다.

앞선 [부분 확인/문구 정리](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6173742113)의 관련46개PASS/분석0/debugAPK 성공은 Flutter 국소 검증이다. 기존1246/국소12와 별도 결과로 유지한다. 현재 구간 정상 보고 후 사용자에게 키 저장 위치/HTTP 경로를 구분하는 추가 시험을 요구하지 않는다. 재설치/별도기기·실provider429 한도 소진은 별도 미확인이며 앱 전체 문구 점검은 Flutter 후속이다.

남은 인계는 Flutter feature/member-lostark-key의 문서 최종화·Git 게시/통합과 적용 SHA 회신이다. 아직 미커밋·미push·dev 미반영. Backend 추가 변경/재시험 요청 없음. 이번 확인으로 Issue를 종료하거나 dev에 병합하지 않았다.


## Flutter Git 게시·dev 통합 확인

[최종 Git 인계](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6174013475): 구현 `8644c81fbd16b3a035531c71498a30c0f4869ce5`, feature/member-lostark-key 원격 게시/유지, dev 통합 `cc6a0b0ffdd11bb87d186f56e79238f59f99f76c` push, 소비 Backend9e1a255. Backend에서 GitHub 원격 dev가 같은 SHA인 점과 compare상 구현 포함/ahead1·behind0·changed_files0을 직접 확인했다. Flutter 로컬 소스는 읽거나 수정하지 않았다.

이 확인으로 앞선 Flutter 미커밋/게시 대기 상태를 대체한다. 기존 자동검증·사용자 현재 구간 정상 보고를 재사용하며 병합 때문에 재시험하지 않았다. Backend 추가 수정 요청 없음. 재설치/별도기기·실provider한도/헤더·운영TLS 및 Flutter 전체앱문구/전체빌드자동갱신 설계는 별도 후속이다. Backend 결과문서는 미커밋, Backend dev/main 미병합·Issue7OPEN이다.

## Backend dev 통합 지시

사용자가 결과 문서 최신화 후 dev 병합·push를 지시했다. 기존 #7 사용자 결과/Flutter 게시 확인과 #6 최종 인계·CLOSED 상태를 반영하고, dev4eb23f5에서 작업 브랜치까지 fast-forward 가능함을 확인했다. 코드/API 계약 변경 없이 문서 diff를 확인하며 기존 자동검증/로컬0006 근거를 유지한다. 서버/DB/기능 테스트 반복 없음. 실제 dev 게시·브랜치 정리 결과는 DEV_LOG와 같은 Issue 결과 댓글에 기록한다.

통합 결과: dev4eb23f5→772b90e fast-forward·origin/dev push 확인. app/OpenAPI/alembic/tests는 검증 게시9e1a255와 동일함을 비교했다. 포함·clean·다른worktree없음을 확인한뒤 feat/member-settings 로컬/원격을 정리했다. 현재dev이며 main/Issue7OPEN은유지한다. 통합완료기록은dev에추가게시한다.

## 현재 완료·종료 인계 상태

2026-10-15 사용자 보고: #7 작업이 완료되어 네이티브에 이슈 종료 처리를 지시했다. GitHub 조회 시 아직 OPEN이며 실제 종료 처리는 네이티브 담당이다. [최신 Backend 통합 회신](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6174087672) 기준 양측 dev 게시·현재 구간 사용자 정상 보고 확인 완료, 추가 Backend 수정/반복 시험 요청 없음. 이전 단계의 게시/인수 대기 기록은 이후 완료 기록으로 대체한다. 재설치/별도기기·실provider 제한/헤더·운영TLS와 전체빌드/역할저장 설계는 별도 후속으로 보존한다. Backend는 문서 최신화·dev 반영/push 후 새 합의 요청 또는 실제 결함 보고를 기다린다.

2026-10-15 11:29 KST: 사용자 확인/종료 지시로 본문·최신 댓글의 완료 근거 및 추가 수정 요청 없음을 재확인했다. Backend에서 완료 사유 댓글과 함께 종료해 CLOSED/COMPLETED를 확인했다. [종료 댓글](https://github.com/heo0328/lostparty-backend/issues/7#issuecomment-6183029637). 앞선 네이티브 종료 대기 상태를 대체하며 별도 후속 미확인은 유지한다.
