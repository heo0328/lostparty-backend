# Issue #3 모바일 조회 인계 이후 등록 관리 구간 계획

작성: 2026-10-14. 상태: **준비 인계·lease 헤더 보완·대상검증·로컬 적용 완료, server key/실등록 인수 후속**.

근거: [Flutter 조회 결과·등록 구간 요청](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6161970774). 구현/계약은 `254cb5de125ab1bcb2aa084e091eae976e9a078a`, Backend 게시 기록은406004e. [현재 API 안내](ISSUE_3_DEVELOPMENT.md)와 [협업 단계](API_COLLABORATION_WORKFLOW.md)를 따른다. 이전 구현을 재작성하거나 동일 API를 추가하지 않는다.

## 1. 최신 인계와 준비 상태

| 항목 | 확인 결과·근거 수준 |
|---|---|
| Flutter 소비 계약 | #3 업무 계약254cb5d 소비 확인, Backend dev/main 미통합 구분 |
| Flutter 코드 | 조회 구현6f97190·문서363ebc2·dev 통합/push3cedd9dd5eda9c1188e66fa3264f386c080f2449 보고. 원격/로컬 Flutter 소스를 별도로 읽지는 않음 |
| 자동 검증 | Flutter1159개 통과(조회 경계25 포함), analyze0·debug빌드 성공 보고. fake HTTP/세션 검증이며 실제 Backend transaction 인수와 구분 |
| 사용자 에뮬레이터 | 로그인 후 빈 등록 안내·로그아웃 후 로그인 필요·로컬 화면 보존 확인 보고. 등록 캐릭터 화면은 등록이 없어 미실행 |
| 모바일 범위 | 등록 GET·캐릭터 GET만 연결. 신규 등록/PATCH/DELETE/refresh·challenge·활동/대표 쓰기는 미연결 |
| Backend 결함 보고 | 이번 조회 구간에서 재현된 결함 없음 |
| 실행 중 Backend | app/alembic 전체py 파일 hash를 게시254cb5d와 비교해 일치. container에Git SHA가 내장됐다는 주장과 구분 |
| DB/접속/계약 | 읽기 전용 DB revision0002_game_accounts, health200, 최신API 전체OpenAPI 일치 재확인 |
| 서버 key | runtime LOSTARK_API_TOKEN 비어 있음. 값 없이bool만 확인 |

이번 준비 확인은 재빌드·DB 초기화·자료 삽입·새 테스트 실행 없이 수행했다. 기존114개Backend pytest는 이전 결과다. 조회 인수를 쓰기/실provider/장비 인수로 확대하지 않는다.

## 2. 이번 목표와 API 경계

목표: 캐릭터 검색 → 미리보기 → 사용자 명시 등록 → 등록/캐릭터 조회 → 표시명·본계정 수정 → 요약 갱신 → 명시 제거, 그리고 로컬 캐릭터/빌드 보존 확인.

| 기능 | 기존 API·규칙 | 현재 준비 조건 |
|---|---|---|
| 검색 | POST /v1/game-accounts/preview, character_name, Bearer, Idempotency-Key 필수 아님 | server key+정상 siblings 필요, Armory 장비 증명은 불필요 |
| 등록 | POST /v1/me/game-accounts, lookup_character_name/label/is_main, UUIDv4 key | fresh siblings 재조회. preview를 소유 proof로 사용하지 않음 |
| 조회 | GET /v1/me/game-accounts 및 등록/characters | 로그인 후 빈 목록은 지금 정상 동작. 등록 이후 preview 캐릭터는 UUID권한ID=null |
| 수정 | PATCH 등록 경로, expected_version+변경필드, UUIDv4 key | 자신의 live 등록이 있으면 외부 API/key 없이 처리 가능 |
| 제거 | DELETE 등록 경로, query expected_version, UUIDv4 key,204 | 사용자 명시 제거만, 같은 actor 성공 replay204. 로컬 자료/canonical 삭제와 분리 |
| 갱신 | POST 등록/refresh,{},UUIDv4 key | server key+fresh siblings 필요. 동일 등록 수동10초 제한 |

미인증 등록은 정상 상태이고 인증/활동 자격을 만들지 않는다. 전체 장비 인증 인수는 이 구간의 선행 조건이 아니다. 공개 mock/성공 fixture를 개발 DB에 삽입해 실제 등록 화면을 위장하지 않는다.

## 3. 실행할 작업과 검증 단위

| 순서 | 작업·담당 | 산출물·완료 기준 |
|---|---|---|
| A. 준비 인계 | Backend, 지금 수행 | 실행소스254cb5d/0002/계약 일치·키 미설정·API별 제한과 로컬 준비 절차를 Issue에 답변 |
| B. 좁은 계약 보완 | Backend | 아래 lease 실패409의 Retry-After 누락 분기를 대상 테스트로 재현·보완. API 경로/DTO·인증6API/완료조회 유지 |
| C. 등록 UI 연결 | Flutter, A/B와 병행 | 기존 preview/등록/PATCH/DELETE/refresh Repository/UI 구현. 동일key/payload·GET복구,503 예상 제한·로컬 보존 처리. 실제 key/장비 자료를 기다리며 UI구현을 미루지 않음 |
| D. server key 준비 | 사용자·Backend | .env 로컬 설정 및 API환경 적용, 존재bool만 확인. 인게임 장비조작은 필요 없음 |
| E. siblings 실관찰 | Backend | 실제 응답 필드/타입/null/수치/200상한·입력캐릭터존재를 parser와 대조. 실제명/키/raw개인정보 없는 shape 근거·status/code/시각 기록 |
| F. 등록 관리 수동 인수 | 사용자·Flutter·Backend | 신규등록→두조회→label/main전환→refresh→명시제거→재조회,실패/유실·로컬보존. 명시적 사용자 동작으로 만든 대상만 사용 |
| G. 발견된 차이 수정 | Backend | 실제 차이가 있는 parser/오류만 수정, 필요한 대상 회귀·최신OpenAPI비교, 변경SHA/호환 영향 인계 |

### B의 구체 대상

정적 검토에서 `support.reserve()`의 처리중409는 Retry-After2를 지정하지만 `support.commit_result()`의 lease generation/만료 거절은 같은 REQUEST_IN_PROGRESS를 `fail()`로 발생시켜 Retry-After가 생략되는 분기를 확인했다. 모바일에서 재현됐다고 보고된 결함은 아니다.

다음 구현은 이 분기의 header 일관성만 보완한다. lease takeover/만료 시 구worker의 업무변경 rollback·다른worker 상태 보존 및409/header를 대상 검증한다. 완료된GET/PATCH/DELETE의 동작을 다시 작성하지 않는다. public schema 변경이 필요 없다면 계약내용/SHA 유지 여부를 명시하고 구현SHA만 인계한다. 현재114개 전체를 단순 준비 확인을 위해 반복 실행하지 않는다.

### E/G의 검증 범위

siblings의 ServerName/CharacterName/CharacterClassName string, CharacterLevel int, ItemAvgLevel nullable string은 기존 Flutter 파서와 mock 근거다. 현재 adapter가 이 형태를 소비하도록 구현돼 있지만 실응답 인수는 미실행이다. preview/등록/refresh의 summary 호출은 proof=False여서 Armory·proof_validated가 성공 조건이 아니다. 실제 자료가 기대 형태면 추가 코드 변경 없이 등록 관리 인수를 진행한다.

실제 차이가 있으면 수치/null·응답크기·입력 누락·중복·상한·외부 실패 처리에 직접 영향 있는 부분만 수정한다. 잘못된 응답을 정상 빈 roster로 덮어쓰지 않는다. 인수 중 재현되는 409/429/503·유실 문제는 safe status/code/request_id와 동작을 근거로 보완한다. 실제 provider quota와 다른 consumer 영향은 관찰 근거로 기록하고 검증된 범위만 보고한다.

## 4. 키 준비·적용 절차

설정 파일은 Backend 프로젝트의 `.env`(`/home/heowork/projects/lostparty-backend/.env`), 변수명은 `LOSTARK_API_TOKEN`이다. 사용자는 로컬 편집기에서 값을 설정하고 기존 파일 권한을 유지한다. 값·.env 본문·실사용 캐릭터명은 Issue/채팅/앱에 전달하지 않는다. Flutter 개인 키를 업로드할 API를 만들지 않는다.

이미 source/migration은 현재 구현과 같으므로 키 준비만으로 migration/DB 재생성/전체재빌드가 필요하지 않다. compose.yaml의 환경 매핑을 적용하기 위해 API 컨테이너만 재생성한다.

```bash
# Backend 프로젝트 디렉터리에서, 로컬 .env 편집 완료 후 실행
docker compose up -d --no-deps --force-recreate --wait --wait-timeout 180 api
```

키 존재 여부만 확인한 뒤 정상 캐릭터 검색을 사용자가 실행한다. health200은 API/DB 상태 근거이며 provider credential이 유효하다는 증거가 아니다. 키가 잘못됐거나 API가 장애이면503 UPSTREAM_UNAVAILABLE로 자료 보존하며 장비인증 실패와 혼합하지 않는다.

## 5. 병행·보류·인계 기준

- 지금 가능한 일: 준비 인계, 좁은header보완·대상검증, Flutter등록UI/Repository 연결·503/409/유실 처리.
- key 준비 이후: 실제 preview·등록·refresh. 기존등록이 없다는 사실을 DB fixture 삽입으로 해결하지 않는다.
- 별도 이후 그룹: 장비challenge/소유권이전·활동/대표 Flutter쓰기. PROVIDER_EVIDENCE_PENDING/ROSTER_EVIDENCE_PENDING 및 suspect 보류를 유지한다.
- 승인 별도: dev/main 통합·이번 신규수정 게시·운영배포·기존데이터 파괴. 앞선 commit/push 완료를 새변경이나 merge 승인으로 확대하지 않는다.

인계는 구현/실행/계약 버전, 실제로 실행한 대상 검증과 이전114개 결과, 바로 가능한 기능/제한, 필요한 로컬 key 준비를 분리한다. 이번 실행에서 헤더 보완과 로컬 적용을 완료했다. 실제 등록·장비 인수 완료를 의미하지 않는다.

## 6. 이번 계획 실행 결과

lease 만료·다른 worker takeover 두 HTTP 사례를 추가해 수정 전409의 Retry-After누락을 실제로재현했다. commit_result의 해당거절을 GameError(REQUEST_IN_PROGRESS,409,2)로수정했다. 대상회귀10개통과(106개제외,기존경고1개): 새HTTP2사례·rollback/처리권보존,기존lease/멱등/DELETE replay/장애복구/권한/계약경계. 이전114전체를반복하지않았으며현재전체116개통과라고표시하지않는다.

최신image를로컬API에적용했고 source hash·health200·기존인증6테이블건수동일·DB0002·OpenAPI전체일치를확인했다. openapi파일은게시254cb5d와byte단위동일,경로/DTO/필수헤더/schema변경없음이다. 보완implementation `db0f3ae438021b4f5fa3738b76fd926687871b0d`을작업브랜치에게시했다. 실행중API에도동일코드가적용됐다. 원본계약SHA254cb5d는그대로이며dev/main통합은별도다.

로컬.env와실행환경의LOSTARK_API_TOKEN은비어있음을값없이확인했다. D/E/F의key·실siblings·수동등록인수만후속입력에의존한다. 개발DB에fixture/임의등록을삽입하지않았고DB초기화·migration재적용·운영변경없음이다. Flutter는기존계약으로등록UI/Repository연결을진행할수있다.
