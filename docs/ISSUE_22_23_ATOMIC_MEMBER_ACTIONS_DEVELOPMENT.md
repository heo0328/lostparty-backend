# 개인 완료후 탈퇴·현재/양주차 원자 추방 개발

2026-10-23 / feat/raid-recruitment / #22, #23. 사용자 요청은 선택한 raid만 완료하고 해당 주차에서 실제로 나가는 행동과, 같은 사람을 현재 주차만 또는 두 주차에서 한 번에 내보내는 행동이다. 기존 개인완료/추방 명령과 별도 경로를 둬 기존 원명령·pending·ACK를 보존한다.

소비 기준은 [실행 OpenAPI](../openapi/two-cycle.openapi.yaml)의 아래 4경로와 닫힌 `DepartureContext`, `RemovalContext`, `DepartureCommand`, `RemovalCommand`, `ActionResult`다. [제안1](ISSUE_13_ATOMIC_MEMBER_ACTIONS_DRAFT.md) 및 [#22 Backend 전체2번째 표시 보완](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6361940655), [#23 Backend 전체2번째 review 보완](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6361941083)을 구현한다. 기본116경로/기존두주차170경로와 그 기존 스키마는 객체 전체 대조로 보존하며 새 실행 계약은174경로다. 고정 제안 full.openapi 0.4.1과 cycle_wire 원본은 변경하지 않는다.

| 목적 | GET | POST |
|---|---|---|
| 개인완료후T탈퇴 | `/v2/raid-rooms/{room_id}/personal-completion-departure-context?target_cycle_key=T&round_id=R` | `/v2/raid-rooms/{room_id}/personal-completion-departures` |
| 동일회원추방 | `/v2/raid-rooms/{room_id}/member-removal-context?target_cycle_key=T&target_cycle_member_id=M` | `/v2/raid-rooms/{room_id}/member-removals` |

라우터는 엄격한 입력/인증과 전용 DTO를 연결한다. `atomic_members`의 snapshot builder는 GET의 READ ONLY/REPEATABLE READ와 POST의 최신 검증에서 공용으로 사용한다. `cycles.execute`가 공통 쓰기잠금·한 트랜잭션·원ACK 저장·최종C 경계를 소유하며 중간 commit이나 기존 public 명령 연속호출은 없다. 기존 내부 점유/예약해제·동의종료·제안 재평가를 재사용한다. 신규 테이블/DDL은 없고 DB0030의 ParticipationEvent/Decision/Outcome에 감사근거를 남긴다.

## 개인 완료후 해당T 탈퇴

C/수10시 이후의 본인 participating 실제 CM 및 선택 active Assignment를 검사한다. 선택1개만 manual 완료하고 나머지 본인T active는 left로 끝낸다. 본인T CM은 cancelled가 되며 지속Member, 타인, 기존 완료 및 N의 실제 자료는 보존한다. 완료/취소의 원 Assignment·예약/참여·제출 증거를 감사에 보존하고 투표 이력은 삭제하지 않으며 현재 eligibility/정족수를 재평가한다.

본인이 리더라면 participating이고 남은 active Assignment가 있는 적격후보 중 joined_order→CM UUID 순으로 자동승계한다. 다른 participating/review 관계가 남았는데 후계자가 없으면 permission=false/SUCCESSOR_UNAVAILABLE, confirmation=null로 전체 거절한다. 남는 실제 참가/검토가 없으면 실제 item 완료근거에 따라 T만 completed 또는 cancelled로 닫고 실행리더 두ID를 null로 한다. 기존 완료의 리더는 일괄 재작성하지 않는다. 닫힌 completed/null 리더를 공용 leadership 및 목록 batch reader에서 허용한다. 마지막1인해산 유지는 사용자 확정이며 양T 다인강제해산은 요청 범위가 아니다.

`data.display`는 subject/impact와 동일 관측의 캐릭터·raid/난이도·저장 catalog_version 및 assignment별 complete/cancel/preserve_completed를 제공한다. display_revision은 표시 객체의 서버 SHA-256 식별값이고 별도 plan을 조립하거나 앱에서 hash를 재현할 필요가 없다. 표시 객체 전체가 token에 결합된다. 별도 시점의 이름/난이도를 더해 확인하지 않는다. 앱 의미 비교는 display/impact/subject/leadership/permission을 사용하고 token/issued_at/expires_at만 바뀐 것은 구분한다.

성공은 전용 ACK로 확정한다. 탈퇴 후 member-only plan이403/404여도 실패/재실행으로 바꾸지 않는다. 본인 summary·해당T 목록/상세/예약 근거를 갱신하고 목록 또는 계정 완료 화면으로 이동한다. N의 참가/공대장/일정/동의·제출 자료를 쓰지 않는다. 단, C에 의존하는 공통 open/reopen 등 권한 표시는 이후 조회에서 재계산될 수 있다. N 자료 불변과 파생 권한 표시는 구분한다.

## 현재만/양주차 동일회원 추방

카드의 source 실제T/CM을 고정하며 서버가 지속회원의 실제 user로 반대C/N을 확인한다. 이름/캐릭터 이름으로 연결하지 않고 원 user/소유 정보는 외부에 추가 노출하지 않는다. 다른 캐릭터도 같은회원이면 동일 대상으로 확인한다.

current_only는 source의 실제CM/양수gen·관계/점유 근거가 확정되고 현재 participating 공대장의 기존 자격이 유효하면 target participating 또는 review_required의 정리를 허용한다. source row 자체가 review여도 같은 증명이 가능하면 허용한다. 대상 소유/활동 불일치를 신규 참가자격으로 차단하지 않고 확인 당시 revision/등록·활동·Assignment·lease에 묶는다. 확인 뒤 변경은 stale로 거절한다. 세대/연결/lease를 확정할 수 없으면 ROOM_REVIEW_REQUIRED이고 가짜ID/participating을 만들지 않는다. 필수 source를 구성할 수 없는 Context는409, 구성 가능한 거절은 permission=false/impact=null/confirmation=null이다.

반대 실제관계가 없으면 status=none/target=null이다. review 또는 미확정gen은 status=review_required/target=null, participating이나 호출자actual actor가 없으면 status=participating/target=null이다. 미확정review를 관계없음으로 숨기지 않는다. both는 양T 정상open/participating·각T현재공대장·비공대장target을 모두 요구한다. review→리더권한→대상상태 순 거절이며 review는 ROOM_REVIEW_REQUIRED, 리더권한 없음은 TARGET_LEADER_REQUIRED, 자기/리더대상은 ROOM_REMOVAL_TARGET_INVALID다. 자동승계나 current_only/옛API fallback은 없다.

option별 별도 token을 발급한다. current_only의 의미/hiddenCAS는 source와 선택impact만 결합하고 반대T의 무관한 변화로 재확인을 강제하지 않는다. both는 두T 증명을 모두 확인한 뒤 첫 mutation을 시작한다. 중간 실패·감사 실패·최종시각 변경이면 두T 모두 rollback한다. 완료Assignment/주간완료·지속Member는 보존한다. ACK의 source첫순 effects/affected_cycle_keys가 가리키는 T만 무효화하며 타기기 push 전달을 새로 보장하지 않는다.

## 공통 복구·입력

GET은 쓰기·Key/pending/원장 생성 없이 반복 조회한다. POST는 UUID4 Key와 정확한 원본문/token을 보존한다. 정상인증과 입력/Key·body 검증 뒤 기존 원ACK24시간 복구가 새 권한·탈퇴·승계·token 만료·주차 검사보다 앞선다. 같은Key 다른본문 IDEMPOTENCY_CONFLICT, 진행중 REQUEST_IN_PROGRESS/Retry-After2, 만료 IDEMPOTENCY_EXPIRED는 공통 구현을 따른다.

새 실행 token은 actor/flow/room/본문·실제T/세대/권한/소유·plan/리더십·선택효과 및 표시 관측을 결합한다. 최대4096 UTF-8 bytes,120초/C종료 중 이른 만료이며 새 실행의 마지막에도 C/만료/개인playable를 검사한다. explicit CAS 변경은 REVISION_CONFLICT, hidden 변경 TARGET_CONTEXT_STALE, 본문/token 불일치는 CONTEXT_INVALID다. no-store·요청32KiB·응답1MiB·중복/추가query·중복JSON 키·추가필드 거절을 유지한다.

## 검증·게시·개발 상태

최종 검증 및 소비 SHA·원격 게시·실제 개발 반영 근거는 아래 확정 기록으로 갱신한다. Backend 구현/격리 시험과 Flutter 연결/실회원·기기 인수는 구분한다. 운영 배포·dev/main 통합·실회원 쓰기는 이번 작업의 완료로 간주하지 않는다.

최종 결과: **고유39 PASS = 신규33 + 기존회귀6**. 신규29/362.46초 → 등록/동시성/추방HTTP 추가3·개인탈퇴재확인2·기존회귀6의11/144.64초 → N source추가1·개인탈퇴재확인2의3/44.02초다. 뒤 두 묶음의 신규4개 외 재확인4개는 고유수에 중복 합산하지 않는다. 초기 날짜 직렬화/GET query 선언·보존시험의 파생권한 비교 오류는 수정 후 검증했고 실패를 통과로 합산하지 않는다. 격리 HTTP는 합성 principal 주입이며 실제 회원 인증·기기 인수와 구분한다.

[합성 실행 예시](design/issue22-23-atomic-member-actions.examples.json)는17개 그룹·실제 캡처응답33개/요청9개이고 게시 OpenAPI/format checker **42개 검증 PASS**다. token은 검증 후 `<opaque-redacted>`로 가렸다. 일반탈퇴/승계·후계없음·마지막완료/불완료/null리더·rollover원ACK, 반대none/actor없음/review/미확정gen/권한없음/target리더, source review 허용/불안전lease거절, source N의N,C 순 ACK를 포함한다.

개발 API8000은 `sha256:92490ff3bf3e777d6342cb7a416af042ccf6654f8429c37a8a7cfd2796d71352`로 교체했고 app/alembic **230개 Python 파일이 현재 소스와 바이트 일치**한다. 기존 이미지는 `lostparty-backend-api:pre-atomic-members`로 보존한다. 두 OpenAPI 객체전체 일치·DB0030 준비검사/health200·새4경로 무인증/잘못된Bearer **8개401/ACCESS_INVALID·no-store/WWW-Authenticate PASS**다. 정상 실회원 HTTP/실회원 쓰기는 수행하지 않았다.

교체 직전/직후 **106표476행의 전체내용 지문·열정의·DB0030·환경/키mount/포트/보안/command 지문 동일**이다. DB 재시작·migration·삭제/초기화·키변경 없음, 이번 임시 시험runner/tmpfs DB/network만 정리했고 기존 API/DB 두 컨테이너 healthy다. 운영·dev/main 병합이나 Flutter 적용/실기기·성능 인수 완료가 아니다. 구현 구간을 commit/push·원격확인한 뒤 #22/#23에 소비SHA/고정링크로 인계한다.
