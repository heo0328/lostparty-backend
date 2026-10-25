# 베타 모집 계약 고정안2 — 완결 wire와 호환 경계

2026-10-25 / `beta-recruitment-wire-2` / profile `beta-recruitment-1`.

[#13 전체149 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6393878499)의 조건부 수용에 대한 Backend 고정안이다. [정책/트랜잭션 원문](beta-contract-proposal.md)을 보완한다. 이번 완료 조건은 네이티브가 전체 envelope를 소비하고 잔여 차이를 확인할 수 있는 계약 인계다. **양측 최종합의·실행 구현·개발 반영은 아직 아니다.** 현재 실행 OpenAPI/서비스/DB는 변경하지 않았다.


공식 회신: [전체150번째 Backend · 계약 고정안2](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6394448231) / 다음 Flutter 잔여차이·최종합의 확인 대기. 고정SHA/원격 게시 상태는 같은 회신에 기록한다.

후속 상태: [전체151](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6394870853)에서 계약을 최종 수용했다. [Backend 구현/격리검증](beta-implementation.md)·[전체153 Backend · 베타 구현/격리검증](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6395894539)로 이어진다. 위 인계 당시의 미구현/합의대기 설명과 현재 소스/실제반영 상태를 구분한다.

## 소비 원본과 재현

- [완결 wire JSON](proposals/beta-recruitment-v2.wire.json): `operations`에 method/path, 전체 path/query/header, requestBody, 성공/오류 response schema·header, security, 구버전 처리분류와 추가 오류를 제공한다. `$defs`는 해당 operation의 참조 전체를 포함한다. 외부 base 문서와 수동으로 DTO를 합칠 필요가 없다. 실행 OpenAPI가 아닌 **제안 전용 bundle**이다.
- [완결 본문 예시](proposals/beta-recruitment-v2.wire-examples.json): operation index와 전체 parameters/본문이 있다. 합성 구조 자료이며 서버에서 관측한 응답·업무 성공 자료가 아니다. 권한문맥을 붙인 actual-T 참가자/자기 pending/리더 review와 record content=null 예시를 포함한다. 예시의 token/ID/표시값은 가상 자료다.
- [신규 component/시간 사례](proposals/beta-recruitment-v1.schema.json)·[문자/시간 벡터](proposals/beta-recruitment-v1.examples.json): 파일명의 v1은 최초 경로 보존이며 현재 내용은 고정안2다. 종전 emoji 허용/EGC 제안은 폐기했다.

```sh
python3 docs/features/recruitment/weekly-cycles/tools/build-beta-wire.py --check
python3 docs/features/recruitment/weekly-cycles/tools/validate-beta-proposal.py
python3 docs/features/recruitment/weekly-cycles/tools/validate-beta-wire.py
```

현재 계약66 operations·완결118 fixture(요청35/성공본문75/오류본문8), 기존 ACK32 operation 동일성·잘못된 metadata 위치3건 거절을 정적으로 확인한다. 별도로 시간/DTO48사례와 문자25벡터를 실행한다. fixture들은 전체 필수구조/nullable/닫힌키 소비를 확인하며 서버의 권한·트랜잭션·시간 경합을 실행한 시험이 아니다. HTTP 기대9사례/DB/Flutter 런타임/실회원·기기는 미실행이다.

## profile 전달과 reader 조합

bundle의 **기존64 operations + 신규 presets GET/PUT 2개 = 66 operations**를 기준으로 한다. 아래 operation 목록이 전체 전달 목록이다. 향후 구현에서는 기존 operation에도 `contract_profile=beta-recruitment-1`을 명시한다. 새 presets 두 경로는 profile/실제T를 받지 않는다. 목록 밖 API, 특히 로그인·개인표 원본 GET/PUT에 profile을 임의 전달하지 않는다.

`contract_profile`은 버전 선택, `reader_profile`은 기존 조회 목적 선택이다. 하나의 query key에 둘을 섞지 않는다. reader_profile 두 값을 동시에 보내거나 쉼표로 합치지 않는다.

| 조회 | 허용 reader_profile | 메타데이터 층 |
|---|---|---|
| GET detail | 생략 / application-display-1 / membership-actions-1 | 기본·application-display는 data. membership-actions는 바깥 data와 실제 content.data |
| GET me/.../plan | 생략 / membership-actions-1 | 기본 data. membership-actions는 바깥 data와 실제 content.data |
| GET room/.../applications | 생략 / application-display-1 | data.items[*] |
| GET me/raid-room-memberships | 생략 / membership-actions-1 | data.items[*]; membership-actions의 기존 content nullable 유지 |
| GET application 단건/review, me/raid-room-applications | 생략만 | 본인 단건 data, 리더 review data.application, 목록 data.items[*] |
| 나머지 | 기존에 허용하지 않은 reader_profile은400 | bundle에 기재한 기존 구조 |

membership_id/cycle_member_id는 membership-actions detail/plan에서만 기존 의미로 허용한다. include_session_display와 include_resume_display는 기존 허용 경로/선택성을 유지한다. beta profile을 썼다는 이유로 session_display를 강제하거나 reader 전체를 전역 완화하지 않는다. candidates(캐릭터/일정)·review도 profile을 전달해 같은 정책과 대상 revision을 사용하지만 불필요한 identity/memo를 추가하지 않는다.

명시되지 않은 query·중복 singleton query·GET body는400 INVALID_REQUEST다. 기존 GET raid-rooms의 반복 experience_levels는 기존 예외대로 유지한다. 새 GET 검색 필터 departure_windows/schedule_states는 각각 **하나의 URL-encoded JSON 배열 query**다. 중복 key/빈 배열/null은 거절한다. POST 검색은 같은 이름의 JSON 배열 body다. base_starts_at은 timezone이 있는 UTC RFC3339 값이며 전송 Z로 통일한다. 생성 context의 OFF에는 early_additional_members를 생략하고 POST의 OFF에는 null을 보낸다. next_*는 실제 C+N 동시생성만 허용하며 N단독은 전송하지 않는다.

## 새 필드의 정확한 위치와 null

`Beta_` DTO들은 원 closed DTO를 바꾸지 않고 별도로 정의했다. 기존 필수필드를 생략한 부분 envelope를 응답으로 쓰지 않는다. 신규 읽기 metadata는 해당 beta DTO의 **필수 key**이며 대상 없음은 아래 nullable 규칙을 따른다.

| 자원/층 | 추가 필드·의미 |
|---|---|
| 생성 context data | beta_schedule_targets: 실제 생성될 T별 config 배열. 아직 저장 session이 없으므로 BetaScheduleView를 꾸미지 않음 |
| opening context data | beta_schedule_config: 새로 개방할 T의 config. opening POST beta_schedule 필수. open/reopen 모두 새 개방 명령이며 이미 열린 대상은 기존 거절/원ACK 유지 |
| 카드 data, 검색 data.items[*], 상세 data 및 그 room, plan data, schedule-context data, admission/continuation context data | beta_schedule: 실제 T의 BetaScheduleView 또는 legacy null |
| 내 참가목록 data.items[*], 내 신청/리더 신청목록 data.items[*], application 단건 data, review data 및 data.application | beta_schedule: 그 항목의 실제 T. legacy/권한상 현재자료 제공불가면 null |
| membership-actions detail/plan 바깥 data | beta_schedule, recruitment_identity. content가 있으면 content.data의 동일값과 일치. content=null인 기록전용/관계전용은 둘 다 null |
| membership-actions 참가목록 data.items[*] | beta_schedule. content=null이면 null. content.room에 secret을 추가하지 않음 |
| 상세/plan data | recruitment_identity:{number,password} 또는 객체 전체 null. public 카드/검색/내참가목록/ACK/기록에는 key 자체를 추가하지 않음 |
| availability-submission data와 schedule-context data.members[*].submission | availability_copy: 복사 상태/원개인표버전/복사시각 또는 legacy 미복사 null. 실패를 unset으로 치환하지 않음 |
| 본인 신청 단건 data, 리더 review data.application, 신청목록 data.items[*], application-display 상세 data.my_application | application_memo:string 또는 null. my_application이 null이면 객체를 새로 만들지 않음 |

identity는 요청T/current generation의 **현재 participating CM + 현재 활성 membership + 최신 접근권한**을 모두 만족할 때만 제공한다. leader/member 모두 동일하고 pending·반대T만참가·review_required/취소/추방/완료/과거기록에는 객체 전체 null이다. 이미 종료된 방/주차에서는 현재 참가권한으로 간주하지 않는다. 권한 자체가 없는 상세는 기존403/404를 유지하며 null 객체를 핑계로 접근을 새로 열지 않는다. 번호/password는 동시에 공개되며 number 단독 공개 예외도 없다.

메모는 신청자 본인과 현재 권한있는 리더만 읽는다. 리더 신청목록은 기존 리더권한 검사를 유지한다. 일반참가자의 상세 members에는 memo key를 추가하지 않는다. preset ID나 현재 저장문구를 옛 신청 응답에 연결하지 않는다. record snapshot은 당시 보존 구조 그대로이며 새로운 secret/현재표/메모를 주입하지 않는다. `content=null`은 정상 계약 값으로 유지하고 빈 기본 content를 합성하지 않는다.

## 입력·오류·원ACK와 갱신

각 operation의 전체 필수 입력/CAS/header/성공·오류본문은 bundle을 따른다. 정책 제안의 입력 차이 표를 함께 적용한다. BETA_SCHEDULE_REQUIRED는 legacy방의 beta 일정편집/선택/제안에 적용하고 legacy의 기존 관리·조회/신청은 자동변환하지 않는다. SCHEDULE_REVIEW_REQUIRED는 needs_review의 일반 조율/선택을 막는 코드이며 **미래 일정 복구제안 자체를 막는 코드가 아니다**. proposal/response는 기존분모·명시동의/CAS로 복구한다. 후보 없음은 HTTP 오류가 아니며 기본약속 유지다.

| 조건 | HTTP/code와 소비 |
|---|---|
| 불허문자/잘못된profile·조합·키·기간/빈preset | 400 INVALID_REQUEST; 입력 보존·수정, 자동삭제/재신청 없음 |
| 정규화후 허용문자21자 이상 | 400 APPLICATION_MEMO_TOO_LONG |
| preset6개 이상 | 400 APPLICATION_PRESET_LIMIT_EXCEEDED |
| 원문4096 UTF-8 bytes/전체요청32768 bytes 초과 | 413 REQUEST_TOO_LARGE; trim/정규화 전 byte 제한 |
| 기존 인증/권한/자원없음 | 401 ACCESS_INVALID / 기존403권한code / 기존404code; Bearer/no-store 유지 |
| 새 명령의 context/revision/기한 불일치 | 기존409 REVISION_CONFLICT/TARGET_CONTEXT_STALE/SELECTION_CONTEXT_CHANGED/CYCLE_CHANGED/RECRUITMENT_CLOSED 등; 실패pending/입력 보존 |
| 동일key 다른 원입력/진행중/만료 | 기존409 IDEMPOTENCY_CONFLICT/REQUEST_IN_PROGRESS/IDEMPOTENCY_EXPIRED; 진행중 Retry-After:2 |
| 구버전이 beta대상에 차단목록의 새쓰기 | 409 CLIENT_UPGRADE_REQUIRED. 기존성공ACK 조회는 아래 우선순위 유지 |
| provider/DB일시실패 | 기존503 SERVICE_UNAVAILABLE; 실패를 빈표/저장성공으로 표시하지 않음 |

추가 오류만 operation.x-beta-errors에 기재했다. 기존 업무별 권한/reason은 원계약·서비스 guard를 유지하며 이 목록을 기존 error.code 전체 enum으로 사용하지 않는다. 오류본문은 error.code/message/request_id/details 및 기존 선택 retry 필드다. 모든 응답 no-store,401 Bearer,429 Retry-After60을 보존한다.

재전송은 **operation/method/path/query(profile 포함)/실제T/원본문/Idempotency-Key**를 함께 보존한다. JSON key 존재/누락/null과 문자열 원문을 보존하고 정규화전 digest를 사용한다. 과거 profile 없는 pending에 profile·memo=null·추가키를 넣지 않는다. 새profile operation namespace는 기존 원요청의 namespace/digest를 바꾸지 않도록 분리/표식한다. 기존인증·현재보안확인을 유지한 원ACK lookup/replay는 새 target beta차단·기한·CAS보다 먼저 수행한다. 유효원ACK는 원응답을 돌려주며 새예약/번호/복사/worker효과를 재실행하지 않는다. 과거key가 만료/다른본문이면 기존결과를 유지하며 새성공으로 추정하지 않는다.

ACK수신 후 상세/plan/신청목록 GET 실패는 **조회만 재시도**한다. 생성/참가/설정 성공 후 해당T의 detail/plan·그래프·내목록/검색을 무효화하고 필요한 현재화면만 재조회한다. C+N 생성은 두T 모두, 전역탈퇴/해산은 실제 영향받은 두T를 갱신한다. 메모 신청후 자기신청/리더목록, preset PUT후 preset snapshot만 갱신한다. preset 저장 실패가 입력중 메모를 지우거나 신청을 다시 보내지 않는다. 기기간 최신화는 진입/명시갱신 GET이며 새 polling/push는 없다.

## 구버전 새쓰기 분류

다음 표는 **profile 없는 새 명령이 이미 beta로 생성된 실제 대상에 접근할 때**다. profile 없는 새 방생성은 legacy 방식 그대로이며 beta방으로 자동생성하지 않는다. safe도 기존 auth·권한·CAS·멱등·주차 제약과 beta 예약정리 helper가 필요하다. 사용자없는 자동시각변경의 신규근거로 삼지 않는다.

- 차단: join, applications, approve, continuation-participations, recruitment-openings, character-changes, PUT availability-submission, PUT schedule-groups, schedule-proposals, schedule-proposals responses, schedule-group selections, session participation-confirmations, PUT target settings.
- 안전관리 유지: reject, withdraw, continuation-declines, participation-cancellations, leadership-transfers, formation, removals, common-settings, leave, end, personal-completion-departures, member-removals, membership-actions, raid-round completion/personal-completion, completion-corrections, manual-completion. 이탈/완료/해산 시 해당 예약을 원자 정리하고 다른T/과거기록은 기존 영향 규칙대로 보존한다. formation은 기존배치 제약을 유지하며 시각/참가 생성·동의를 대체하지 않는다.
- IF-001 비활성 보존: weekly-incomplete-closures/weekly-resume-proposals와 기존 원pending/ACK는 기존 권한/동작을 보존한다. beta도 이를 자동복구 UX로 연결하지 않는다. needs_review 복구는 schedule-proposals의 별도 guard다.
- 읽기: profile 생략은 기존 shape, beta profile은 이 고정안 shape. 안전한 관리 context를 조회하려고 구클라이언트를 일괄 차단하지 않는다. 새표시를 이해하지 못하는 클라이언트의 위험한 새쓰기는 위 목록으로 막는다.

세션/일정group/proposal/round로 접근하는 명령도 먼저 실제 room/T를 해석해 같은 분류를 적용한다. 경로에 room_id가 없다고 예외가 되지 않는다. 원ACK 재생과 새명령 안전분류는 서로 별개다.

## 다음 담당과 미완료

Backend는 문자정책 수용·완결 DTO/예시/차단·안전목록 고정안을 제공한다. Flutter는 **고정안2의 잔여 소비차이와 최종합의 상태**를 확인하고, operation/query/profile 포함 원요청 영속복구·C+N개별draft/전용DTO 구현 설계를 이어간다. 기존 제품결정/정상시험을 반복 요청하지 않는다. query 전달과 영속복구는 Flutter 미완료 상태이며 완료로 올리지 않는다.

양측 합의 후 Backend 구현/마이그레이션·격리 PostgreSQL/HTTP·동시성/호환검증을 별도 작업 파트로 진행한다. 이번 문서 인계의 승인에 merge/배포/실데이터 변경을 포함하지 않는다.

## 전체 operation 목록

아래 목록의 구버전 분류는 bundle의 x-old-client-on-beta-target과 일치한다. 신규 presets는 대상T와 무관하다.

| method | path | 구버전 beta대상 새쓰기 |
|---|---|---|
| GET | `/v2/me/raid-room-creation-context` | read_legacy_shape |
| POST | `/v2/raid-rooms` | legacy_create_unchanged |
| GET | `/v2/raid-rooms` | read_legacy_shape |
| GET | `/v2/raid-rooms/{room_id}/admission-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/join` | blocked |
| POST | `/v2/raid-rooms/{room_id}/applications` | blocked |
| GET | `/v2/raid-rooms/{room_id}/applications` | read_legacy_shape |
| GET | `/v2/raid-room-applications/{application_id}` | read_legacy_shape |
| POST | `/v2/raid-room-applications/{application_id}/approve` | blocked |
| POST | `/v2/raid-room-applications/{application_id}/reject` | safe_management |
| POST | `/v2/raid-room-applications/{application_id}/withdraw` | safe_management |
| POST | `/v2/raid-rooms/search` | read_legacy_shape |
| GET | `/v2/me/raid-room-filter-context` | read_legacy_shape |
| GET | `/v2/groups/{group_id}/raid-room-character-candidates` | read_legacy_shape |
| GET | `/v2/raid-rooms/{room_id}` | read_legacy_shape |
| GET | `/v2/raid-rooms/{room_id}/detail` | read_legacy_shape |
| GET | `/v2/me/raid-rooms/{room_id}/plan` | read_legacy_shape |
| GET | `/v2/me/raid-room-applications` | read_legacy_shape |
| GET | `/v2/me/raid-room-memberships` | read_legacy_shape |
| GET | `/v2/groups/{group_id}/raid-room-member-projections` | read_legacy_shape |
| GET | `/v2/me/raid-rooms/{room_id}/continuation-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/continuation-participations` | blocked |
| POST | `/v2/raid-rooms/{room_id}/continuation-declines` | safe_management |
| GET | `/v2/me/raid-rooms/{room_id}/opening-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/recruitment-openings` | blocked |
| GET | `/v2/me/raid-rooms/{room_id}/participation-cancellation-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/participation-cancellations` | safe_management |
| GET | `/v2/me/raid-rooms/{room_id}/leadership-transfer-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/leadership-transfers` | safe_management |
| POST | `/v2/raid-rooms/{room_id}/character-changes` | blocked |
| GET | `/v2/me/raid-rooms/{room_id}/availability-submission` | read_legacy_shape |
| PUT | `/v2/me/raid-rooms/{room_id}/availability-submission` | blocked |
| GET | `/v2/me/raid-rooms/{room_id}/schedule-context` | read_legacy_shape |
| GET | `/v2/me/raid-schedule-overlaps` | read_legacy_shape |
| POST | `/v2/raid-sessions/{session_id}/participation-confirmations` | blocked |
| PUT | `/v2/raid-rooms/{room_id}/schedule-groups` | blocked |
| GET | `/v2/raid-schedule-groups/{group_id}/candidates` | read_legacy_shape |
| POST | `/v2/raid-schedule-groups/{group_id}/selections` | blocked |
| POST | `/v2/raid-rooms/{room_id}/schedule-proposals` | blocked |
| POST | `/v2/raid-schedule-proposals/{proposal_id}/responses` | blocked |
| GET | `/v2/raid-rooms/{room_id}/command-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/weekly-incomplete-closures` | inactive_preserved |
| POST | `/v2/raid-rounds/{round_id}/completion` | safe_management |
| POST | `/v2/raid-rounds/{round_id}/personal-completion` | safe_management |
| POST | `/v2/raid-rooms/{room_id}/weekly-resume-proposals` | inactive_preserved |
| PUT | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion` | safe_management |
| GET | `/v2/me/raid-rooms/{room_id}/settings` | read_legacy_shape |
| PUT | `/v2/raid-rooms/{room_id}/settings` | blocked |
| PUT | `/v2/raid-rooms/{room_id}/formation` | safe_management |
| POST | `/v2/raid-rooms/{room_id}/removals` | safe_management |
| GET | `/v2/me/raid-rooms/{room_id}/common-context` | read_legacy_shape |
| PUT | `/v2/raid-rooms/{room_id}/common-settings` | safe_management |
| POST | `/v2/raid-rooms/{room_id}/leave` | safe_management |
| POST | `/v2/raid-rooms/{room_id}/end` | safe_management |
| GET | `/v2/me/raid-rooms/{room_id}/continuation-choices` | read_legacy_shape |
| GET | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-correction-context` | read_legacy_shape |
| POST | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/completion-corrections` | safe_management |
| GET | `/v2/raid-rooms/{room_id}/personal-completion-departure-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/personal-completion-departures` | safe_management |
| GET | `/v2/raid-rooms/{room_id}/member-removal-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/member-removals` | safe_management |
| GET | `/v2/raid-rooms/{room_id}/membership-action-context` | read_legacy_shape |
| POST | `/v2/raid-rooms/{room_id}/membership-actions` | safe_management |
| GET | `/v2/raid-rooms/{room_id}/admission-character-candidates` | read_legacy_shape |
| GET | `/v2/me/application-message-presets` | not_target_scoped |
| PUT | `/v2/me/application-message-presets` | not_target_scoped |
