# F2-A 모집 조회·권한·참가조건

2026-10-19 / Backend / `feat/raid-recruitment` / [F2 설계](../planning/ISSUE_13_F2_IMPLEMENTATION_DESIGN.md)·[상세 제안](../contracts/ISSUE_13_R1_R2_CONTRACT_DRAFT.md) 기준.

현재 후속: [F2-B 후보 HTTP](ISSUE_13_F2_HTTP.md) 9fb2058/101PASS까지 진행했다. 아래는 F2-A 당시 결과이며 main 앱/개발DB 활성화는 여전히 F3다.

## 구현한 구간

- `schemas.py`: 공개 요약/상세·현재/종료 본인관계·신청·최소관리·참가조건의 required/nullable 응답 DTO. 기존 CharacterDisplay/P1 RoleSummary를 재사용하며 전역 타인 user UUID·등록/소유 선택원문·개인키를 출력하지 않는다.
- `queries.py`: 공개 현재주차 목록/요약, 현재참가자 상세, 본인 현재/종료관계, 본인신청·현재파티장 신청목록/개별조회, 최소관리와 본인 admission-context. 각 호출은 REPEATABLE READ + SET TRANSACTION READ ONLY이고 provider 호출·행생성·만료정리·예약·행잠금이 없다.
- `projections.py`: 권한별 allowlist, 당시 표시/빌드와 현재 소유/활동/입장레벨의 분리, 검토 필요/빌드 stale, 한도3원인의 설명과 진행/회복 권한을 투영한다. 신청자는 본인신청만, 현재파티장은 해당방 신청만 볼 수 있으며 일반참가자/이전파티장/무관한 회원은 다른 사람 신청을 조회하지 못한다.
- HMAC cursor는 actor/조회종류/필터/limit에 묶고 주차·head·현재 표시/권한 결과 및 해당 방 policy revision을 대조한다. 개인 head가 같아도 다른 참가자의 가입·방의 제한/파티장 변경·논리만료가 영향을 주면 stale다. 공개 cursor에는 신청 head를 연결하지 않는다. 주차 변경은 CURSOR_STALE로 재조회한다.
- admission-context는 본인 현재 source revision을 해결하고 intent=apply/join을 구분한다. 신청은 자리·방한도 증가를 예약하지 않고, 직접가입은 정원·구성·겹치는 일정을 검사한다. 최종 명령은 현재 원본을 재검사한다.
- `policies.public_finite`는 공개·유한 단일회차의 명시 adapter다. 기존 F1 생성/가입 함수의 필수 policy 주입을 유지하며 자동 기본 허용값으로 연결하지 않는다. 미정 Q1~Q3와 최소전투력 문턱은 활성화하지 않는다.

## F1과의 직접 연계 보완

F1 selection 검사를 읽기에서 재사용할 때만 행잠금을 생략하며 기존 쓰기의 기본값은 잠금 유지다. 참가 빌드를 `version/summary/saved_at` 묶음으로 보존하고, 신청에도 당시 빌드 묶음을 남긴다. 신청 Selection CAS 원문은 별도로 유지한다. 현재 P1 요약으로 과거 빌드를 재작성하거나 가입 근거로 승격하지 않는다.

`0018_room_application_build`는 신청표에 nullable JSONB `build` 열만 추가하는 **신규 migration**이다. 기존 0017 이력을 수정하지 않았고 기존 행에 가짜 빌드 backfill을 하지 않는다. 격리 테스트DB에서만 적용했다. 예전 내부 snapshot의 metadata가 없으면 상세 빌드 조회는 SERVICE_UNAVAILABLE로 구분하며 당시 버전/요약을 추정하지 않는다. 빌드를 사용하지 않는 공개요약·본인 최소정리는 계속 가능하다. 개발DB에는 F1 원본 자체가 아직 없어 실제 모집 이관/복원 작업은 하지 않았다.

## 검증 및 제공 상태

최종 **58 PASS/23.38초**(F2-A23+F1 32+시각3), 기존 Starlette/AnyIO 경고1개다. F2-A 구현은 `e74d850` 로컬 커밋·미push, [#13 전체14번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260548709)에 회신했다. [DEV_LOG](../../../project/DEV_LOG.md)에 실패 정정·검증 범위를 기록한다. 실행 명령:

```bash
docker compose -f compose.test.yaml run --rm -v "$PWD/app:/app/app:ro" -v "$PWD/tests:/app/tests:ro" -v "$PWD/alembic:/app/alembic:ro" tests pytest -q -p no:cacheprovider tests/test_raid_room_queries.py tests/test_raid_room_foundation.py tests/test_record_timestamps.py
```

공개/private 누출·인증취소·파티장 이전 후 권한상실, 고정정렬/서명/actor/limit/주차·논리만료/타회원 변경 cursor, 실제 가입과 context 연결·변경 후 최종 재검사, 읽기 SQL쓰기/행잠금0·도중 다른 transaction의 한도변경에도 snapshot 일관성, 정확한도/초과·거절/철회/정리 유지, 소유상실·과거 빌드 불변/새버전 stale·metadata 부재, 종료이력/주차·일정·공개방 경계를 검사한다. 기존 F1 원자성·경합·최소ACK와 공통시각/metadata 및 app.openapi 원본일치 시험을 포함한다.

**후보 내부 조회 함수의 구현/격리검증이다.** main 앱 router·원본 OpenAPI·개발 이미지/서버8000·개발DB0016은 변경하지 않았다. 실제 HTTP 입력/헤더·HTTP 권한 검증은 다음 F2-B다. Flutter 적용/실기기·실provider·운영 검증을 의미하지 않는다. 그룹방은 조회/쓰기 adapter 미지원이며 개인목록에서도 해당 관계를 제공하지 않는다. 혼합 그룹 기능 완성이나 기존 사용량 source 활성화로 해석하지 않는다.

## 다음 담당과 완료 조건

Backend F2-B: 후보 router를 격리 앱에 연결해 strict query/body/header·인증·no-store·권한/오류·ACK 후 현재GET과 후보 HTTP schema를 검증한다. 초안 대비 DTO 차이가 있으면 #13에 해당 변경을 명시한다. F3에서는 DB0017+0018/source·main 앱/router·최종 원본 OpenAPI 및 개발 이미지 반영을 같은 검증 구간으로 맞추고 commit/push·원격확인 뒤 필요한 소비 인계를 한다. 현재 Flutter #15 우선은 유지하며 신규 API 테스트를 요청하지 않는다.
