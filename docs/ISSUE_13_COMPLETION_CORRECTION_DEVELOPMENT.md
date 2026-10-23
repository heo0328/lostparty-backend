# Issue #13 — 본인 완료 정정·완료 방 보관 개발 인계

Flutter [전체127번째 계약 수용/최종 wire 요청](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6358680312)을 기준으로 구현한다. [제안1](ISSUE_13_COMPLETION_CORRECTION_LIFECYCLE_DRAFT.md)과 아래 실제 wire 경계를 함께 따른다. 게시 SHA·검증·개발반영 결과는 문서 끝에 기록한다. 구현 소비는 해당 구간 최종 push SHA로 고정한다.

## 새 정정 경로·확인/결과

정확한 schema는 [실행 OpenAPI](../openapi/two-cycle.openapi.yaml)의 `CorrectionContext`, `CorrectionCommand`, `CorrectionResult` 및 참조 객체다. 기존 168경로에 아래 2개를 추가해 170경로이며 기존 manual·summary required/type·기존 body/hash를 변경하지 않는다. 기본0023 OpenAPI와 고정 0.4.1 wire는 보존한다. 런타임 확장 schema revision은 `0030_completion_corrections`, policy는 `two-cycle-contract-4`다.

- GET `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-correction-context?target_cycle_key=T`
- POST `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-corrections`, UUID4 Idempotency-Key 필수

닫힌 객체이며 명시null/생략 필드·추가필드를 추정하지 않는다. 실제 과거T도 읽을 수 있으므로 최상위는 기존 C/N `scope` 대신 `{server_now,current_cycle_key,data}`다. 모든 시각은 offset ISO datetime. 현재C는 수06시 기준이며 context.issued_at=server_now, expires_at은 그 시각+최대120초와 현재C 종료 중 이른 값이다.

Context.data는 `character_id,raid_id,target_cycle_key,weekly_revision,ownership_revision,lifecycle_revision,completion_sources,permission,confirmation`이다. sources는 기존 SummaryCompletionSource의 닫힌 객체 최대2개(manual→party 순), 권한은 `{allowed,reason,next_change_at}`다.

- 본인 완료 source가 있으면 allowed=true/reason=null/next_change_at=null 및 confirmation=`{context_token,issued_at,expires_at}`.
- 현재 소유/등록 범위를 확인한 뒤 완료 source가 없으면 sources=[]/allowed=false/reason=COMPLETION_NOT_FOUND/next_change_at=null/confirmation=null. 이 응답을 성공 정정으로 표시하지 않는다.
- 소유 불가/세션 오류·미래T/입력 오류는 에러 HTTP이며 성공 객체에 임의 permission/confirmation을 채우지 않는다. 복수source 중 일부만 해제하는 명령이 아니다.

Command는 `target_cycle_key,expected_cycle_key,expected_weekly_revision,expected_ownership_revision,expected_lifecycle_revision,correction_context_token`만 required다. expected_cycle_key는 읽은 현재C, target은 실제 정정T다. token 최대4096 UTF-8 bytes, 전체 요청32KiB 초과413. Key/pending은 POST 제출에만 생성한다. 같은 확인의 본문/T/권한이 바뀌면 쓰기 없이 새 context로 재확인한다.

Result.data는 `command_id,outcome='applied',correction_id,character_id,raid_id,target_cycle_key,weekly_revision,completion_sources=[],participation_restored=false`다. command_id는 요청Key, correction_id는 감사 UUID, revision은 정확히1 증가한다. 방 Ack로 캐스팅하지 않는다.

### ACK·오류·주차 전환

원 method/path/body/key/token을 결과불명 재송에 보존한다. 성공 후24시간 동안 같은 유효회원세션의 동일 명령은 당시 ACK 전체(당시 server_now/currentC/targetT 포함)를 반환하고 새 source를 지우지 않는다. 주차가 바뀌어도 **원pending에 기록한 T/C와 원명령**을 대조하며 현재C를 원ACK 필드에 덮어씌우지 않는다. 그 후 현재T 재조회는 별도 읽기다. 오래된 성공 ACK의 존재를 새 완료가 현재도 해제됐다는 뜻으로 사용하지 않는다.

기존 공통 원장은 `IDEMPOTENCY_CONFLICT409`(같은key/다른본문), `REQUEST_IN_PROGRESS409`/Retry-After2초(진행중), `IDEMPOTENCY_EXPIRED409`(24시간초과)다. 24시간을 넘긴 불명명령은 자동 새key 재취소 없이 현재 실제T context로 상태 확인한다.

실행 순서는 라우터 엄격입력/현재인증·공통Key와본문→원성공ACK→현재소유/대상T→expected C/세revision→token actor/flow/character/raid/T·만료/currentC/source digest→완료 존재→투영/감사/ACK 원자적 저장→최종C/만료 검사다. 일반명령과 마찬가지로 auth/input 검사는 원ACK에서도 생략하지 않는다.

`INVALID_REQUEST400` 형식/미래T, `CONTEXT_INVALID400` 변조/대상·actor·flow, `CYCLE_CHANGED409`, `REVISION_CONFLICT409`, `COMMAND_CONTEXT_EXPIRED409`, `COMPLETION_CONTEXT_CHANGED409`, `COMPLETION_NOT_FOUND409`를 구분한다. 현재 기록 없음+예전token이면 revision/context 오류가 먼저 나올 수 있다. 기존 source가 현재 revision 변화 없이 바뀐 경우에도 digest로 거절한다. 정상인증/소유 비노출 오류는 기존401/403/404, DB/런타임 미준비는503이다.

### 소유·시각·감사 경계

- 실제T<=현재C의 정규 수요일 날짜만 허용한다. 과거T 만료 제한 없음/현재C 수06~10시 취소 가능. 새 완료 생성의 기존 C/수10시 제한은 유지한다.
- 현재 등록/Account소유·검증과 본인 user_id의 WeeklyState·ownership/lifecycle revision을 확인한다. 비활성/은퇴 캐릭터와 현재 비활성·삭제된 카탈로그raid도 본인 저장 완료가 있으면 정정할 수 있다. 이름 재사용/타인/소유이전 자료를 연결하지 않는다. 이 전용경로의 기록 권한을 다른 쓰기 권한에 재사용하지 않는다.
- WeeklyState의 현재 manual/party 투영만 함께 비운다. 별도 `raid_completion_corrections` 불변 감사에 전source/전후revision·actor/command/실제T를 남긴다. 기존 Outcome/완료 Assignment/Round/다른회원·N/원ACK는 보존한다.
- 공통 쓰기 잠금·CAS로 완료/참가와 직렬화한다. source가 먼저 바뀌면 예전확인은 거절, 정정이 먼저면 예전weekly revision 명령은 거절된다. 새 완료가 나중에 생기면 새 source로 읽으며 과거정정이 영구 억제하지 않는다.
- 참가/좌석/방/점유·동의/예약 자동복원은 없다. 완료한 방의 당시 사실/논리보관은 그대로다. 현재T summary(과거T는 새context) 재조회 실패가 ACK성공/pending해제를 되돌리지 않는다.

## 선택T current/ended/all과 복구용 nullable

`current`는 SQL pagination 전에 지속Member 미종료·Room미종료/미보관·선택T open/review_required·실제 현재 generation CycleMember participating/review_required를 검사한다. 지속관계만 있고 T미선택인 관계, completed/stopped/cancelled/removed는 제외한다. 단순legacy_intent로 실제참가를 만들지 않는다.

`ended`는 기존 지속관계종료 또는 방종료/보관 또는 실제T completed/stopped/cancelled/removed 근거를 포함한다. 단순 not_selected는 all에만 남긴다. 기존 wire에 removed enum이 없으므로 실제 removed 관계는 목록 target_participation_state=cancelled로 표현하고 실제 CycleMember ID/revision을 유지한다(새 enum 추가 없음). `all`은 기존자료를 보존한다. row.state/history_only는 지속관계 의미를 보존하므로 ended query 안에도 row.state=current/history_only=false·target_participation_state=completed 조합이 가능하다. 이것을 활성참가로 재분류하지 않는다.

Flutter127의 nullable 질문은 다음 형태로 확정한다.

| 형태 | 정확한 결합 |
|---|---|
| 명시 generation 있는 review | 실제 room/card·room_cycle_id·양수 target_generation/revision·실제 cycle_member_id/revision. target_participation_state=review_required. room.target_state도 review_required 가능. 기존 schema대로 읽고 open만 허용해 숨기지 않음 |
| generation 미확정 + 실제 review 관계 | room=null, recovery_only=true, assignments=[], target_role=none, target_generation=null, joined_order=null. **room_cycle_id/target_revision은 실제 값, cycle_member_id/revision도 실제 review 관계 값**. permission.view_plan=false/ROOM_REVIEW_REQUIRED. 가짜 card/gen/리더/좌석 없음 |
| 선택T 실제관계 없음 | current에서 제외. all에서 기존 room/card 또는 null·cycle_member_id/revision null·not_selected를 유지 |

null-card 복구 행은 활성 방 카드로 꾸미지 않고 별도 복구/안내 행으로 보존할 수 있다. 기존 room/card parser에 가짜 양수gen을 넣지 않는다. 실제 자료를 확인할 수 없는 detail/plan 실행은 기존 ROOM_REVIEW_REQUIRED409다.

## 보관방 기록 조회·permission/access·N 보존

전raid 완료는 explicit 현재 generation의 completed 상태와 모든 현재 item Round/실제완료Assignment 근거를 확인한다. 개인완료들로 Round active여도 더 이상 active/stopped_incomplete Assignment가 없고 실제 완료근거가 있어야 한다. 빈방/일부완료/stopped/legacy를 전완료로 추정하지 않는다.

이후 열린 실제주차(open/review_required) 또는 미완료 stopped 주차가 있으면 보관하지 않는다. 열린N은 C완료와 별개로 모든 ID/참가/리더/일정·동의를 유지한다. N취소/최종완료로 보관이 성립하면 관련 디렉터리 cursor를 무효화한다. GET은 보관상태/자료를 쓰지 않고 기존완료방에도 같은 판정을 적용한다.

| 실제 경로 | 보관방 소비 |
|---|---|
| GET `/v2/raid-rooms/{id}` | 공개카드 ROOM_NOT_FOUND404. 이 응답으로 아래 회원기록 접근까지 차단하지 않음 |
| GET `/v2/raid-rooms/{id}/detail?target_cycle_key=T` | 현재 지속회원 검증 후 기존 기록 DTO200. room.state=ended/phase=ended, room.target_state=completed·실제 양수cycle/gen/revision·기존 leadership/my_target_role 유지. access.state=allowed/정상 policy_snapshot/evaluated_at/issues=[]와 view_detail/view_plan의 기존회원권한은 유지. settings의 쓰기permissions는 false/ROOM_NOT_ACTIVE |
| GET `/v2/me/raid-rooms/{id}/plan?target_cycle_key=T` | 기존 회원·실제CycleMember 확인 후 기록 DTO200. target_state=completed·실제UUID/양수generation·원leadership/완료Assignment·formation_history 보존. 최상위 data.permissions 쓰기/command-context 진입은 false/ROOM_NOT_ACTIVE. 가짜 nullleader/세대 없음 |

기록조회는 기존 C/N 경계 안이다. 보관은 새 과거방 전체이력 API가 아니다. 직접 상세는 비회원에게 보관방 개인정보를 추가 공개하지 않으며 기존 권한 오류를 반환한다. 지속회원이 이미 명시탈퇴한 경우의 기록조회 권한을 새로 부여하지 않는다.

보관방의 새 참가/편집/일정/리더이전/N개방·현재주재개 쓰기는 공통 envelope의 room/round/session/proposal/group/application 실제 소속을 확인해 ROOM_NOT_ACTIVE409로 막는다. 기존 원명령 ACK 복구는 그보다 먼저 수행하고 새 본인 완료정정은 방쓰기와 독립이다. 보관 이후 N개방은 새방 생성 안내, N개방이 먼저 확정됐으면 C완료로 N을 없애지 않는다. stopped 불완료 방은 보관조건과 구분하며 all/ended·기록상세에서 기존 재개 경로를 유지한다.

## 실제 합성 응답 예시

[실행 예시8개](design/issue13-completion-correction.examples.json)는 합성계정/격리DB 실행 결과이며 token만 `<opaque-redacted>`로 치환했다. 실제 회원 원본/인증정보가 아니다. 정상/완료없음context·새명령/ACK·명시세대review·미확정세대review·보관회원 detail/plan을 포함한다. 최종 런타임 닫힌 OpenAPI의 format/null/required를 JSON Schema로 대조한다.

## 검증·게시·실행 기록

최종 관련 **고유42PASS(신규26/기존회귀16)**다. 42개 묶음은41PASS/1실패·516.99초였고, 실패는 합의 전의 current/not_selected 노출을 기대한 기존 시험이었다. 새 contract에 맞춰 current/ended 제외·all 보존 기대값을 수정하고 최종 가시성 guard·생성/보관/nullable 경계와 함께 **5PASS/56.63초**로 재확인했다(이전 묶음과 중복4 제외 고유42). 탐색24PASS/312.64초와 중간 재실행을 합산하거나42개 단일실행 성공으로 표현하지 않는다. 기존 anyio deprecation warning1종, 최종 미해결 실패 없음이다.

수동/party/둘다 원자적 해제·불변 감사/기존완료Assignment·타인보존, 실제수06~10시/과거T·은퇴기록, 권한/변조/CAS/출처변경/만료/최종만료·rollover rollback·감사실패·동일명령경합/원ACK·새source 재생성, 합성 실제Bearer/타인·폐기세션/32KiB·no-store, 개인완료전raid/N보존·보관기록/현재목록·새개방차단/원ACK·복구용 두nullable 형태를 검증했다. 기존 생성/참가/신청·목록/C/N·manual·완료/종료/재개·제안/표/plan을 직접 회귀했다. 합성 예시8개의 최종 closed OpenAPI JSON Schema/format 검증도 통과했다.

검증 API 이미지 `sha256:13291847b6ec78a6fdaa33d334128d6bf59d775d784f0dc7752491d3ef5a4519`의 app/alembic Python228파일이 작업 소스와 바이트일치한다. 실제 개발API8000을 해당 이미지/two-cycle factory로 교체하고 `alembic upgrade 0030_completion_corrections`를 적용했다. 실제 기존104개 업무표430행의 모든 내용/열정의·실행환경/키mount/포트/보안/command 지문이 전후 일치하고 새 감사표는0행이다(총106표431행, version행 포함). DB 재시작·기존회원행갱신/삭제·키교체/실회원 명령은 하지 않았다. 실제 직전 baseline을 사용하며 이전344행 기록을 재사용하지 않는다. 직전0029 API는 `lostparty-backend-api:pre-completion-correction` 태그로 보존하지만0030에 구전용이미지를 그대로 실행하는 rollback은 하지 않는다. 합성 시험/실제 정상로그인 HTTP·실기기·운영 인수는 분리한다. 실회원/실기기 전체·성능 인수, dev/main 통합·운영배포는 이 인계의 완료 의미가 아니다.

Migration `0030_completion_corrections`는 새 `raid_completion_corrections` 감사표와 불변/기록시각 trigger만 추가한다. 기존 업무표의 행 갱신·삭제·초기화나 과거 완료 근거 재작성은 없다. DB0029/0030을 명시 호환하며 새 정정 기능은0030에서만 활성화한다. rollback 명목으로 감사표를 지우거나 구0029전용 이미지로0030을 실행하지 않는다.


실제 개발 API의 기본116/두주차170 OpenAPI 각 전체 객체 일치, 런타임 모델을 등록한 API 제한역할의 DB0030 전체 readiness 통과다. 실제 health200·새2경로 무인증/오류Bearer401·no-store/WWW-Authenticate4검사를 확인했다. 이 검사는 정상로그인 실회원 HTTP 성공·기기 쓰기 검증이 아니며 해당 인수는 미확인이다. 이번 합성DB/runner/network는 정리해 기존 API/DB만 healthy로 남겼다.

현재C 수06~10시와 과거T를 각각 명시하는 시각시험 보강 뒤 **2PASS/30.18초**도 재확인했다(기존고유42에 포함된 중복2, 합산 없음). 최종 app/migration 바이트는 동일하고 추가 시험용 tmpfs 환경도 정리했다.

최종 소비 SHA `8bbcfc8cb89e69eb1f9747a0fcf2e919e41c3b76` / feat/raid-recruitment commit/push·원격SHA일치 확인. [전체129번째 Backend · 완료정정/보관 구현·개발반영·소비인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360251618) 전문/본문제외실제댓글순번 확인 완료다. 다음Flutter는 새 DTO/정정writer·원pending schema호환/권한·원ACK/실제T 재조회·review/목록/회원기록 직접진입 차이를 연결해 사용SHA/결과를회신한다. 같은 정책/기존mock 반복 요청 없음, Backend는 재현 차이 대응이다.
