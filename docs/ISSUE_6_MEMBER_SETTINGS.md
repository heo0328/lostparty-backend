# 회원별 나이스단 자동 갱신 허용 설정

기준: [Issue #6](https://github.com/heo0328/lostparty-backend/issues/6), [Backend 계약 정리](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6168785700). 사용자 진행 지시로 확정된 회원 설정 저장·복원만 구현한다. 브랜치 `feat/member-settings`, 기준 dev4eb23f5. 게시 시 실제 구현/원본계약 SHA를 같은 이슈에 인계한다.

## 계약

| 요청 | 입력·성공 응답 |
|---|---|
| GET /v1/me/settings | 앱 로그인 Bearer. 200 `{nice_group_auto_refresh_enabled:boolean,version:integer>=1}` |
| PUT /v1/me/settings | Bearer + UUIDv4 Idempotency-Key. body `{nice_group_auto_refresh_enabled:boolean,expected_version:integer>=1}`. 200은GET과동일형태 |

미설정회원은false/version1. GET은설정행생성/설정변경·Lost Ark호출없음. 원정대별이아닌Backend내부회원별1행이다. 로그아웃/새session은설정을지우지않는다. 새기기/재설치후같은회원로그인→GET성공값복원이며로컬캐시없음/GET실패를false자동PUT로처리하지않는다.

PUT 두필드필수·null/숫자boolean/문자열boolean·boolean/string/0이하version·추가actor/user_id·알수없는query거절(400 INVALID_REQUEST). 응답필드는두개만이며모두필수/null불가. 기존 /v1/me와다른모든DTO·path정책은변경없어기존StrictDTO를일괄변경할필요없음.

## 동시수정·재시도·오류

- 조회version을expected_version으로사용한다. 실제값변경시version+1,동일값명시저장은version유지. 미설정상태첫true저장은version2/첫false저장은version1.
- 같은값이라도stale expected_version은409 REVISION_CONFLICT. Flutter는GET재조회후사용자새결정에새key를부여한다. 다른기기의값을자동덮어쓰지않는다.
- 동일회원/operation/key·body는기존멱등규칙을사용한다. 성공응답24시간replay,이후24시간tombstone·30초lease/generationfencing. 진행중409 REQUEST_IN_PROGRESS+Retry-After2·다른body409 IDEMPOTENCY_CONFLICT·24시간이후409 IDEMPOTENCY_EXPIRED.
- 응답유실은원래key/body로재전송한다. 이후다른수정이있어도replay는이전결과이며현재상태는GET으로확인한다. replay가설정을다시적용하지않는다.
- 모든요청/재전송에서현재member/session검증. 미인증/만료/폐기401(기존ACCESS_*/SESSION_*),정지403 ACCOUNT_DISABLED. DB일시장애503 SERVICE_UNAVAILABLE. no-store와401 WWW-Authenticate:Bearer 유지.
- 설정변경과멱등완료는한transaction,lease충돌/장애는설정rollback. 사용자명시저장만있으며UI위치/앱실행UX결정은Flutter범위다.

## 데이터·실행

additive `0004_member_settings`: 회원당user_id PK/FK·boolean·version·updated_at의최소테이블. 기존회원행backfill/기존자료변환/삭제없음. 설정행없는회원은GET기본값이며명시PUT에서만행생성한다. 기존game_request 결과보관/cleanup·세션권한검증을재사용한다.

기존DB/키유지·이미지빌드→`docker compose run --rm --no-deps -T api alembic upgrade head`→API만재생성→`python3 scripts/check_openapi.py`. 개발DBfixture/초기화/실기기자료삭제없음.

인계순서: 대상검증·로컬적용/계약비교 → 작업브랜치1회commit/push·원격확인 → 실제SHA·branch/push/dev반영여부와검증결과로Flutter연결요청. 실제새기기/재설치UI인수는Flutter연결후사용자명시확인으로진행한다. 이미성공한등록/이름/전투력시험반복요청없음.

## 별도 후속 계약 후보

이번API는허용설정만저장하며자동빌드갱신을시작하지않는다. #5 profiles전투력은전체Armory/역할별Snapshot을대체하지않는다. 다음범위는구현전별도합의한다.

| 후속 | 정할 항목 | 담당·완료 기준 |
|---|---|---|
| 전체Armory·역할별자동갱신 | 대상/나이스단OFF제외·앱실행1회명령·전체수집경계·quota/부분실패·원본과로컬역할계산책임 | Flutter/Backend. 합의된입력/결과·재시도/실패와역할Snapshot보존인수 |
| 회원별빌드저장·복원 | dealer/support저장Snapshot허용필드/버전·보관범위·나이스단OFF에서유지할기존빌드·서버관찰값과분리 | Flutter가필요형식제시/Backend저장계약. 기기변경/재설치후합의된저장빌드복원 |
| 선호역할·표시순서등 | 서버동기화대상/로컬유지대상·기본값·member/character식별·다중기기version충돌·초기복원순서 | 양측. 역할우선/표시순서가정확히복원되고기존자료자동이관없음 |

사용자정책미결정범위만보류하고확정회원설정의구현을미루지않는다. Firebase이관/초기화·소유증명·모집/파티·운영배포는이번범위에없다.

## 구현·검증·게시 상태

GET/PUT·엄격DTO·회원별설정·멱등/버전·0004 구현완료. 격리PostgreSQL 대상22개통과(9.61초,기존경고1개): 미설정read-onlyfalse·true/false/no-op/replay/키충돌/version충돌·세션폐기후같은회원새session유지·회원격리·guest/만료/폐기/정지·strict/quota없는provider독립·동시기기한승자·fencingrollback/동일key복구·migration/model/원래인증계약보존. Google증거는mock이며실기기/재설치UI인수는미실행. 기존등록/이름/전투력회귀전체재실행없음.

로컬API healthy200·DB0004_member_settings·OpenAPI전체일치PASS·기존19테이블집계보존/새설정테이블0확인. 개발fixture/자료이관·삭제·DB초기화/외부호출없음. 검증된현재코드/계약/문서를작업브랜치에1회commit/push해인계한다. 실제immutable구현/계약SHA와push확인은같은Issue의게시결과회신에서추적한다. dev/main병합·배포/Issue종료는범위외다.

## Flutter 연결 회신 확인

[최신 회신](https://github.com/heo0328/lostparty-backend/issues/6#issuecomment-6170276194)에서 Backend 계약 `79255f0f77602c26a215bf0340331eb697417ff4` 소비를 확인했다. 사용자 확정 UX는 기존 캐릭터관리 화면의 스위치 변경 즉시 저장이며 하단 캐릭터 저장/취소와 독립한다. GET 복원·명시 PUT·실패와 false 구분·멱등 복구/현재 GET·충돌/회원·세션 격리 연결 완료 보고다.

Flutter 자동 검증은 전체1219개 이후 국소 보완 관련32개, 최종 분석0·debug APK 성공 보고이며 전체1220개 재검증으로 표현하지 않는다. Flutter feature/member-settings 변경은 미커밋·미push·dev 미반영이다. 실제 Backend 설정 쓰기·사용자 새환경 복원은 미실행. 사용자 ON/OFF 저장·화면 재진입·동일회원 재로그인/가능한 새환경 복원 결과와 Flutter 게시 SHA를 기다린다. 새 Backend 수정/반복 시험 요청은 없다. 전체 Armory 자동 갱신·역할별 빌드 복원은 후속으로 유지한다.
