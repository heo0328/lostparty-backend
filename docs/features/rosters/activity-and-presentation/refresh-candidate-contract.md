# 상세 분석 후보 계약과 구현

2026-11-17 / Issue58 / `feat/roster-refresh-policy` / 구현 `8f29271d610aad83021ec3a00e5879f2adda76d5`.
현재 계약은 아래 제품·조회·명령·설정·복구 절과 B2 enum 보완을 함께 적용한다. 구현/격리검증·실제개발 DB0038/API 반영 완료, 사용자 지시로 작업브랜치에 게시한다. dev/main 병합·운영은 별도다. 원문 설계 경과는 [초기 검토](refresh-candidate-review.md)·[DEV_LOG](../../../project/DEV_LOG.md), 실제반영은 [원장](../../../engineering/operations/records/analysis-candidates-local-rollout.json)을 따른다.

Native [전체6 N1](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6945574683)의 일반 앱 연결·자동검증 완료 보고를 수신했다. 남은 것은 사용자 실제HTTP저장/신규후보·재등록·웹/Android 결과이며 기존 기술질문/개발반영 대기를 반복하지 않는다. 아래 B1/B2/B3 인계 절의 미커밋/미반영 설명은 각 당시 이력이다.

## 제품과 소유 범위

전체 목록은 보존한다. 자동은 선택 집합∪신규1700/첫1700 후보, 최초 등록·인증1700 최초1회. 기존 선택저레벨 유지, 신규저레벨 목록만, null을0/적격으로 추정하지 않는다. 수동전체는 선택만, 개별manual은1명. 나이스단OFF는 신규에도 적용·실패집계 제외. 사용해제는 후보 자동분석 금지·개별manual 허용. 후보 분석은 Activity/대표/configured를 자동 생성하지 않는다.

첫 도입 기존 canonical은 legacy 기준선으로 유지해 이미1700인 미선택을 부활시키지 않는다. 도입 후 새 관찰 UUID가 처음 유효1700으로 확인되면 후보를1회 생성한다(null 관찰은 첫 유효레벨 판정을 소모하지 않음). 기존 legacy 캐릭터는 도입 후 유효1700미만 정상 관찰 뒤 유효1700이상 관찰이 있을 때만 첫 도달 후보를 생성한다. 목록 관찰 실패/누락은 이 사실을 초기화하지 않는다. 첫 인증 성공의 검증된 roster는 소유 확정 transaction에서 재사용하되 armory 분석 성공과 혼동하지 않는다.

동일 회원/account/ownership_revision의 삭제·재등록은 기준선·제외·후보 완료를 보존한다. 새 registration/configuration 생성 시 미선택으로 제외를 추정하지 않고 보존된 의도를 적용한다. 소유세대 변경은 승계하지 않으며 이전 세대 자료는 현재 소유자에게 노출하지 않는다. 실제 회원 탈퇴 데이터 수명은 별도 정책이고 이 계약이 영구보존/삭제 승인이 아니다.

## 조회 — 하나의 opt-in

GET /v2/me/account-bootstrap?include_analysis_candidates=true
기존 include_roster_presence와 병용 가능. true/false 각1개, 누락 false, 다른/중복 query와 body는 기존 strict400. 인증/오류/읽기전용/no-store/REPEATABLE READ는 기존과 같다. false일 때 새 키를 생략해 기존 응답을 보존한다. true일 때 각 registrations[]에 analysis_candidates 키를 추가한다. 미인증/타인 소유에는 null. 현재 소유에만 다음 객체를 반환한다.

- policy_version: "analysis-candidates-1" (문자열 계약 ID)
- policy_revision: 양의 정수 (명시 선택/제외 의도 변경 때 증가, 문자열 ID와 구분; 후보 실행은 개별 generation/lease로 CAS)
- baseline: "legacy" | "observed" | "not_initialized"; not_initialized면 GET이 만들지 않고 다음 정상 관찰을 기다린다.
- game_account_id, ownership_revision, registration_id, settings_version: 현재 scope
- complete: true; candidates: 후보ID 순 전체 배열, 최대200. 페이지/부분 잘림 없음.
- 후보: candidate_id/character_id UUID, generation 양의정수(명시 재시도 실행세대), reason "new_at_threshold" | "first_threshold" | "initial_verification", state "pending" | "running" | "succeeded" | "blocked", eligibility "eligible" | "nice_group_disabled" | "explicitly_excluded" | "character_unusable" | "command_unresolved", next_attempt_at ISO8601|null, last_error AnalysisError|null, unresolved_command 객체|null.
- unresolved_command: command(해당 item의 정확한 원본문), recovery "same_command" | "reconcile_required". 신규 명령 예약 때 원본문을 후보 실행정보에 저장하므로 두기기/재설치도 동일ID·본문 복구 가능. 토큰/armory는 포함하지 않는다. 과거 명령의 digest로 본문을 역산하지 않는다.
- succeeded의 completed_at와 completed_command_id 제공. 원ACK 24h 경과 뒤에도 성공 근거이며 원ACK 자체의 복원은 아니다.

나이스단/usable/명시제외는 읽기 시 최신 투영이며 GET이 state를 바꾸지 않는다. failed blocked에는 오류/명시retry 안내를 유지한다. 선택 목록은 기존 characters/settings에서 읽으며 후보 배열에 선택 전원을 중복 저장하지 않는다. 소유세대에서 retired돼 후보 이력만 남은 캐릭터도 목록 최대200 검토 대상이다. 한 세대 후보 총수가200을 넘으면 잘라 반환하지 않고 기존 BOOTSTRAP_LIMIT_EXCEEDED409로 전체 거절한다(생성/관찰 한도와 함께 표적 검증). 기존20원정대·캐릭터200·16MiB 전체 응답 상한, 초과 BOOTSTRAP_RESPONSE_TOO_LARGE409를 유지한다. 새 profile/별도GET/캐시는 만들지 않는다.

## 분석 POST 확장

POST /v2/me/character-analysis/refresh, 기존 items1..50/524288bytes/20초/동시2 유지.
기존 AnalysisCommand의 command_id, character_id, expected_ownership_revision, expected_lifecycle_revision, expected_summary_versions, trigger를 그대로 유지한다. 선택/일반manual은 종전 본문 그대로 사용 가능하다. 신규 후보 경로에만 candidate_context 객체를 추가한다:

candidate_id, expected_generation, expected_policy_revision, expected_settings_version,
purpose: "automatic_candidate" | "manual_retry".

automatic_candidate는 trigger=automatic, 현재 pending/적격 후보에만 허용. manual_retry는 trigger=manual, 해당 blocked 후보의 명시 재시도이며 나이스단OFF/명시제외 자동금지를 우회할 수 있는 사용자 개별 행동이다. 같은 body/command_id의 재전송은 기존 ACK, 새 명령의 manual_retry는 transaction 안에서 generation을1 올려 임대를 획득한다. expected_generation은 실행 전 읽은 값이다. 새로운 generation은 후속 projection에서 제공한다.

일반 개별manual 성공도 같은 소유세대/캐릭터의 유효 후보를 완료한다. 선택 automatic과 후보가 겹치면 Native는1item만 생성하며 서버도 동일 후보 임대로 단일 실행을 보장한다. 이미 blocked인 신규후보는 automatic_candidate 새ID로 재개하지 못한다. 다만 현재 Activity에 명시선택된 캐릭터의 기존 automatic 갱신1회는 별도 권리로 유지되며 성공하면 후보도 완료한다. blocked가 기존 선택경로 전체를 막아서는 안 된다.

기존 pending에는 새 필드를 삽입하지 않는다. exclude_unset 기반 digest/과거본문 호환을 유지하고, 원명령 replay가 현재 후보 CAS보다 먼저 일어나도록 한다(세션/현재 소유 접근검증 유지). 결과 item 형식은 기존 saved/skipped/failed/not_processed/in_progress/unknown 및 error/retry를 유지하고 새 성공 response shape를 만들지 않는다.

계약안 코드/허용행동:
- generation/policy/settings 불일치: failed409 REVISION_CONFLICT, 현재 projection 조회 후 새ID; 원명령 불명확 상태는 먼저 같은ID 복구.
- 후보 ID가 현재 scope에 없음: failed404 ANALYSIS_CANDIDATE_NOT_FOUND. 타인 후보 세부정보 노출 없음.
- 다른 실행의 후보 임대가 유효함: failed409 ANALYSIS_CANDIDATE_IN_PROGRESS, 새ID/provider 반복 호출 금지; projection의 unresolved 원명령 복구.
- terminal 실패후보 automatic 재요청: skipped200 ANALYSIS_CANDIDATE_RETRY_REQUIRED, 명시manual_retry만.
- 이미succeeded: skipped200 ANALYSIS_CANDIDATE_COMPLETED, 저장정보/현재projection 조회.
- 나이스단/명시제외/현재 자동부적격: 기존 skipped200 AUTOMATIC_TARGET_EXCLUDED. 실패집계/성공소모 없음.
- 실제 provider/역할/한도 오류: 기존failed503/429와 code·retry metadata 보존, 후보 blocked; 앱실행/재관찰만으로 새명령 발급하지 않는다.
- 결과불명/진행중/미처리: 기존 same_command/원본문. budget 거절·요청 미처리만으로 blocked로 만들지 않는다.

새409는 existing REQUEST_IN_PROGRESS와 구분한다. 후자는 같은 명령의 복구이고 후보중복409는 다른 명령 소유 임대이기 때문이다. 신규 코드는 현 실행 명세에 아직 추가하지 않았다.

## 설정 PUT과 제외 delta

사용 경로 PUT /v2/me/game-accounts/{registration_id}/character-settings를 확장한다. 현재 character-management-2·expected registration/settings/ownership/roster/order_digest는 유지하고 expected_analysis_policy_revision 양의정수 선택 필드를 제안한다. 신규 Native는 bootstrap 후보revision을 보내고 서버는 같은 transaction에서 CAS한다. 기존 클라이언트가 필드를 생략해도 기존 CAS하에 변경 delta를 기록한다.

서버의 잠금 후 실제 이전 Activity집합 A, 검증된 새집합 B로 A-B만 명시제외=true, B-A의 명시 재선택은 기존 제외 해제. A에도B에도 없는 자료는 일절 추정하지 않는다. 전체선택 PUT 재전송/정렬·대표 변경만으로 제외를 새로 만들지 않는다. 소유세대의 제외 사실은 Configuration.ended_at와 독립 보존한다.

기존 V1 settings writer에도 동일 delta hook을 연결해야 우회가 없다. 별도 opt-out UI/API/명시 전체제외 입력은 추가하지 않는다. 기존 최소1활동/대표/순서 규칙은 유지한다. 같은 명령 원ACK는 되풀이해서 delta를 적용하지 않는다.

사용해제/재선택은 policy_revision 증가, 실행중 후보 lease fencing. provider I/O 뒤 저장 transaction에서 당시 settings/policy stamp를 재검증하므로 먼저 commit된 해제가 이긴다. 먼저 분석 저장이 끝난 후 해제는 과거 성공을 취소하지 않고 이후 자동호출만 막는다. 저레벨을 선택하는 동작 자체는 기존대로 허용한다.

## 영속·원자성·복구

기준선(account/member/ownership_revision)과 캐릭터 관찰/제외/후보 상태를 기존 #18 공통 구조로 설계한다. account-ownership-character-event 유일성으로 신규+첫1700을1건 처리한다. 임대 실행세대/command원본문/오류는 후보와 연결해 중복·복구 근거를 남긴다. 무한 실행이력 테이블은 만들지 않고 최근 실행/완료 근거를 보존한다.

정상 목록 transaction에서 후보 upsert, 후보 예약 transaction은 기존 game-mutations lock와 명령 dedup 순서를 일관되게 사용한다. 네트워크는 잠금 밖. 저장 transaction의 최신권한/소유/lifecycle/정책/설정/후보임대/summary CAS 후 summary+후보성공+ACK를 원자 commit한다. lease30초와 generation fencing을 연결해2기기가 다른ID로 동시에 수집하지 못한다. 기존 in-flight 관찰 공유는 보조일 뿐 완료 원장이 아니다.

원ACK24h, 미완료 명령48h/정리 이후에도 후보 완료·제외·blocked 오류는 남긴다. unresolved의 원장 expiry/세대 대조는 명시 복구 POST의 mutation transaction에서 처리하며 GET은 정리하지 않는다. 정리 뒤 재개 허용 시 새 명시manual_retry를 요구한다. 후보 succeeded면 원장 만료를 이유로 새 수집을 하지 않는다. 등록 삭제 cleanup이 후보/기준선을 건드리지 않게 FK를 registration/Configuration cascade에 연결하지 않는다.

## 구현 순서·인계 완료 조건

1. Native가 이 계약의 읽기DTO/새입력·코드/원본문 복구·설정delta 소비를 대조하면 계약 명세/합성 예시를 고정한다. 제품 정책 질문 재개가 아니다.
2. 구현 착수 시 최신 Alembic head 확인 후 비파괴 migration·기준선/순수판정·정상관찰/인증 연결. 기존 자료는 보수적legacy로 유지, GET에서 migration 금지.
3. 후보 읽기 opt-in·권한/명령/임대·원자저장·설정writer delta·등록삭제 cleanup 보존을 연결하고 OpenAPI를 구현과 함께 갱신한다.
4. 격리DB 표적 시험: legacy/new/null/1700/인증재사용, 선택저레벨·나이스단OFF·명시제외/재선택·unconfigured, 두기기/같은ID·다른ID/선택중복·manual성공, CAS/소유변경·ACK유실·24h/48h/정리, 실패blocked/새ID반복거절·삭제재등록.
5. 후보이미지 전체 OpenAPI 비교와 Native 계약 인계. commit/push는 별도 사용자 지시 기준, 실제dev 교체도 별도 지시 기준이다. 운영/DB초기화/자료삭제/키변경/provider한도소진 승인으로 확대하지 않는다.

현재 수행은 정적 코드·계약 대조 및 문서 검증만이다. 원정대 refresh의 일반1+N·404 anchor대체최대3/인증 장비조회 예외를 바꾸거나 절감 수치를 실측했다고 주장하지 않는다.

## 인계

[Issue58 전체1 Backend B1](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6943318871) 게시·순번 조회 확인. 다음 Native 소비 대조 후 명세/구현 고정. 미커밋·미push.

## B2 고정 보완 — 복구와 enum

reconcile_required도 같은 POST /v2/me/character-analysis/refresh, {"items":[projection.unresolved_command.command]} 원ID·원본문 그대로다. candidate_context를 새generation/policy로 덮지 않는다. 서버는 세션·현재 소유 접근검증→저장된 원본문/digest 일치→원장/후보 실행세대 확인 순서로 처리한다. 원ACK가 유효하면 원ACK, 원실행이 유효하면 in_progress409 REQUEST_IN_PROGRESS/same_command. 원ACK 만료/원장 삭제 뒤 동일 후보 실행이 미해결이면 provider 호출 없이 후보를 blocked로 reconcile하고 failed409 ANALYSIS_CANDIDATE_RECONCILED/new_command를 반환한다. 이 결과는 저장된 원본문 참조에 대해 반복해도 재수집하지 않는다. 이후 bootstrap 최신generation/policy/settings로 읽은 manual_retry 새ID만 사용한다. 현재 소유권 상실/캐릭터사용불가는 기존403/409이며 타소유세대에blocked를 쓰지 않는다. 복구자체는 원 ownership/lifecycle/policy CAS가 stale이어도 현재 소유 접근과 원본문 연결이 맞으면 허용하되 새분석은 절대 실행하지 않는다.

고정 enum (item.status이며 HTTP envelope200):
ANALYSIS_CANDIDATE_NOT_FOUND = failed/404/none
REVISION_CONFLICT = failed/409/new_command
ANALYSIS_CANDIDATE_IN_PROGRESS = failed/409/none
ANALYSIS_CANDIDATE_RETRY_REQUIRED = skipped/200/none
ANALYSIS_CANDIDATE_COMPLETED = skipped/200/none
ANALYSIS_CANDIDATE_RECONCILED = failed/409/new_command
AUTOMATIC_TARGET_EXCLUDED = skipped/200/none
REQUEST_IN_PROGRESS = in_progress/409/same_command

IN_PROGRESS 실패ID를 재전송해서 다른실행이 해제되길 기다리지 않는다. bootstrap에 있는 owner 원ID/원본문을 복구한다. RETRY_REQUIRED는 명시manual_retry, COMPLETED는저장정보읽기다. manual_retry는blocked에 nice_group_disabled/explicitly_excluded가 있어도현재소유/usable이면허용한다. 어떤new_command도앱의자동반복재시도승인이아니다.

## B2 구현·검증 기준

현재 소스에0038 비파괴 기준선/후보 구조·bootstrap opt-in·분석 후보context/임대/원본문 만료복구·양쪽 설정writer delta와 이력보존을 구현했다. 원래 Issue55 합성schema는 보존하고 [확장schema](refresh-candidate.schema.json)와 [고정예시](refresh-candidate.examples.json)를 별도로 두었다. 신규 예시에는 만료복구·다른owner명령 복구·skipped 구분·제외/나이스단OFF 수동retry saved를 포함한다.

B1 대비 기술 보정: policy_revision은 선택/제외 의도에만 증가한다. 후보별 state 변경까지 원정대revision을 증가시키면 같은 배치의 다음후보/두기기 독립캐릭터가 불필요하게CAS 충돌하므로 개별generation/command/lease로 검증한다. GET의 현재 state는 snapshot 읽기이고 원정대revision만으로 state캐시를 재사용하지 않는다. 종전 context없는 terminal명령의24h 만료는 IDEMPOTENCY_EXPIRED를 유지한다. 후보context/미해결 running 실행만 원본문 reconcile 경로를 사용한다.

검증: current131PASS/하위13PASS, bootstrap/management/후보 회귀86PASS, 최종 후보/합성예시/소유세대/자료보존migration17PASS. 일부 current/설정 회귀는 마지막 복구error표시/48h projection 보완 전 버전이고 해당 보완은 최종 후보17PASS에서 확인했다. 초반 startup schema호환/시험seed 및 구명령 만료 호환 실패를 보완했으며 실패를 PASS로 집계하지 않는다.

개발 DB/API는 기존0037/실행이미지 그대로이며0038 migration/서버교체·provider 호출/키변경/초기화는 수행하지 않았다. 후보이미지 OpenAPI 비교·hash와 게시인계는 후행 결과를 따른다. 미커밋·미push라 Native는 아직 source를 원격소비할 수 없다.

## 최종 인계 상태

[Issue58 전체3 Backend B2](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6944474148). 최종 OpenAPI SHA256: `12634daa64a8c4cbdfecfdb53bc7c1aca3bdb721c5ea555d098aea51544b9665`. 검증된 합성 요청/응답을 분석POST OpenAPI 예시에도 직접 포함하고 최종격리이미지 전체객체 일치191경로 PASS. 파일구조/JSON Schema/DTO·문서검증 PASS. 미커밋·미push, 실제dev0037 그대로. 신규 dev호출은 아직지원하지 않는다. 다음 Native enum/복구소비, 소스게시와 별도 사용자 dev반영 지시 후 통합시험이다. 기존미결정/미구현 문장은 당시 설계단계 이력으로만 해석한다.

## B3 실제 개발 지원

2026-11-17 사용자 명시 승인으로0038/API 반영 완료. [전체4 Backend B3](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6944629650)·[보존/실행집계](../../../engineering/operations/records/analysis-candidates-local-rollout.json). 기존114테이블794행/키5개·주요환경 지문 일치, health200·미인증401·실제OpenAPI 전체일치·유효세션1명 저장읽기 PASS. 신규계약을 로컬dev에서 소비할 수 있다. 실제provider/분석저장·Native기기인수는 별도다. 소스 미커밋·미push, 운영 변경 없음. 위dev미지원 표기는 B3 이전 이력이다.
