# F3-A 독립 구현 준비 기반

2026-10-19 / Backend / `feat/raid-recruitment` / 구현 `a0a515c` 로컬 커밋·미push.

[활성화 설계](ISSUE_13_F3_ACTIVATION_DESIGN.md) 중 제품 결정에 의존하지 않는 내부 기반을 작성했다. [#13 전체19번째 Backend 준비 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263654624). **현재 실행 API 활성화·최종 계약 고정은 아니다.** 전체17번째 Flutter 검토/18번째 답변의 최초 지원범위·문턱 입력/수치·그룹탈퇴 제한/최소정리 공개는 미정 경계를 유지한다.

| 준비한 기반 | 현재 호출/검증 | 실제 연결 시 남은 일 |
|---|---|---|
| `usage.count` | 기존 F1 core.room_count가 동일 원본을 재사용 | scope/주차·캐릭터 수로 사용량을 잘못 줄이지 않고 동일 집계 유지 |
| `usage.limits_snapshot` | 내부 명시 source adapter를 격리 검증 | 기존 한도 GET을 이 source에 연결하고 실수치 전환 계약/예시 검증 |
| `readiness.require_ready` | 격리 DB의 읽기 검사·합성 제한 role 검증 | 실제 앱 계정 migration/CRUD 및 main startup 경계 설치 |
| `runtime.admission_policy` | 명시 policy를 감싼 최초 실행·정지/재개·replay 검증 | 후보/실제 명령 policy 주입, context/permissions의 정지 사유 연결 |

## 공유 사용량과 기존 동작

`member_limits.snapshot()`의 내부 전용 `room_count` 인자는 기본None이며 기존 GET 호출은 인자를 주지 않는다. 따라서 **기존 한도 GET은 아직 unavailable**이다. 테이블 검사 실패를 fallback하는 기능이 아니라 아직 활성화하지 않은 기존 호출을 유지하는 것이다. 실제 source를 명시한 `usage.limits_snapshot()`은 count 오류·잘못된 결과를0/unavailable로 바꾸지 않는다.

집계는 현재 membership + 종료되지 않은 room만 사용한다. pending·캐릭터/원정대 개수·주차/일정 종료는 확정 방수에서 제외/초기화하는 근거가 아니다. 기존 기본한도/한도행·head 의미, 정확한도·초과 issue·회복 규칙과 GET쓰기0을 유지한다.

## 준비 검사와 정지 제어

DB 준비 검사는0018 정확한 revision과 모델의 필수 열/type/nullable·PK/FK/deferrable·unique·partial index·check 수, 활성 공통시각 trigger, directory head 및 현재 role의 SELECT/INSERT/UPDATE 권한을 확인한다. 미래 migration은 호환 확인 없이 성공 처리하지 않는다. check 식 전체 의미·trigger 함수 본문·실제 앱 계정 DDL/CRUD까지 증명하는 검사가 아니며 F3-B migration 회귀와 실제 연결 검증이 남아 있다.

`RAID_ROOM_ADMISSIONS_ENABLED`는 미설정/false/0이면 prepared wrapper가 신규 증가를 거절하며 true/1도 명시 policy를 재검사한다. 잘못된 설정은 성공 허용으로 해석하지 않고 원문을 오류에 노출하지 않는다. wrapper는 service의 reserve/replay 이후 최초 실행에서만 호출하므로 원성공 ACK는 정지 중 복구할 수 있다. 조회/거절/철회·탈퇴/이전/종료에는 이 wrapper를 적용하지 않는다.

아직 후보 router조차 이 wrapper를 사용하지 않는다. **지금 환경변수를 바꿔 실제 서버 정지가 가능하다는 의미가 아니다.** runtime 설정·준비 검사·사용량 source의 실제 호출부는 계약/활성화 단계에서 함께 연결한다. main lifespan/router·Compose/환경·원본 OpenAPI는 이번에 수정하지 않았다.

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

## 다음 실행

결정 전에도 합성 자료의 migration 보존·실제 앱 역할에 준한 격리검증 준비와 지원표/예시 대조를 이어갈 수 있다. 실제 API 연결/최종 계약 고정·개발 서버 활성화는 필요한 결정 후 F3-A/B 나머지 구간으로 진행한다. 문턱 UI·그룹 분기를 임의 구현하거나 F3 전체를 완료 처리하지 않는다. Backend 준비 결과에 대한 Flutter 신규/동일코드 테스트 요청은 없다.
