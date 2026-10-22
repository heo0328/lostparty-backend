# Issue #13 W5 — 로컬 개발 DB/API 전환

2026-10-22 / Backend / `feat/raid-recruitment` / 시작 `0bf3f44`.

사용자의 다음 구간 진행 지시에 따라 **기존 로컬 개발 DB0023→0029와 API8000/모집 worker를 전환했다.** 운영 배포·dev/main 병합·자료 초기화는 수행하지 않았다. 착수 시 AGENTS→협업→NEXT_WORK→AI_CONTEXT→계약3판/4판/ACK, Git과 Issue 본문/전체91번째까지를 확인했고 새 계약 변경·사용자 미커밋 변경은 없었다.

사용자 확인: 지난주 키 모집이 현재 C/N 모집에서 제외되는 것은 정상이다. 과거7건의 검색 제외를 제품 미결정이나 전환 장애로 취급하지 않는다. 원본과 persistent 관계는 보존한다.

## 실제 전환과 보존

[직전 checkpoint 집계](design/issue13-cutover-checkpoint.json) · [실행 결과 집계](design/issue13-live-cutover.json) · [이전 복원 리허설](ISSUE_13_W5_RESTORE_PREFLIGHT.md).

1. 실행 컨테이너는 기존 API/DB 두 개뿐이고 DB0023임을 확인했다. 구 API를 정지해 내부 모집/소유권/인증 정리 worker도 중단하고, DB의 다른 연결0개를 확인했다. source-reader는 읽기 전용이며 uvicorn/worker를 실행하지 않는다.
2. `scripts/recruitment_restore_preflight.py --docker docker.exe --image lostparty-two-cycle-preflight:f276342 --report docs/design/issue13-cutover-checkpoint.json --quiesced-checkpoint`를 실제 실행했다. 새 snapshot83표/414행·제한 LOGIN 복원/0029 이행 보존·별도 fresh0023/구 이미지 복구·키4개/시퀀스1/DB profile 일치가 통과했다. 이번에는 `source_writes_paused=true`, `cutover_checkpoint=true`다. 이전 무정지 리허설과 구별한다.
3. 별도 migration runner는 source와 동일 환경·DB network·읽기 전용 키 mount, rootfs read-only/cap_drop ALL을 사용했다. 검증된 후보 이미지의 **app/alembic Python 소스 전부가 현재 작업트리와 일치**함을 확인했다. 실제 `lostparty_app` LOGIN의 제한 권한과 checkpoint 원본 지문을 재확인한 뒤 `alembic upgrade 0029_cycle_outcomes`를 실행했다.
4. **version을 제외한82개 기존 업무 테이블413행의 모든 열·기록 시각·열 정의가 일치**했다. 원본 키4개·시퀀스1개·UTF8/en_US.utf8, DB volume·환경 값을 유지했다.0029 전체 readiness는 DB 비소유자·NOSUPERUSER/NOCREATEDB/NOCREATEROLE LOGIN에서 통과했다.
5. 검증한 이미지에 `lostparty-backend-api:two-cycle` 태그를 붙이고 [전환 override](../compose.two-cycle.yaml)로 **API만** `--no-deps --no-build --wait` 재기동했다. factory는 `app.main:create_two_cycle_app --factory`이며 같은 lifespan에서 새 cycle worker를 기동한다. DB 컨테이너는 재생성하지 않았다. 구 이미지ID는 그대로 남겼고 새 DB에 구 worker를 기동하지 않았다.
6. Compose 재기동 후 Docker Desktop이 키 bind 원본을 POSIX 경로 대신 같은 WSL 디렉터리의 UNC 경로로 표시해 최초 문자열 동일성 검사만 실패했다. 같은 경로로 정규화하고 mount 목적지/ro·원본 키 bytes·환경/보안/포트를 재검증해 일치했다. 이를 자료 변경이나 migration 실패로 처리하지 않았다.
7. 실제 API 기동 후 모든 테이블 지문이 migration 직후와 일치했고 worker 기동 후에도 과거 review 자료를 자동 변경하지 않았다. migration runner와 리허설 전용 DB/network를 정리해 기존 API/DB만 healthy로 남겼다.

실행 이미지: `sha256:ccc787cb9ccb3bf5731336398d3fedf6645178244ac2b5014243208d479250a2`. 구 이미지: `sha256:efde69d269a405358d99a45b1a2bbf243b0cb3f1408a29d878ee05e759d2b5fb`. 새 이미지의 기능 소스는 `f27634246a6e54988d815cb8009fd02ec621b6b7` 기준이고 이후 변경은 백업 도구/문서·이번 Compose 이미지 선택이다. 실행 이미지와 현재 app/alembic 소스의 바이트 일치를 따로 검증했다.

checkpoint는 `backups/lostparty-preflight-f2b2a14f7162`에0700/0600으로 보관한다. DB archive·인증 키·환경/실행 설정·원본/이행 지문은 비공개이며 Git/Docker build에서 제외한다. 공개 artifact에는 집계/일치 여부만 포함한다. 원본 overwrite/drop/downgrade·볼륨 삭제는 하지 않았다. **새 쓰기 이후 이전 snapshot으로 되돌려 새 자료를 버리지 않는다.** 이후 복구는 새 쓰기 보존 범위와 연결 전환을 확인해야 한다. checkpoint 도구는 source0023 전용이므로 이제29인 실제 source에 재실행하지 않는다.

## 실제 확인과 한계

| 구분 | 실제 결과 |
|---|---|
| 서버 health | 컨테이너 내부 HTTP 및 호스트 `127.0.0.1:8000/health` 200 |
| 실행 계약 | factory167경로·기본 소스116경로 각각 고정 파일과 전체 객체 일치. 현재 서버는167경로 factory |
| 고정 소비 계약 |0.4.1/policy4·53경로56동작204schema, canonical SHA `fb4c7d065594a9a0e7e8288e5f73179f90b078b68ac4323d1aade5c7a63b42f1` 불변 |
| 공개 HTTP | v1 검색200/0건, v2 C/N 검색각200/0건 |
| 인증 거절 HTTP | 메타 무인증/잘못된 Bearer, summary 무인증, v1/me 무인증 모두401 ACCESS_INVALID·WWW-Authenticate Bearer |
| 캐시 | 실제 v1/v2 HTTP 성공/오류 모두 Cache-Control:no-store |
| HTTP 합계 | health/검색/인증 거절8검사 통과. 호스트 health는 별도 추가 확인 |
| 서비스 읽기 | 기존 유효 세션2회원: C/N 관계 목록각7건/not_selected, 현재 plan TARGET_NOT_OPEN7건, leave-context allowed/impact0 각7건 |
| 과거 자료 | C/N 밖 cycle7개·review/legacy_unknown/generation unknown·assignment evidence7. 새 explicit/참가/동의0 |
| 읽기·worker 후 | migration 직후 전체 테이블 지문 불변. 실제 leave/end·회원 쓰기 명령은 실행하지 않음 |

실제 인증된 HTTP 성공·Google 로그인/provider·기기 인수는 **미확인**이다. 자동 승인 검토가 추가하려던 기존 세션 기반 테스트 액세스 토큰 발급/저장을 credential-probing side effect로 거절했다. 해당 코드는 실행되지 않았고 발급/저장 없이 승인된 DB/API 전환과 읽기·공개 HTTP/인증 거절 검증으로 진행했다. 서비스 읽기는 JWT/HTTP 로그인 성공의 증거가 아니다. 필요한 실제 로그인/메타·summary 성공 확인은 Flutter의 정상 로그인 세션으로 수행한다.

기존 W5 고유304 합성 시험·백업 보호7시험은 이전 구간 근거이며 이번에 다시 실행/합산하지 않는다. 이번 변경은 이미지/진입점 선택과 실제 이행·문서/집계이며 API DTO·DDL·고정 계약을 추가 변경하지 않았다. v1 위험 방 쓰기의 원 ACK 우선/409 CLIENT_UPGRADE_REQUIRED·본인 수동 C10시/개인표 유지의 근거는 기존 W4-D/W5 격리 검증이며 실제 회원 명령을 재실행한 것으로 표시하지 않는다.

## 재기동과 다음 담당

현재 개발 DB29에는 다음 구성을 사용한다. `compose.yaml` 단독의0023 기본 앱으로 기동하지 않는다. 이 명령은 migration/초기화를 하지 않는다.

```bash
docker.exe compose -f compose.yaml -f compose.two-cycle.yaml up -d --no-deps --build --wait --wait-timeout 180 api
python3 scripts/check_openapi.py --docker docker.exe --container lostparty-backend-api-1 --profile two-cycle
```

첫 전환 때는 리허설에서 검증한 동일 이미지로 `--no-build`를 사용했다. 이후 코드 변경 시 위 명령으로 two-cycle 태그를 새로 빌드한다. 호스트 포트8000·기존 환경/키/읽기 전용 mount·보안을 유지한다. 실제 기기에서 기존 연결 경로에 도달하는지 여부는 Flutter 확인 범위다.

commit/push·원격 SHA 확인 후 **Flutter**에 합의된 다음 구간 GET `/v2/raid-cycles`·POST `/v2/me/raid-weekly-summary`와 주차 선택/target 본인 목록·계정 캐시 격리를 인계한다. 정상 로그인 세션으로 두 조회 성공·C/N 선택·계정 전환/로그아웃 캐시 격리·사용 계약 SHA를 같은 Issue에 회신하면 된다. 과거 키 모집이 현재 검색에 없는 것은 정상이며 새 모집/쓰기 전체 실기기 인수와 구별한다. Backend는 재현 가능한 차이/실패가 오면 해당 구간을 보완한다. Issue는 OPEN이며 Flutter 적용/실회원 쓰기/운영 인수·#19 통계 완료로 표시하지 않는다.
