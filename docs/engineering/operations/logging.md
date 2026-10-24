# Backend 로깅과 조회

2026-10-25 / 작업 구간: Backend 로깅·관측 보강 / `chore/backend-architecture-review`.
Python 기본 logging을 사용하며 외부 서비스·새 runtime 패키지는 추가하지 않았다. **코드·후보 설정을 검증한 단계이며 실제 개발 API에는 아직 반영하지 않았다.** 기존 개발 API sourcef471e31/이미지6d5857b3 상태와 구분한다.

## 기록 내용

`app/core/logging.json`은 허용된 필드만 JSON 한 줄로 stdout에 출력한다. 시각은 UTC다.

| event | 기록·해석 |
|---|---|
| http_request | HTTP method·등록 경로 template·상태·전체 처리시간(duration_ms)·outcome·서버 생성 request_id. 404는 unmatched, query/path 실제 값·클라이언트 IP는 제외한다. 응답 streaming 종료까지 측정하며 DB 시간만을 뜻하지 않는다. 미처리 예외는500/failed,취소는cancelled로 구분한다. |
| api_rejected | 공통 예외 처리의 기존 응답 error.code/status/request_id. 정상 형식은 유지하고 하나의 요청 요약과 상세 원인 event를 request_id로 연결한다. |
| database_error | SQLSTATE 기반 connection/lock_unavailable/query_cancelled/deadlock/serialization/constraint/database 분류. query_cancelled는 서버 timeout과 다른 취소를 단정해 구별하지 않는다. |
| job_completed | auth_cleanup/ownership_settlement/recruitment의 tick 종료시각·소요시간·success/failed/partial_failure·failed_items. 가장 최근 success의 time으로 해당 프로세스의 마지막 성공을 찾는다. no-op tick의 성공도 포함하며 실제 업무1건 처리 보장은 아니다. |
| job_item_failed | legacy_opening/cycle_rollover의 항목 실패 분류. 모집 tick 내부 실패수를 누적해 일부 실패를 전체 성공으로 숨기지 않는다. 회원/방 ID는 제외한다. |
| provider_failure / google_verification | 기존 검증된 진단 vocabulary와 request_id·단계/시간을 유지한다. provider 원응답·claims·토큰은 기록하지 않는다. |
| server_event / library_event | Uvicorn/기타 라이브러리의 심각도·발생시각만 보존한다. 임의 message·예외 원문/traceback을 렌더링하지 않는다. 원문을 볼 수 없는 대신 민감정보가 예외/URL/SQL에 섞여 출력되는 것을 막는다. |

새 요청은 외부 X-Request-ID를 신뢰하지 않고 서버 UUID를 생성한다. 기존 provider 진단 UUID를 오류응답에 사용하는 경우에는 기존 응답 ID를 요청 요약에도 사용한다. 성공응답에 새 필드/헤더를 추가하지 않는다. 원ACK/직접 반환 응답의 본문은 관측기가 읽지 않으므로 그 안의 과거 request_id는 현재 요청 로그 ID와 다를 수 있다. 업무응답·권한·CAS·원ACK·no-store 정책은 유지한다.

Uvicorn 원래 access log는 --no-access-log와 별도 NullHandler로 차단해 주소·query·IP가 중복 기록되지 않게 했다. 요청본문/응답본문/헤더/쿠키·인증정보·회원/캐릭터명/원SQL·파라미터·예외 메시지·환경값은 앱 JSON 기록에 포함하지 않는다. SQL 원문을 켜는 echo/debug 설정은 추가하지 않는다. PostgreSQL 자체의 서버 로그 내용은 Python formatter가 처리하는 대상이 아니며 이번에는 그 내용 정책을 변경하지 않았다.

## 조회 방법

다음은 **개발 서버에 새 이미지·설정이 반영된 이후**의 읽기 명령이다. Windows Docker를 쓰는 WSL 예시이며 환경에 따라 docker.exe 대신 docker를 사용한다. 실제 로그 원문에 개인정보/인증정보가 없는지 확인한 부분만 협업에 공유한다. 과거 이미지의 로그까지 새 formatter로 소급 정제되는 것은 아니다.

```bash
# 최근30분의 마지막200줄
docker.exe logs --since 30m --tail 200 lostparty-backend-api-1
# 마지막50줄부터 실시간 확인 (Ctrl-C는 조회만 종료)
docker.exe logs --follow --tail 50 lostparty-backend-api-1
# 새 JSON 형식의 오류/경고
docker.exe logs --since 1h lostparty-backend-api-1 2>&1 | rg '"level":"(ERROR|WARNING)"'
# 백그라운드 tick의 최근 결과
docker.exe logs --since 1h lostparty-backend-api-1 2>&1 | rg '"event":"job_completed"'
```

공통 예외 처리 오류응답의 request_id로 같은 시간대의 로그를 검색한다. 원ACK의 과거 ID는 원래 실행 구간을 확인한다. 시간대/컨테이너를 먼저 좁힌다. 로그 조회는 서버 재시작·DB 변경을 하지 않는다. 별도 웹 대시보드/검색 서버/알림은 없고 서버 접근 권한이 필요하다. 사용자 ‘로그 확인’ 요청 시 접근 가능한 대상의 해당 구간만 조회한다.

## 보관과 적용 경계

compose.yaml의 api/db에 `json-file`, max-size10m/max-file5를 설정했다. **컨테이너당 약50MB**의 최근 기록을 유지하며 기간 보장은 없다. 용량 초과 시 가장 오래된 파일이 교체된다. Docker 로그 파일을 직접 편집·삭제하지 않고 docker logs로 조회한다. 컨테이너 재생성/제거 시 과거 로그 수명도 달라지며 무기한 이력 저장소가 아니다.

기존 컨테이너는 이 설정 변경을 자동 적용받지 않는다. 실제 API 교체 및 DB 컨테이너의 로그 정책 반영은 대상·자료보존·허용 중단을 확인하는 별도 개발 반영 구간에서 수행한다. 이번 작업은 DB 재생성·볼륨 삭제·데몬 재시작·자동배포를 실행하지 않는다. DB도 정책 반영하려고 불필요하게 재기동하지 않는다.

tick 종료 로그는 처리시간과 성공/실패 간격을 볼 근거다. 주차 업무의 예정시각 대비 지연·전체 backlog·멀티프로세스 전체 성공을 집계한 모니터링/알림은 구현하지 않았다. worker 스위치가 꺼져 있거나 로그가 회전/컨테이너가 바뀌면 이전 성공 기록이 없을 수 있다. 요청 전체의 성능 인수를 선언하지 않는다.

근거: [Python logging 설정](https://docs.python.org/3.12/library/logging.config.html), [Docker json-file 회전](https://docs.docker.com/engine/logging/drivers/json-file/). 실제 검증 범위·미실행은 [DEV_LOG](../../project/DEV_LOG.md)를 따른다.

## 구현 검증

로깅21건을 포함한 인증/Google/provider 합동78건, 최신 모집 대표회귀18건, 두 OpenAPI 객체 전체 비교와 호스트12건이 통과했다. 합성값으로 Compose의10m×5 및 Uvicorn 옵션을 렌더링 확인했다. 실시간 개발 로그 조회/실제 컨테이너 정책 반영·50MB 초과 회전·부하시험은 이번에 실행하지 않았다. 테스트 결과는 실제 개발 서버에 반영됐다는 뜻이 아니다.
