# 서버 수집·분석·저장 및 비로그인 공통 UI — Backend 설계안

2026-11-16 / [Issue55](https://github.com/heo0328/lostparty-backend/issues/55) / Backend 조사·공동 설계 단계. **이 문서는 제안이며 실행 API 계약이 아니다.** 현재 계약은 [OpenAPI](../../../../openapi/openapi.yaml)다. Native 전체2 대조를 수신했고 아래 수정안을 반영했다. Backend 후보1의 정확 wire/오류·저장/제거 영향표를 작성했고 Native 전체5 수용에 따라 같은 character-analysis-refresh-1을 공동 설계 기준으로 확정했고 구현 단위/담당/완료조건을 계약 문서에 연결했다.

## 목표·승인 경계

사용자는 임시 사용자 베타 단계이며, 기존 결과 승계보다 단순하고 계속 확장·관리할 수 있는 단일 구현을 우선한다고 명시했다. 정식 운영 때 가능한 자료는 유지하되 자료/이전 방식 보존 때문에 임시 코드·호환 계층을 남기지 않는다. 구버전 앱 지원, 옛 미전송 summary/응답불명 명령 복구, 구신 이중 실행·쓰기·전환 플래그·자료 이전 리허설은 이번 전환의 완료 조건이 아니다. 새 방식의 명령 정합성은 별도로 보장한다.

이번 승인은 조사·설계·관련 Issue 회신까지다. 기능 구현·새 OpenAPI 반영·키 설정·DB migration/초기화·기기 자료 삭제·배포는 하지 않는다. 데이터 초기화가 단순한 해법이면 대상/영향을 제시해 별도 실행을 결정한다. 기존 문서의 과거 호환/승계 합의를 이번 전환의 추가 요구로 재도입하지 않는다.

## 기준·확인 수준

- 소스: dev/main `cda4db352c9ac922f269b9ec2794f0d888d4dca6`에서 조사. 작업 구간 `서버 수집·분석 전환 공동 설계`, 목적 브랜치 `refactor/lostark-server-processing`. 새 설계 문서는 미커밋·미push다.
- 로컬 실행의 마지막 원장: [BUG-036 반영](../../../engineering/operations/records/unopened-next-detail-local-rollout.json), image `add28707…1f71f2`, DB0036. 최초 inspect는 Docker 엔진 연결 실패였으나 사용자 기동 후 재조회에서 API running/healthy·동일 image를 확인했다. 이미지 ID 확인은 서버 소스와 현재 Git 전체의 동일성/기능 재검증을 뜻하지 않는다. 서버 교체는 하지 않았다.
- 운영 마지막 확정: [v2.3.0 원장](../../../engineering/operations/records/release-2.3.0-deployment.json), source `05daa42`, DB0036. 이번에 운영에 접속하지 않았다.
- Native: Issue55 본문의 고정 소스 조사 보고를 입력으로 사용했다. Flutter 로컬 경로/소스는 읽지 않았다. Native 전체2가 고정 source/비민감 fixture/상세 필드를 인계했고 scoped mapper·role policy 두 파일은 GitHub 고정 source로 추가 확인했다. Python 동등성 시험은 아직 미실행이다.

## 현재 외부 호출 지도

아래는 정적 코드 조사 결과다. 공통 transport는 [provider.py](../../../../app/game_accounts/provider_io/provider.py)의 siblings/종합 armory/profiles 세 경로이며, 앱에서 해당 transport를 사용하는 모든 생산 경로를 함께 추적했다. 별도 앱 내 로아 HTTP 구현은 검색에서 발견하지 못했다. Google 인증 HTTP는 이 전환 대상이 아니다.

| 사용자 행동·진입 | 권한·키 | 수집·가공·저장·응답 |
|---|---|---|
| POST `/v1/game-accounts/preview`, `/v2/game-accounts/preview` | 회원 인증 → 개인 Credential capture/check | `rosters.service.preview/lookup` → siblings → 이름/서버/수치/중복 검증 → 회원·키버전·context별 MemberPreview/MemberFetch. 목록 캐시30분·lease30초, 중복 요청 최대10초 합류. v2는 소유권 context를 추가한다. |
| POST `/v1/me/game-accounts` 등록 | 회원 인증·멱등 키·등록 관계 stamp → 개인 키 | siblings → 중복/등록 한도·최신 관계 확인 → Registration preview 저장. 취득 목록만으로 소유권을 부여하지 않는다. |
| POST `/v1/me/game-accounts/{id}/refresh` | 본인 등록·소유/등록 stamp·개인 키, 수동 제한 | siblings → owned_refresh는 기존 usable anchor 최대3개를 사용하되 provider404일 때만 다음 anchor 조회 → NameClaim/동일 원정대 검사 → 캐릭터/누락 관찰 갱신. 분석 summary 갱신과는 별개다. |
| POST `/v1/me/game-account-verifications` 및 `/{id}/confirm` | 회원·등록/인증 상태·기한·개인 키 버전 | siblings + 새 armory → 서버 장비 baseline/receipt·대상 identity → 장비 변화 확인·소유권 처리. 종료/만료 confirm은 provider를 호출하지 않는다. |
| POST `/v2/me/game-account-verifications`, `/{id}/confirm`, `/v2/me/ownership-disputes/{id}/defenses` | 회원·등록/후보/분쟁 버전·개인 키 | `ownership_disputes.commands` → accounts.lookup(proof=True) → siblings + 새 armory. `core.scope_error`도 개인 키 버전을 확인한다. Proof/분쟁/소유권 변경은 짧은 최종 트랜잭션에서 수행한다. |
| POST `/v1/me/game-accounts/{id}/combat-power/refresh` | 본인 owned 원정대·usable 대상 전체 선검사·개인 키 | profiles에서 서버/이름과 전투력 검증. ScopedPowerCache는 회원·UUID/수명·키버전별, 정상30분/실패10초·lease30초. 동시2·전체20초 예산, 항목별 결과·최근 정상값 보존·멱등 ACK 저장. 늦은 worker 결과는 저장하지 않는다. |
| 소유권 분쟁 주기 정산 | `current_lifespan`이 worker 시작. 회원 active·원정대/분쟁/lease 세대·개인 Credential 직접 복호화 | 5초 loop가 due 분쟁을 claim → siblings + 새 armory → 최종 회원/키/등록/후보/소유권/기한 재검사 → 이전 또는 보류. 활성 참가 영향 미합의 정책(#15)은 그대로 보류한다. 서버 키 전환에서 누락하면 안 되는 비HTTP 경로다. |
| 수동 진단 CLI 2개 | HTTP에 연결되지 않음. 숨김 터미널 입력 키·대상 | `verification.diagnostics`: siblings 형태 확인. `ownership_diagnostics`: armory 장비 관찰. DB 업무 쓰기 없는 명시적 진단 도구이며 자동 수집/회원 기능이 아니다. 키 입력은 서버 공급 재사용 방식으로 교체할 후보. |

주요 근거: [rosters/service.py](../../../../app/game_accounts/rosters/service.py), [observations.py](../../../../app/game_accounts/rosters/observations.py), [owned_refresh.py](../../../../app/game_accounts/rosters/owned_refresh.py), [power_service.py](../../../../app/game_accounts/power/power_service.py), [분쟁 commands](../../../../app/ownership_disputes/commands.py), [scope 검사](../../../../app/ownership_disputes/core.py), [정산 worker](../../../../app/ownership_disputes/worker.py), [목록 진단](../../../../app/game_accounts/verification/diagnostics.py), [장비 진단](../../../../app/game_accounts/verification/ownership_diagnostics.py).

현재 lifespan의 나머지 작업은 인증 정리와 모집 주차 처리다. 로아 정기 전체 원정대/빌드 수집 job은 발견하지 못했다. legacy 앱도 공통 원정대/키/분쟁 모듈을 마운트하므로 이 코드들을 legacy 전용으로 잘못 분류하지 않는다. legacy DB0023 시험 실행을 구버전 지원 목적으로 확장하지 않으며, #55에서 직접 불필요해지는 사용처만 제거한다.

## 재사용·변경·제거 결정

| 영역 | 설계 방향 |
|---|---|
| 업무 책임 | HTTP는 입력·인증, 업무 함수는 현재 권한·정책, 최종 트랜잭션은 CAS·자료 저장·ACK를 소유한다. 외부 I/O는 업무 잠금 밖에서 수행한다. 기존 기능별 모듈 안에서 확장하며 일반 Repository/작업 프레임워크를 신설하지 않는다. |
| transport | URL 인코딩·redirect 금지·connect3/read5초·본문8초 deadline·최대1MiB·프로세스 내 동시2·민감 원문 오류 차단을 재사용한다. 자동 무한 재시도/대기는 추가하지 않는다. |
| 키 | 서버 읽기 전용 secret 파일 하나를 공급한다. 제안 이름은 secret_dir의 `lostark-api-token`, 공개 응답/로그/Flutter 전달0. 스냅샷은 토큰+비공개 세대 식별을 가진다. 개인 Credential DB 조회/버전 검사는 제거하고, 외부 호출 전·최종 저장 전 현재 서버 키 세대를 확인한다. 역할 분석 버전·카탈로그 버전·업무 revision과 키 세대를 혼용하지 않는다. |
| 호출 제한 | 기존 token fingerprint별 DB quota/blocked_until을 모든 사용자·HTTP/분쟁 worker가 공유하게 한다. 현재 자체 상한80회/60초는 프로젝트 설정값이며 공급자 보장치가 아니다. 실제 문서/응답 근거와 대조한 뒤 설정한다. transport semaphore는 프로세스별이며 전역 제한이라고 설명하지 않는다. 회원별 남용 제한도 유지한다. |
| 오류 | 서버 키 미설정·거절·교체는 서비스 구성 문제로 안전한503을 제안한다. 개인 키 입력을 요청하지 않는다. 현재 자체 quota429와 상위429→503 UPSTREAM_RATE_LIMITED·Retry-After/retry_at 의미를 재사용한다. 재시도 시각 전에 서버가 잠든 채 기다리지 않는다. |
| 관찰/캐시 | 목록/전투력의 기존 lease·generation·짧은 실패 캐시를 재사용하되 개인 credential_version을 제거한다. 키가 공유돼도 결과·소유 증거는 회원·UUID·소유수명·대상 범위로 분리한다. 무제한 전역 raw cache를 신설하지 않는다. 장비 소유 인증은 새 관찰을 사용하며 일반 캐시로 대체하지 않는다. |
| 분석 | 서버의 기존 수치/장비/식별 검증과 Flutter의 역할·보석·스킬·아크그리드 분석을 분리해 조사한다. 레이드 카탈로그는 빌드 분석 카탈로그의 대체물이 아니다. Native 전체2의 고정 규칙/카탈로그·합성 fixture 정의를 입력으로 순수 분석 함수와 제품별 최소 projection을 서버로 이전한다. |
| 출처/소비자 | 새 산출물은 제안 `source=server_analysis`, 모집 비교의 trust는 `server_computed`로 표시한다. 로아 자체가 보증한 분석값이라는 뜻이 아니다. analysis_rules_version/catalog_version/관찰시각을 유지한다. 현재 `flutter_analysis`/`client_submitted`는 profile DTO뿐 아니라 모집 비교 DTO·동적 wire·main 계약 보정·입장 snapshot에도 있으므로 생산자/소비자를 함께 전환한다. 두 출처를 영구 병행하지 않는다. |
| 개인 결정 | 자동 관찰/분석이 활동·대표·소유권이나 수동 선호 역할을 바꾸지 않는다. 나이스단 OFF는 새 자동 수집의 제외 조건이며 이전 빌드 삭제 조건이 아니다. 역할은 현재 수집 근거로 감지하며 미판정이면 저장하지 않는다. preferred_role 선택은 표시/선호 설정만 변경한다. 강제 역할 저장·사용자 선택 후 재수집 단계는 도입하지 않는다. |
| 제거 | 개인키 GET/PUT/DELETE/restore와 암복호화/회원 key readiness, 클라이언트 role-summary PUT/배치 업로드와 그 전용 검증/전송복구 경로를 제거한다. personal profile/일괄 읽기·preferences·presentation·소유권 검증·공유 quota처럼 새 방식에서 사용하는 부분은 유지한다. 옛 API를 새 API로 프록시하는 shim은 만들지 않는다. |

현재 키/제한 근거: [service](https://github.com/heo0328/lostparty-backend/blob/cda4db352c9ac922f269b9ec2794f0d888d4dca6/app/lostark_keys/service.py), [rate_limits](https://github.com/heo0328/lostparty-backend/blob/cda4db352c9ac922f269b9ec2794f0d888d4dca6/app/lostark_keys/rate_limits.py). 현재 저장/소비 근거: [profile DTO](../../../../app/game_accounts/schemas/profile_schemas.py), [profile 저장](../../../../app/game_accounts/character_profiles/profiles.py), [최근 정상 전투력](https://github.com/heo0328/lostparty-backend/blob/cda4db352c9ac922f269b9ec2794f0d888d4dca6/app/game_accounts/power/power_success.py), [모집 비교](../../../../app/raid_rooms/participation/participation_core.py).

## 최종 계약 제안 — 후보1/Native exact wire 대조 대기

[character-analysis-refresh-1 계약·오류·저장/제거 영향표](analysis-refresh-contract.md)가 정확 명세의 원본이다. [후보 Schema](analysis-refresh.schema.json)와 [합성 요청·응답](analysis-refresh.examples.json)을 함께 작성했다. 이전 조사 단계의 요청역할/강제확정·선택후재수집·TTL cached성공 및 별도 nonnull 성공값 fallback 제안은 후보1에 포함하지 않는다.

단일 batch POST·양역할 version 입력/감지 역할CAS, 수집성공한 저수치·세팅error·명시null 최신저장, 최신head+detail 단일 version, 새관찰/동시fresh합류·ACK복구, reserve0 미시도와 결과불명 구분을 명시했다. 현재 실행 API/OpenAPI·DB/키 변경 없이 제안 문서만 작성했다. 현재 head와 옛 역사 snapshot의 자료정리 영향은 후보1 영향표를 따르며 실제 초기화 승인이 아니다.

## 비로그인 계약 — 기존 API 재사용

사용자는 **공개 요약 + 기능 예시**를 선택했다. 실제 회원 전용 상세를 guest에 공개하는 API 확장은 이번 안에 없다.

| 대상 | 현재 사용할 API·범위 | 금지/로그인 경계 |
|---|---|---|
| 모집 목록/필터 | POST `/v2/raid-rooms/search?response_profile=discovery-1`, OptionalPrincipal. 공개 가시성·카테고리/레이드/난도·경험·남은 자리·출발/일정 상태·인원순 정렬·현재/다음 실제 주차·총개수/cursor를 기존 의미로 소비한다. | group_ids/그룹원 조건·filter/candidate token은 회원 전용. 비로그인에는 공개 조건만 보내고 /me context·후보를 호출하지 않는다. 로그인/로그아웃 후 cursor는 공유하지 않고 목록을 새로 조회한다. |
| 모집 카드 | GET `/v2/raid-rooms/{room_id}?target_cycle_key=…`도 OptionalPrincipal이나, 목록 표시만 위해 카드별 GET을 추가하지 않는다. discovery 카드의 제목/레이드/정원/인원/전투력 조건/일정 요약/공개 대표와 target 식별자를 사용한다. | discovery의 view_detail_permission은 guest에 allowed=false/AUTH_REQUIRED. UI가 이를 실제 `/detail` 허용으로 해석하지 않는다. 요약을 펼치거나 가상 기능 예시로 설명한다. 실제 /detail·plan·내 참가/신청은 인증 유지. |
| 그룹 둘러보기 | GET `/v1/groups?q=…&limit=…&cursor=…`, GET `/v1/groups/{group_id}`는 인증 없는 public summary다. group_id/name/revision/member_count/대표와 상태/공개 leader_display만 사용한다. | 전체 회원 목록·활동 캐릭터·내 그룹·관리·그룹 모집 내부 조회는 회원/그룹 권한 유지. 공개 summary에 내부 자료를 붙이지 않는다. |
| 기준 자료 | GET `/v1/raid-catalog`, `/v1/raid-cycle`는 패키지 카탈로그와 서버시각만 사용한다. 키·provider·업무 DB 쓰기 없이 읽는다. | 분석 카탈로그까지 이 endpoint가 제공한다고 가정하지 않는다. |
| 내 계정/관리 기능 소개 | Native 고정 가상 예시, 최신 실제 UI 구성요소 공유. 예시임을 표시하고 DB/외부 API/쓰기/가짜 회원 세션0. | 로그인 때 실제 자료로 전환, 로그아웃 때 예시 복귀, 지연된 개인 응답 폐기. 예시 동작을 로그인 후 자동 실행하지 않는다. |

소스 근거: [cycle router](../../../../app/raid_rooms/api/cycle_router.py), [SQL 검색/페이지](../../../../app/raid_rooms/reads/cycle_queries.py), [discovery 카드](../../../../app/raid_rooms/reads/discovery.py), [그룹 public router](../../../../app/groups/router.py), [그룹 공개 schema](../../../../app/groups/schemas.py), [raid service](../../../../app/raids/service.py). HTTP POST 검색은 읽기이며 로아 provider quota와 무관하다. 전체 UI 레이아웃은 같아도 서버 권한/개인 조건/자료까지 같아지는 것은 아니다.

## Native 전체2 수신·다음 Backend 명세 작업

[전체2 Native — 규칙·자료·상세 필드 설계 인계](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6909842470)를 본문 제외 실제2번째로 확인했다. 기능코드/시험 변경은 없다는 Native 보고이며 새 소비 SHA 없음·로컬 미커밋/미push다. 단일 서버 키·분석 출처, 공개요약/예시, 최대50/20초·부분독립과 기존 읽기 확장을 수용했고 위 의미를 수정했다. 이 단계는 양측 정확 명세 합의 완료가 아니다.

고정 자료는 Flutter `302243fb7474e548c4eb722a1a40759274528322`의 character_build_analysis_mapper/gem_tooltip_class_extractor, scoped_role_build_mapper, character_build_role_policy/build_integrity_snapshot_mapper, 분석 game_catalog.v1.json과 mapper/entity/validator, NiceGroupPolicy와 projectScopedRefreshTargets다. Backend는 [scoped mapper](https://github.com/heo0328/LostParty_flutter/blob/302243fb7474e548c4eb722a1a40759274528322/lib/features/account/data/mappers/scoped_role_build_mapper.dart)와 [role policy](https://github.com/heo0328/LostParty_flutter/blob/302243fb7474e548c4eb722a1a40759274528322/lib/features/account/domain/services/character_build_role_policy.dart)를 원격에서 확인해 선호역할 fallback 없음·수치/시각·issue 매핑을 대조했다. 나머지 source/fixture의 세부 대조는 구현 전 포팅/동등성 구간에서 수행하며 미검증을 유지한다.

비민감 입력은 [겸용8계열 정의](https://github.com/heo0328/LostParty_flutter/blob/302243fb7474e548c4eb722a1a40759274528322/test/fixtures/lost_ark/support_hybrid_builds_user_reference.json)와 [합성 builder 시험](https://github.com/heo0328/LostParty_flutter/blob/302243fb7474e548c4eb722a1a40759274528322/test/features/account/data/mappers/character_build_analysis_mapper_test.dart)의 _hybridBuildFixture다. character_armory_full.json/live foreign-class raw는 제외하며 measuredAgainstLiveApi 표시는 새 Python/운영 검증 통과가 아니다. 새 golden/동등성 시험은 아직 없다. 제공된 자료를 다시 요청하지 않는다.

상세 projection 요구: 계열판정 status/id/표시명·감지역할·tier1/관련노드, rune_count/gem_count/source가용성, 보석 slot/level/target/설명/category/검증status, grid 이름/grade/point/최소·권장/조건text/필요·누락node, notice code/severity/표시자료다. summary/detail은 같은 UUID/role/version/관찰시각을 가리키며 새 기기에서도 저장 projection GET으로 읽는다. 전체 tooltip/raw는 반환하지 않는다. 숫자 표시 반올림/문구·시각 표현/반응형은 Native 책임이다.

Backend는 아래 항목을 후보1 명세로 작성했다. (1) 양역할 version 입력·감지 역할 CAS·정확 요청/응답/오류, (2) 수집 상태/업무 성공/세팅 integrity·null/실패 구분, (3) 미시도 reserve0·같은ID 후속/결과불명 복구·종결 결과 재시도, (4) 수동 fresh/동시 합류, (5) 상세 저장·GET과 요약 일치, (6) API/DB/역할 비교·옛 경로 제거 영향표를 고정 제안으로 회신한다. repo 문서는 현재 미게시이며 새 고정 소비 SHA가 없음을 유지한다. commit/push 승인을 Native 요청에서 추론하지 않는다.

## 구현 순서·검증안·완료 조건

이번 순서: Backend 조사/최소 계약 회신 → Native 대조/fixture·필드 제공 → Backend 최종 계약/삭제·저장 영향표 → 양측 합의. 미합의 필드를 현재 OpenAPI에 넣지 않는다. 이번 회신으로 Issue 종료/전체 기능 완료를 표시하지 않는다.

합의 후 구현 단위는 (1) Native 공통 UI·공개 탐색·고정 예시, (2) Backend 서버 키·모든 호출자/worker·분석/읽기/저장 계약과 Native 새 업무 요청 연결, (3) 양측 개인키/직접분석/옛 업로드·전용 의존성 제거와 통합 검증이다. 같은 목적 브랜치에서 이어가며 중간 단위가 최종 이중 경로 유지의 근거가 되지 않는다. 앱 공개는 새 계약/앱을 함께 소비할 준비가 된 뒤 별도 결정한다.

| 검증 묶음 | 확인할 동작 |
|---|---|
| 공개·예시 | guest 검색/필터/정렬/페이지/현재·다음주/그룹 summary·카탈로그, private401/403, provider0·쓰기0·예시 세션0. 로그인 전후 cursor/개인 응답 격리·웹 F5/뒤로가기·Android 복귀는 Native 담당. |
| 서버 수집 | 키 미설정/거절/교체·timeout·대형/불량 응답·전체 quota/상위429·Retry-After·중복 합류/lease takeover. HTTP와 소유권 worker 모두 같은 키 공급/제한 사용, 일반 GET은 provider0. |
| 분석·사용자 결정 | 공통 fixture 결과 동등성·수치/반올림·양역할 독립·나이스단 OFF/명시 수동 갱신·선호역할 비개입·고→저/세팅error 최신저장·source null/실패 구분·상세 projection과 요약 일치. |
| 업무 정합성 | 수집 중 소유/등록/수명 변경·삭제/누락·권한 상실 시 저장 차단, 활동/대표 불변, 현재 명령 CAS·중복/응답유실·부분 결과/예산 초과·늦은 결과 미저장. 분쟁 lease/기한/활성 참가 보류 유지. |
| 제거·계약 | 삭제 대상 import/router/model/설정/배포·도구·시험 참조0, 개인키/클라이언트 summary 쓰기 경로가 최종 앱에 없음, 기존 기능 권한 회귀. 합의 변경 후 현재 OpenAPI 전체 비교·저장구조 검증·로컬 실제 지원을 구분해 기록. |

현재 수행한 검증은 정적 조사와 문서/링크·diff 검사다. 새 기능 시험·실제 provider·DB·기기·운영 인수는 수행하지 않았다. 키 설정/DB 구조 변경을 실행하는 단계에서는 [백업 원장](../../../engineering/operations/backup-and-recovery.md)의 대응 파일·보관 안내를 적용한다. 지금 새 키·사본·자료 삭제는 만들지 않는다.

[전체1 Backend 조사·설계 제안 회신](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6909472129) 게시 후 실제 전체 댓글1개/대상ID를 재조회했다. Backend 1차 조사 이력이다. 이후 전체2 Native 수신으로 다음 담당은 후보1 명세 인계 뒤 Native exact wire/영향 대조이며 기능 구현/양측 합의 완료가 아니다.

[전체4 Backend 최종계약 후보1 인계](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6910288469) 게시 완료. 다음 Native exact wire/저장·제거 영향 대조 대기이며 기존 전체1/2/3은 조사·수정 이력으로 유지한다.

현재 다음 담당·회신 링크는 [NEXT_WORK](../../../project/NEXT_WORK.md), 누적 결과는 [DEV_LOG](../../../project/DEV_LOG.md)를 따른다.


[전체5 Native 설계 수용](https://github.com/heo0328/lostparty-backend/issues/55#issuecomment-6910545522) 수신·Backend 동일계약 확정. 이전 검토대기/후보 표현은 조사 당시 이력이며 현재는 공동설계 완료·기능 미착수다. 정확 기준과 다음 구현 단위는 [계약7절](analysis-refresh-contract.md#7-공동-설계-확정구현-단위)을 따른다. Schema/examples 변경 없음.
