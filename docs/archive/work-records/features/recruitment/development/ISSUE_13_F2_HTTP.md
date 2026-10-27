> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [participation](../../../../../features/recruitment/participation/README.md) · [creation-and-settings](../../../../../features/recruitment/creation-and-settings/README.md) · [search](../../../../../features/recruitment/search/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# F2-B 모집 후보 HTTP 연결

2026-10-19 / Backend / `feat/raid-recruitment` / [상세 제안](../contracts/ISSUE_13_R1_R2_CONTRACT_DRAFT.md)·[F2 설계](../planning/ISSUE_13_F2_IMPLEMENTATION_DESIGN.md)·[F2-A](ISSUE_13_F2_READS.md) 기준.

최종 **101 PASS/35.00초**(HTTP43+F2-A23+F1 32+시각3), 기존Starlette/AnyIO경고1개. 구현은 `9fb2058` 로컬커밋·미push이며 [#13 전체15번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260695606)에 회신했다. 다음 담당은 Backend F3다.

## 지원과 연결

`app/raid_rooms/router.py`에 기존 제안의 18 HTTP 동작을 연결했다. 이 라우터는 **main 앱에 등록하지 않았다.** 격리 테스트 앱에서 기존 인증·오류 envelope·no-store middleware 및 실제 PostgreSQL 원본을 사용한다. provider 응답과 회원 신원은 테스트 fixture이며 실회원/실provider 검증이 아니다.

- 공개 모집 목록/요약, 현재참가자 상세·본인 현재/종료관계, 본인 참가조건, 신청자·현재파티장 신청조회, 본인 최소관리.
- 생성, 신청/직접가입, 승인/거절/철회, 본인탈퇴/파티장이전/마지막1인종료.
- 공개·현재주차·유한 단일회차·최소전투력 미설정·leader_only/direct_join만 지원한다. Q1 미정/주차초과 일정, Q2 최소전투력 문턱, Q3 그룹방은 해당 분기만 미지원이다. 전체완료/반복·고급관리·통계·그룹/V2 통합을 추가하지 않는다.

## HTTP 경계

`http_schemas.py`는 내부 명령 위에 wire 전용 검증과 최소 ACK를 정의한다. 생성 입력의 그룹 CAS 3필드와 min_combat_power는 초안처럼 required/nullable를 유지한다. public은 group_id 및 그룹 CAS가 모두 null이어야 하고 group은 모두 nonnull이어야 한다. 전투력은 plain decimal 문자열만 받되 문턱이 설정된 지원 분기는 COMBAT_REQUIREMENT_UNAVAILABLE이다. 공개 정책에 필드를 삭제하거나 임의 기준을 넣지 않는다.

일정은 UTC RFC3339 문자열/null, cycle은 유효한 날짜 문자열, catalog_version은 기존 카탈로그와 같은 1..64자 문자열이다. 숫자형 timestamp/비UTC 시각·가짜 입력 actor/user_id/수치/표시·잘못된 역할·bool revision·추가 필드를 거절한다. 카탈로그 버전을 raid ID의 제한된 문자 집합으로 검사하지 않는다.

알 수 없는/중복 query, 정수가 아닌 limit/party_no·범위 초과·빈 cursor, GET body, 중복 Authorization/Idempotency-Key 및 중첩 JSON 중복 키를 INVALID_REQUEST/400으로 처리한다. 명령 key는 UUIDv4다. 인증은 기존 세션에서 actor를 결정하며 공개 조회도 Authorization이 명시되면 잘못된 인증을 비로그인으로 우회하지 않는다. 오류는 입력 원문 없이 code/message/request_id를 주고 401 Bearer·409 REQUEST_IN_PROGRESS의 Retry-After2를 유지한다. 성공/실패 모두 no-store다.

지원 생성 입력 전체가 원명령 digest에 포함된다. min_combat_power를 변경해도 원키/본문 충돌 검사를 우회하지 않는다. 최소 ACK는 과거 성공이며 현재 권한/구성은 GET으로 재조회한다. 탈퇴 후 옛 ACK·파티장 이전 후 원승인 ACK를 복원해도 새 참가관계/권한을 되살리지 않는다.

F2 연결 중 `core.room`의 기존 방 접근을 공개방에 한정했다. 그룹방은 active/ended나 명령 종류에 관계없이 ROOM_NOT_FOUND/404이며 원본 ID로 존재 여부를 추측하거나 Q3 미합의 철회/종료를 실행하지 못한다. 그룹 생성 자체의 미지원 입력은 ROOM_FEATURE_UNSUPPORTED로 구분한다. 원래 성공이 있었던 최소 ACK 복구와 현재 private 권한은 구별한다.

## 검증 범위와 남은 단계

최종 실행 결과·SHA·댓글 링크는 [DEV_LOG](../../../../../project/DEV_LOG.md)와 [NEXT_WORK](../../../../../project/NEXT_WORK.md)에 기록한다. 검증 명령:

```bash
docker compose -f compose.test.yaml run --rm -v "$PWD/app:/app/app:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/alembic:/app/alembic:ro" tests pytest -q -p no:cacheprovider --tb=short tests/test_raid_room_http.py tests/test_raid_room_queries.py tests/test_raid_room_foundation.py tests/test_record_timestamps.py
```

실제 HTTP 생성→신청→승인→이전→탈퇴→마지막종료, 직접가입/재가입 후 옛 ACK, 본인신청 철회/파티장 거절, 조회/입력/헤더/권한·타인정보 비노출, 마지막자리 동시가입·source 변경 후 최종검사, ACK 기록 실패 전부 rollback과 커밋 후 응답유실의 원 ACK 복구를 검사한다. 후보 18동작과 required/nullable·응답모델·오류헤더를 확인하며 기존 main app.openapi와 원본 계약 일치·모집 경로 미등록을 별도로 확인한다.

현재 결과는 **격리 앱에서의 후보 HTTP/DB 동작 검증**이다. 원본 OpenAPI는 기존 실행 API 기준을 유지한다. 후보 FastAPI의 자동 schema는 F3에서 main 앱의 기존 OpenAPI 가공(422 제거/공통 응답헤더 등)과 함께 최종 원본과 맞춘다. 개발 서버8000·DB0016/이미지·기존자료·사용량 source/V2/G3를 변경하지 않았다. Flutter 구현 테스트·실기기·실provider·운영/전체 Backend suite 검증은 별도다.

다음 Backend F3: 현재 지원 부분집합을 명시한 최종 계약을 정리하고, 데이터 보존 migration0017+0018·사용량 source 활성화·main 앱 router/OpenAPI·개발 이미지를 하나의 검증 구간으로 맞춘다. 최신 이미지에서 기존 API/전체 실행 계약을 비교하고 commit/push·원격 게시 확인 후 필요한 소비 인계를 한다. Flutter #15 우선/Q1~Q3 분리 원칙을 유지한다. merge/운영 배포·자료삭제 승인은 포함하지 않는다.
