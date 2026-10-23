> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [membership-actions](../../../../../features/recruitment/membership-actions/README.md) · [completion-and-records](../../../../../features/recruitment/completion-and-records/README.md) · [search](../../../../../features/recruitment/search/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 검색 제외·일반 탈퇴/해산 구현

2026-10-24 / `feat/raid-recruitment` / #24·#25. 사용자 구현 진행 지시와 [#24 전체3번째 Flutter 계약 수용](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6370137482), [#25 전체5번째 Flutter 네 차이 해소](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6370138718)를 기준으로 한다. 원본 정책은 #13 전체135·136번째이고 [보완안2](../contracts/ISSUE_25_CONTRACT_REVIEW_V2.md)와 [검색 계약](../contracts/ISSUE_24_SEARCH_CONTRACT.md)의 wire를 구현한다.

현재 **소스 구현·격리 검증·실제 개발 API/DB0031 반영 완료**다. 실행176경로/기본116 계약 전체 일치·기존106표603행 보존/2표 추가·health/인증 경계를 확인했다. [실제 전환 결과와 미확인 범위](ISSUE_24_25_DEVELOPMENT_ROLLOUT.md)를 따른다. 실회원 명령·기기 인수는 다음 Flutter 단계이며 운영·dev/main은 유지한다.

## API와 저장 책임

- POST `/v2/raid-rooms/search` 및 기존 GET adapter: 로그인 호출자의 선택 실제T/현 generation CM participating/review와 활성 지속회원이 일치하면 SQL NOT EXISTS로 정렬/offset/limit+1 전에 제외한다. 반대T만 참가·미결 신청·단순 지속/종료 관계와 비로그인은 구분한다. 요청/응답/필터/전체 인원 집계는 유지한다. cursor digest에 `own-target-participation-excluded-v1`을 포함해 옛 의미/head 변경은 CURSOR_STALE409, 외부 scope/위조는 INVALID_REQUEST400으로 처리한다.
- GET `/v2/raid-rooms/{room_id}/membership-action-context?target_cycle_key=T`: 활성 지속회원이 메뉴 입구다. 실제 참가·리더·복구 조건은 옵션마다 검사해 현재T 미참가/일반이어도 반대T 해산·모두탈퇴를 읽을 수 있다. 거절 옵션의 impact/confirmation은 null이다. GET은 자료/권한을 변경하지 않는다.
- POST `/v2/raid-rooms/{room_id}/membership-actions`: 합의한 6필드와 선택 옵션 token만 받는다. leave_target/leave_all/dissolve_led_targets/recover_leadership의 전용 불변 Context/ACK와 실제 C→N 순서를 사용한다. 기존 cancel/leave/end·D22/E23 transport·namespace·원 효과/24h ACK와 분리한다.
- 기존 detail/plan/내참가 목록에 `reader_profile=membership-actions-1`을 명시하면 target/viewer/recovery/permission·legacy content/본인 record를 분리한다. profile 생략 시 기존 DTO를 유지하고 미지원/오타 profile·반쪽 기록 anchor는400이다. profile은 cursor scope에 결합한다.
- 종료 기록은 본인 membership_id+cycle_member_id의 정확한 관계를 확인한 후 읽는다. 타인/다른 방·T의 anchor는404이며, 그룹 탈퇴 후에도 그 본인 기록만 읽을 수 있다. 새 Member·새 참가를 쓰기 권한으로 섞지 않는다. 다른 과거 회원의 private 자료는 반환하지 않는다.

`membership_actions`의 planner를 GET의 READ ONLY/REPEATABLE READ와 POST의 최신 검증에서 공유한다. `cycles.execute`가 공통 game-mutations 잠금·단일 트랜잭션·원 ACK 저장·최종 C/만료 확인을 소유한다. 선택 옵션의 모든 before/권한/대상 집합을 확인한 뒤 실제 자료를 변경한다. 기존 public 명령을 연속 호출하지 않는다.

자기 탈퇴는 실제 source/점유 정리가 증명되면 후계자의 부적격 때문에 막지 않는다. 실제 순서/자격의 후계가 있으면 승계하며, 없으면 탈퇴 후 review/null 리더·명시 복구 상태를 남긴다. 복구는 POST로 자격을 재검사하고 다른 검토가 남으면 review를 유지한다. 다중 주차 해산은 본인이 실제 리더인 모든 유효T를 묶고 다인·8인을 지원하며 비대상T를 보존한다. Room 종료는 미정/다른 live T나 미정리 active Assignment가 없을 때만 수행한다. effects=[]의 순수 지속관계 종료는 가짜T를 만들지 않는다.

room/Member/CM/members/leadership은 합의한 유지·명령당 1회 증가 규칙을 적용한다. target/plan은 내부 일정·정족수 재평가의 엄격 증가 규칙을 사용한다. 완료 Assignment/원 완료 근거를 지우거나 새 완료로 덮지 않는다. 실제 영향T directory와 관련 회원 목록·한도 head를 갱신한다.

## 0031 이행과 기록 식별자

추가 migration `0031_membership_actions`는 명시 리더 복구 상태와 불변 명령 감사의 두 표를 추가한다. 감사표 UPDATE/DELETE는 기존 불변 보호 함수로 막고 기록 시각 trigger를 설치한다. 기존 행/키·완료/예약·제출/동의·감사 이력을 초기화하거나 backfill하지 않는다.

같은 지속회원의 선택T 탈퇴 후 재참가에서도 옛 기록 식별자가 새 쓰기 권한으로 재사용되면 안 된다. 0031은 CM의 `(cycle,generation,membership)` 전체 unique를 **현재/retained 상태의 partial unique**로 바꾸고 Assignment의 `(round,membership)`도 현재/retained 상태의 partial unique로 바꾼다. 새 일반 명령으로 종료된 CM은 보존하고 재참가 시 새 CM/Assignment·가입순번을 발급한다. 기존 구 명령으로 종료한 CM의 기존 재참가 규칙은 보존한다. 현재 조회는 현재 CM을 선택하고 완료 정리는 옛 cancelled/removed CM을 재작성하지 않는다. 종료 시 자기 일정 segment snapshot도 감사 증거에 저장해 재참가 후 재사용된 일정 참여와 섞지 않는다. API에 임의 새 anchor 필드는 추가하지 않는다.

이행은 기존 행을 바꾸지 않는 제약 교체와 표 추가지만 **기존 개발 DB에 자동 실행하지 않았다**. 준비된 0031 호환 API·worker/readiness와 함께 별도 반영해야 한다. 복구 대기 T는 다음 주차 만료 시 자료/완료를 보존하며 종료하고 GET/worker가 자동 리더를 배정하지 않는다.

## 검증·인계

최종 코드의 고유38개가 분할 실행으로 통과했다(신규21·검색11·기존 회귀6). 합의 설계37벡터의 구현 DTO 정적 검증과 [합성 DB 실행 응답7개](../../../../../features/recruitment/membership-actions/examples/membership-actions-implementation.json)의 closed schema 대조도 통과했다. 후보 API 실제 ASGI 시작/health200·인증거절3건/no-store와 기본116·후보176 OpenAPI 전체 일치를 확인했다. 후보 이미지의 app Python203개가 소스와 일치한다.

구체 실행 결과와 소스 SHA/원격 게시·댓글 링크는 [DEV_LOG](../../../../../project/DEV_LOG.md), 다음 담당은 [NEXT_WORK](../../../../../project/NEXT_WORK.md)를 따른다. 시험은 임시 tmpfs PostgreSQL·비관리자 LOGIN·합성 계정/키로 수행하며 실제 회원·기기/운영 시험이 아니다. 실행 OpenAPI는 기존 component 전체를 보존한 176경로이고 기본116경로와 고정 설계0.4.1 원본은 유지한다.

Flutter는 게시된 source/실행 계약으로 전용 DTO·원 명령/ACK → 실제 메뉴·성공 화면·관계 종료 알림 → profile/기록 Router를 연결할 수 있다. 실 개발 서버 연동은 API/DB0031 반영 확인 후 수행한다. effects=[]의 관계 종료는 C/N 내목록·한도 별도 무효화, 비대상T 해산은 현재 화면 유지, 대상T 탈퇴는 성공1회 이탈이다. 후속 GET403/404·refresh 실패를 쓰기 실패로 되돌리지 않는다.

[IF-001](../../../../../features/recruitment/completion-and-records/inactive-features.md)에 따라 close_weekly/weekly_resume 앱 신규 진입은 비활성 보존이다. endpoint/서버 권한·과거 stopped/완료·원 pending/ACK를 삭제하거나 재해석하지 않으며 retained 자료를 읽었다고 앱 기능을 다시 켜지 않는다. 다음주 reopen과 #25 recover_leadership은 별개다. 복구 UX는 여전히 제품 승인 전 제안이다.

retained/stopped의 `resume_weekly`는 기존 서버의 source/권한 검사 결과를 그대로 반영한다. IF-001 앱 진입 비활성은 별도 제품 상태이며 이 권한 필드를 일괄 false로 바꾸는 근거가 아니다. 조회는 기존 준비 검사만 재사용하고 재개 제안/명령을 생성하지 않는다.
