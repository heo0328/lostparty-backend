# 전투력 갱신 API 실행·인계

기준은 [Issue #5](https://github.com/heo0328/lostparty-backend/issues/5)와 [Flutter 동의](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6166739099)다. 브랜치 `feat/account-management`, 미커밋·미push이며 새 구현/계약 SHA는 아직 없다. 계약 원본은 [OpenAPI](../openapi/openapi.yaml). Flutter는 원격 게시 후 새 계약 SHA를 소비한다.

## 요청

`POST /v1/me/game-accounts/{registration_id}/combat-power/refresh`, 앱 로그인 Bearer와 UUIDv4 Idempotency-Key 필요.

```json
{"characters":[{"server_name":"sample-server","character_name":"sample"}]}
```

characters 필수·1~20개, 각 이름1~64자/앞뒤공백제거·추가필드거절. 중복은 순서를 유지해 제거하되 원본 정규화 body가 멱등 해시 기준이다. 전체 현재 roster 범위를 먼저 확인하며 하나라도 범위 밖이면400 CHARACTER_OUT_OF_SCOPE, 외부호출/값변경 없음. 타인/삭제등록404 REGISTRATION_NOT_FOUND, guest401. 본인 소유상실 등록의 preview는 표시 조회만 가능하다.

기본 대상은 [공통상수](GAME_DEFAULTS.md) `DEFAULT_MIN_ITEM_LEVEL=Decimal("1700")`. 미만/null은skipped, 전체 roster GET/ID·권한/활동을 바꾸지 않는다. 실제 profiles 경로는 [공식 사용 안내](https://developer-lostark.game.onstove.com/usage-guide)에 따른 `/armories/characters/{characterName}/profiles`. 서버에서 조회·식별 검증하고 raw profile은 저장하지 않는다.

## 응답·캐시

HTTP200 body=`{items:[...]}`. items는 중복제거한 입력 순서다.

| 필드 | 의미 |
|---|---|
| server_name / character_name | 대상 식별키 |
| combat_power: string 또는null | 최근 정상 수치, 쉼표 제거·유한값/음수거절. 실제0 허용 |
| power_fetched_at: UTC 시각 또는null | 정상 수치를 확인·적용한 시각. 실패/미제공으로 바꾸지 않음 |
| power_checked_at: UTC 시각 또는null | 마지막 적용한 조회 시도 시각. 정상/미제공/실패 구별 |
| power_status: unknown/available/unavailable/failed | 저장된 최근 관찰 상태. unknown은아직관찰없음 |
| power_reason: string 또는null | 최근 관찰의 고정 사유. 정상null, 미제공COMBAT_POWER_UNAVAILABLE, 실패UPSTREAM_* |
| power_stale: boolean | 정상값없음/30분경과/summary보다오래됨/마지막실패·미제공이면true |
| status: updated/cached/unavailable/failed/skipped/deferred | 이번 명령의 처리 결과 |
| reason: string 또는null | 이번 결과의 고정 사유 |

위 power_checked_at/power_status/power_reason은 기존 CharacterOut에도 필수 필드로 추가한다(null 허용인 필드는명시null). 기존 combat_power/power_fetched_at/power_stale 유지. Strict DTO 소비 시 새 snapshot을 반영해야 한다. representative_summary에는 같은 캐시 수치만 overlay하고 Summary DTO를 추가 변경하지 않는다.

회원+서버+캐릭터별캐시 한 테이블 `character_power_cache`, additive migration0003. 캐시값은 소유권/활동 proof가 아니다. 정상·미제공은30분 재사용,실패는10초 연속재시도억제. summary가더새로우면재조회. 캐시 hit는 외부호출/quota소모없음. 실패·미제공시이전정상값/성공시각보존·stale=true; 최초값없음null. 최신canonical정상값도fallback으로보존. 일반GET은읽기만,summary갱신이power성공시각을위장하지않는다. 관찰90일후 정리하고값없는inactiveunknown행은기존cleanup에서정리한다.

## 시간·동시성·복구

- 공식client100/min과구분하여 기존DB공유provider80/min/transport동시2·connect3/read5초·stream기한8초·1MiB를재사용한다. 기존HTTP재시도/redirect없음 유지.
- 요청진입시20초처리예산,초기등록/캐시확인·quota·진행중profile대기도예산에포함. 네트워크결과대기는진입19초까지,최종DBcommit에1초여유. 이 서비스DBstatement/lock은500ms 제한. OS스케줄링/DB연결·응답전송까지정확히20.000초를강제하는proxyharddeadline은아니다. Flutter는동의한새요청전용30초receiveTimeout사용.
- 시간안에아직처리하지않았거나대기결과를수용하지못한대상은deferred/TIME_BUDGET_EXCEEDED. 이미실행된blockingHTTP는transport정리후종료할수있지만worker에DB쓰기없고그결과는폐기해뒤늦은적용없음. 별도jobqueue/polling없음.
- 같은회원/캐릭터진행중조회는cachelease로중복외부호출억제,다른명령에는deferred/FETCH_IN_PROGRESS. quota부족은deferred/RATE_LIMITED로즉시응답하고할당량리셋까지sleep하지않는다. skipped는ITEM_LEVEL_BELOW_DEFAULT 또는ITEM_LEVEL_UNAVAILABLE.
- 동일key/body완료replay는동일결과. deferred도원래결과그대로이며사용자다음명시묶음에는새key. 응답유실/REQUEST_IN_PROGRESS는기존key/body유지. 새key다른payload재사용409 IDEMPOTENCY_CONFLICT,24시간이후409 IDEMPOTENCY_EXPIRED.
- 마지막반영전에active회원/session·등록삭제/version·roster/소유차수재검사. 변경409 REVISION_CONFLICT·세션폐기401 SESSION_REVOKED·삭제404. cachelease generation/만료충돌409 REQUEST_IN_PROGRESS+Retry-After2,그명령의값반영rollback. 외부실패는items부분실패,DB장애503 SERVICE_UNAVAILABLE.
- profile호출동안DBlock없음. 캐시반영/멱등완료결과는같은transaction. power만으로등록/roster/소유권/settings revision은증가하지않는다.

## 로컬 실행·검증과 남은 입력

기존 DB/비밀설정 유지. 새이미지빌드→`docker compose run --rm --no-deps -T api alembic upgrade head`→API만재생성→`python3 scripts/check_openapi.py`. 기존테이블의집계건수보존을확인하며개발fixture/초기화없음.

실제 provider profile 응답과 Flutter 전투력 표시/로컬 역할snapshot우선·회원/로그아웃격리는미인수다. 기존이름/등록성공시험을반복요청하지않으며장비인증·활동/대표·운영기능으로범위를확대하지않는다.

현재검증: 대상42개통과(9.29초/기존경고1개),이후null레벨reason·retention·상수메타데이터후속3개통과(3.37초/경고1개). 이전22개/중간33개와별도실행이며전체기존테스트반복없음. migration/model일치·기존authschema보존·guest/타인/미인증/canonical·20명·부분실패·중복조회/fencing·등록version/삭제/session폐기·기한뒤늦은값미반영·quota·summary값시각보존 검증. 로컬OpenAPI전체일치PASS/health200/DB0003·18기존테이블집계보존·새cache0/runtime키존재true. 실제profile미호출/Flutter미인수,미commit/push.

게시 전 [Flutter 인계 확인](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6167001322): 기존 Flutter Strict DTO는 추가 CharacterOut 필드를 거절한다. 로컬 Backend 적용을 기존 앱 호환/연결 완료로 표시하지 않는다. 새 게시 계약을 소비한 Flutter DTO/화면 구현 후 연동한다. 추가 서버 수정/테스트 요청은 없으며 기존 자동 검증 근거를 유지한다.

## 2026-10-14 게시 완료

사용자 승인으로 `feat/account-management`에 commit/push 완료. 실제 구현·원본OpenAPI SHA: `39188d5dca2d394f4e8b3fcbfe332274812285bf`. 앞선 미커밋/미push·새SHA없음 설명은 게시 전 이력이며 현재 Flutter 소비 기준은 이 SHA다. dev/main 병합·배포·Issue종료는 하지 않았다. 기존42개/후속3개·로컬0003/API 적용 근거 유지,실profile/Flutter신규인수후속. 게시기록후속은파일끝공백정리와문서상태만 바꾸며새API동작/계약변경없음.

## 2026-10-14 Flutter 연결·사용자 확인

[연결회신](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6167414628)의39188d5원본소비·StrictDTO/POST/GET·전용30초·1700/20명·로컬카드역할snapshot우선/회원격리연결과전체1204테스트·국소후속70/분석0/debug11.4초보고를확인했다. 전체1206통과로확대하지않는다. [사용자확인](https://github.com/heo0328/lostparty-backend/issues/5#issuecomment-6167529348)에서서버전투력확인/표시·로컬카드역할값유지·로그아웃/재로그인표시캐시3흐름모두정상. 원본profileschema/모든장애상한실인수로확대하지않는다.

Flutter feature/character-combat-power 미커밋·미push/dev미반영·새적용SHA없음. 새Backend수정/테스트요청없음·성공시험반복없음. 나이스단앱시작자동갱신Backend연결은별도후속이며이번수동API확인에포함하지않는다.

## 2026-10-14 dev 통합·정리

사용자 승인으로 #5작업/문서·인계규칙을 dev87751537bd63f13605fb8f0eacbca749c0898285에fast-forward 통합·push했다. 완료 feat/account-management는로컬/원격삭제. 위작업브랜치/미통합 설명은당시이력이며실제구현/계약39188d5는유지된다. Flutter연결·사용자3흐름은확인됐고Git게시SHA미회신/별도미확인범위는후속이다. 이번통합에코드/계약추가변경없음·반복검증없음.
