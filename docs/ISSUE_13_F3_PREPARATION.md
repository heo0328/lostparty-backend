# F3-A 독립 구현 준비 기반

2026-10-19 / Backend / `feat/raid-recruitment` / 구현 `a0a515c` 로컬 커밋·미push.

[활성화 설계](ISSUE_13_F3_ACTIVATION_DESIGN.md) 중 제품 결정에 의존하지 않는 내부 기반을 작성했다. [#13 전체19번째 Backend 준비 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263654624). **현재 실행 API 활성화·최종 계약 고정은 아니다.** 전체17번째 Flutter 검토/18번째 답변의 최초 지원범위·문턱 입력/수치·그룹탈퇴 제한/최소정리 공개는 미정 경계를 유지한다.

| 준비한 기반 | 현재 호출/검증 | 실제 연결 시 남은 일 |
|---|---|---|
| `usage.count` | 기존 F1 core.room_count가 동일 원본을 재사용 | scope/주차·캐릭터 수로 사용량을 잘못 줄이지 않고 동일 집계 유지 |
| `usage.limits_snapshot` | 내부 명시 source adapter를 격리 검증 | 기존 한도 GET을 이 source에 연결하고 실수치 전환 계약/예시 검증 |
| `readiness.require_ready` | 격리 DB의 읽기 검사·합성 제한 role 검증 | 앱 역할에 준한 격리 migration/CRUD 통과; 실제 개발 앱 계정 확인·main startup 경계 설치 |
| `runtime.admission_policy` | 후보 명령 policy·context/permissions 연결, 정지/재개·replay 검증 | 실제 main router/계약 및 설정 연결 |

## 공유 사용량과 기존 동작

`member_limits.snapshot()`의 내부 전용 `room_count` 인자는 기본None이며 기존 GET 호출은 인자를 주지 않는다. 따라서 **기존 한도 GET은 아직 unavailable**이다. 테이블 검사 실패를 fallback하는 기능이 아니라 아직 활성화하지 않은 기존 호출을 유지하는 것이다. 실제 source를 명시한 `usage.limits_snapshot()`은 count 오류·잘못된 결과를0/unavailable로 바꾸지 않는다.

집계는 현재 membership + 종료되지 않은 room만 사용한다. pending·캐릭터/원정대 개수·주차/일정 종료는 확정 방수에서 제외/초기화하는 근거가 아니다. 기존 기본한도/한도행·head 의미, 정확한도·초과 issue·회복 규칙과 GET쓰기0을 유지한다.

## 준비 검사와 정지 제어

DB 준비 검사는0018 정확한 revision과 모델의 필수 열/type/nullable·PK/FK/deferrable·unique·partial index·check 수, 활성 공통시각 trigger, directory head 및 현재 role의 SELECT/INSERT/UPDATE 권한을 확인한다. 미래 migration은 호환 확인 없이 성공 처리하지 않는다. check 식 전체 의미·trigger 함수 본문·실제 앱 계정 DDL/CRUD까지 증명하는 검사가 아니며 F3-B migration 회귀와 실제 연결 검증이 남아 있다.

`RAID_ROOM_ADMISSIONS_ENABLED`는 미설정/false/0이면 prepared wrapper가 신규 증가를 거절하며 true/1도 명시 policy를 재검사한다. 잘못된 설정은 성공 허용으로 해석하지 않고 원문을 오류에 노출하지 않는다. wrapper는 service의 reserve/replay 이후 최초 실행에서만 호출하므로 원성공 ACK는 정지 중 복구할 수 있다. 조회/거절/철회·탈퇴/이전/종료에는 이 wrapper를 적용하지 않는다.

초기 a0a515c에서는 후보 router도 wrapper를 사용하지 않았다. 후속 ffa3575에서 후보 명령과 조회 권한에 연결했다(아래 기록). **실제 main 앱에는 후보 router가 등록되지 않아 지금 개발 서버의 환경변수로 모집 제어가 가능하다는 의미는 아니다.** main lifespan/router·사용량 GET·Compose/환경·원본OpenAPI 연결은 남아 있다.

## 검증 결과

격리 PostgreSQL에서 준비 기반·기존 모집 HTTP/F2-A/F1·한도·공통시각 **144 PASS/42.77초**, 기존Starlette/AnyIO경고1개다. 기존101PASS 등과 중복이며 합산하지 않는다.

- 실제 source의0/정확한도·초과·회복·pending/주차 독립 집계, SQL 실패/잘못된 count·GET쓰기/행잠금0·head 비생성.
- 신규 생성/신청/직접가입/승인 정지, 재개 후 동일key retry, 정지 뒤 원 ACK 복구·기존 조회/거절/철회·정리와 명시 policy 유지.
- 부족한 revision/열/trigger/index/head/FK는 준비실패. 합성 NOLOGIN role에 실제 GRANT/REVOKE 후 권한 부족 검출. 이 역할 생성/권한 변경은 격리DB transaction에서 rollback했다.
- 기존 모집 원자성·경합/ACK·조회·HTTP/기존 한도 및 main app.openapi 원본 일치·모집경로 미등록.

```bash
docker compose -f compose.test.yaml run --rm -v "$PWD/app:/app/app:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/alembic:/app/alembic:ro" -v "$PWD/openapi:/app/openapi:ro" tests pytest -q -p no:cacheprovider --tb=short tests/test_raid_room_preparation.py tests/test_raid_room_http.py tests/test_raid_room_queries.py tests/test_raid_room_foundation.py tests/test_member_limits.py tests/test_record_timestamps.py
```

실제 개발/운영DB의 lostparty_app migration/CRUD·최신 개발 이미지 반영/실회원쓰기·실provider/Flutter/기기·전체 Backend suite는 이번 검증이 아니다. 기존 API8000/DB0016·자료는 변경하지 않았고 격리 테스트DB만 중지했다.

## F3-B 독립 migration·앱 역할 검증

2026-10-19 / 시험 `06a530f` 로컬 커밋·미push. `tests/test_raid_room_migrations.py`와 기존 preparation 시험 **25 PASS/9.88초**, 기존 Starlette/AnyIO 경고1개다. 이전144PASS와 일부 중복이므로 합산하지 않는다.

- compose.test의 tmpfs PostgreSQL에 무작위 이름의 일회용 DB와 LOGIN role을 생성했다. `current_user=session_user`와 NOSUPERUSER/NOCREATEDB/NOCREATEROLE을 확인했고 docker/init-db.sh와 같은 public 스키마 USAGE/CREATE 권한으로 **0016부터0017→0018까지 migration을 그 계정으로 실행**했다. 관리자 SET ROLE이나 기존 개발DB migration 시험이 아니다.
- 0016의 합성 로그인/회원·원정대/캐릭터·그룹/멤버십·주간 수동완료·개인한도 자료를 준비했다. 기존 모든 표의 전체 열/행을 해시 비교해0017 적용 전후 보존을 확인했다. 원본 행을 출력하지 않았다.
- 0017에서 실제 service로 방을 만들고 build 열이 없는 신청을 SQL로 준비했다. 0018 적용 후 신청의 기존 모든 열과 공통시각이 같고 build는NULL임을 확인했다. 나머지 모든 표도 전체 열/행이 동일했다. 없는 build를 임의로 채우지 않는다.
- 같은 제한 LOGIN 계정으로 readiness 성공, 기존 신청 상세503/거절 가능, 새 신청·승인/빌드 저장·공통시각, 공개 조회·본인 탈퇴·마지막 종료·사용량 해제를 확인했다. 기존 그룹 인증조회도200이었다. 서비스 정책은 기존 명시 test policy이며 미정 제품정책 승인 근거가 아니다.
- 시험 중 첫 실패는 테스트 SQL의 JSON 리터럴을 bind로 오인한 fixture 오류였다. bind 입력으로 고쳤고 최종25PASS에 포함됐다. 제품 코드/migration 변경은 없었다.
- 임시 DB/role은 fixture 종료 때 제거하고 격리 test-db만 중지했다. 개발 API/DB·원본OpenAPI·설정·기존자료는 변경하지 않았다. 실제 lostparty_app 권한/실자료 보존·백업복원·개발이미지 반영·Flutter/기기 검증은 별도다. 내부 독립 시험 결과이므로 이슈에 동일 명세/시험 요청 댓글을 추가하지 않았다. 협업 기준은 기존 #13 전체19번째 결과와17~18번째 결정 경계다.

## 후보 HTTP 참가 정지 연결

2026-10-19 / `ffa3575` 로컬커밋·미push. 실제 지원범위 결정에 의존하는 main 연결을 기다리는 동안 기존 후보 정책을 감싼 정지 제어를 연결했다. 공개/유한일정 후보 범위나 미정 정책을 확정한 변경이 아니다.

- 후보 생성/신청/직접가입/승인에 기존 명시 policy를 감싸 적용한다. 미설정/false/0/비정상 설정에서 신규 실행은503이며 true도 기존 지원범위/소유/주간/슬롯/CAS 검사를 유지한다.
- 참가 context 및 방/신청의 승인 permissions는 기존 원인이 없다면 SERVICE_UNAVAILABLE을 표시한다. 거절·철회·탈퇴/이전/종료 permissions에는 이 원인을 넣지 않는다. 정지 상태를 회원한도 초과 issue로 합치거나 실제 사용량을0으로 숨기지 않는다.
- 성공 ACK 재전송, 정지 실패 후 같은 key 재시도/재개, 조회·거절/철회·리더이전/탈퇴/마지막종료와 실제 내부 사용량 해제를 검증했다. 후보 OpenAPI는 설정 전후 같고 실제 main OpenAPI=원본/모집경로 미등록도 유지한다.
- 신규 HTTP 제어시험·기존 후보HTTP/조회/preparation **97 PASS/31.73초**, 기존Starlette/AnyIO경고1개. 이전 결과와 중복이므로 합산하지 않는다. 제품코드 외 검증 fixture는 기존 정상 시나리오에서만 명시 true를 설정하고 기본 미설정은 별도 HTTP시험으로 검증한다.
- 실제 main/router/lifespan·usage GET·원본계약·Compose/환경·개발서버/DB는 미변경이다. 격리test-db는중지했다. Flutter 신규시험 요청/원격게시/운영반영은 없다.

## 다음 실행

합성 자료의 migration 보존·앱 역할에 준한 격리검증은 완료했다. 후보 policy/context/permissions까지 연결했다. 다음은 최초 지원범위 답변 후 공유 usage·main startup/router·최종OpenAPI를 연결하는 구간이다. 사용자에게 ‘공개 모집·현재주차 안 시작/종료가 확정된 일정·최소전투력 조건 없음’의 최초 실제지원 여부를 질문했다. #13 전체17번째가 이 결정을 명시적으로 남겼으므로 미응답을 승인으로 처리하지 않는다. 역할별 문턱/UI와 그룹 전용은 계속 후속이다. 실제 API 연결/최종 계약 고정·개발 서버 활성화는 필요한 결정 후 F3-A/B 나머지 구간으로 진행한다. 문턱 UI·그룹 분기를 임의 구현하거나 F3 전체를 완료 처리하지 않는다. Backend 준비 결과에 대한 Flutter 신규/동일코드 테스트 요청은 없다.
