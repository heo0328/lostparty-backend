# 현재 작업과 다음 실행

기준일 2026-10-17. **현재 사용하던 로컬 개발환경과 개발자료로 개발을 계속한다. 완료한 앱 실행·Google 로그인·키/설정·캐릭터 갱신·원정대 저장과 #8 구현을 유지한다. 새 환경 채택·초기 설정·기본 기능 전체 재인수로 되돌리지 않는다.**

최상위 실행 기준은 [긴급 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428)이다. [Backend 실행 기준 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207867594)도 게시했다. 이전 [통합 정리](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207398915)의 새8001 채택/기초 재인수 순서와 이를 수용한 Backend6207472610은 철회된 순서다.

## 유지할 완료 결과와 현재 상태

| 구간 | 상태 |
|---|---|
| 통합 기준 | dev `821c758`, main `e6c72e4`. #1~#7 CLOSED. #8은 dev/main 미통합 |
| #8 Backend | 대표 `cd3e003`, L1a/L1b `6f3d029`/`c91af2e`, P1/P2 `6e4f625`/`7027f0b` 구현·격리검증·원격 인계 완료. P2 계약 유지 |
| 현재 작업 브랜치 | `feat/representative-selection`, 준비구현 `4bdaea6`, 권한/비노출 `59b8c23`·활동1700 `47a2ce4`·인증대상검사 `78d3d1a`·인증이력 `ccd2e6a`·장비증거 `13d9f68`·본인목록 `3c8e799`·인증선택/재인증 `cc372bf` push·[최신 결과 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6216253151) 완료 |
| 사용하던 개발환경 | 기존 Docker/포트8000/DB 자료를 유지해 0007~0010·최신 API 반영 완료. DB0010·API/DB healthy·health ok·OpenAPI 전체일치·기존 전 테이블의 원래 컬럼/행 내용 동일 확인. 초기화/새환경 전환 없음 |
| 별도8001 환경 | 구성했던 작업 이력이며 현재 개발의 기본 경로/채택 대상/선행조건이 아니다. 이번 정정으로 컨테이너/volume을 삭제·재설정하지 않는다 |
| Flutter 최신 | [기존관리/초기대표/인증전환 연결](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209931176)·[Backend검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209973965) 완료. 최신99번째전체1579PASS/분석0보고·자동목록선행연결/ON경로구현/기본OFF·미게시·실인증1회완료/복귀새UI실기기미확인. feature/scoped-account-cache/HEADcc6a0b0 위 미커밋·미push·dev미반영. 앱재실행을넘는미확정원명령종결보장은미확인 |
| 소유 증거 | [서버 장비 해제 연결](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md)로 신규/claim충돌 없음의 검증·소유생성 경로 구현. 현재본인등록재인증/타소유pending도전까지구현·소유이전/퇴역은별도보류, 이번 대상 실제1회인증성공은 [98번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6217275533)로 확인·전체/다른대상 인수와 구분 |

## 최신 사용자 채택 정책과 재검토 결과

[정책6208967265](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208967265): guest는 기본 로컬조회만, 로그인 미인증은 조회용Registration 저장/복원 유지·전투력/상세 제한, 소유인증 후 본인 상세/역할저장 및 별도 활동subset/대표 명시저장. 검색 주액션 ‘인증하고 사용하기’/보조 ‘조회 목록에 저장’. DB/캐시삭제 없이 비노출 처리한다. [Backend 현재차이 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208988839): 미인증power refresh/replay 및 V1/V2 preview cache노출의 서버권한/응답 변경 필요. 소유profile/역할저장은 기존권한을재사용한다. [Backend 구현](../ISSUE_8_BASIC_ACCESS_DEVELOPMENT.md): 미인증/소유상실power 갱신/replay403·목록/preview 과거수치 비노출 완료, 격리256PASS·기존8000 반영·`59b8c23` [인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209379848) 완료. Flutter R1 소비값과 일치하며 paths/DTO/enum불변·OpenAPI 정책3항목 보완. 실제소유증거구현과별개다.

[Flutter6208744179](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208744179): 등록/인증UI는 있으나 registration_id 사전선택·인증성공→E2 전환/전체활동편집 미연결, E1 GET revision에의한pending해제·넓은오류종결판정·재진입미보존 보완필요. 기존질문반복없이 실제보완결과를대기한다.

## 최신 협업 순서

본문 제외 순번: 102번째 사용자최신정책 → 103번째 Flutter선행UX/56PASS → 104번째 Backend검토 → **[105번째 Backend 구현/계약 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228173800)**. 구현 `19c2dcc33630078fa0d88a1dd60e11857a44472b`·feat/representative-selection commit/push/원격일치·격리483PASS·기존8000/API·DB healthy/health ok·전체OpenAPI일치/DB0010·기존소유유지확인. 현재본인유효인증의등록/direct start·pending확인은409 ALREADY_VERIFIED,타회원/소유상실도전·완료replay/현재GET유지. 같은회원삭제후재등록은확인가능한기존account에201 owned로재연결·소유/ID/감사보존/새활동설정unconfigured다. **다음담당Flutter: 서버ALREADY/등록201 owned·기존복구분기 소비/필요한구간검증 회신 대기**. 실제새정책/삭제재등록의기기확인은미실행·반복실인증요청없음·dev/main미통합/운영배포없음. 반영시기존개발DB중지상태를동일컨테이너start로해소했으며초기화/삭제없음.

## 기존 Flutter 장비 인증 재사용 설계 — 최신 회신 검토

**후속 완료:** 아래 이력 누락 차이는 [실행 이력 구현](../ISSUE_8_VERIFICATION_HISTORY_DEVELOPMENT.md)으로 보완·검증·기존8000에 반영했다. 후속 [서버 장비 해제 연결](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md)을 구현했다. 기존 ID 연속성/타소유 연결과 실제 게임 인수는 별도다.

[67번째 Flutter 기존 구현 자료 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6210605354)을 수신하고 [68번째 Backend 검토 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211222550)를 게시했다. 자료 대기는 해소됐으며 **다음 담당은 Backend 설계·구현**이다. 기존 Flutter `8f4209deb980660e227134bf1241677875d02e06`의 기준6부위·무작위1~3부위 해제·Type/Name/Grade 비교·10분·명시 재확인 흐름을 활용한다. 과거 Android 사용자 인증 성공 기록은 제품 경험으로 수용한다. 현재 Backend live 성공/원본 응답·정확한 반영시간은 미확인이며 사용자 실게임 관찰은 나중이다.

현재 서버 장비 비교/대상 고정/회원·기한/횟수 저장은 재사용한다. **우선 보완은 타소유 도전 이력**이다. 현재 claim 존재/binding 부재 시 start가 Verification 생성 전에 거절될 수 있어 시작·당시 소유/요청 회원·대상·결과가 누락된다. 기존 성공 Audit/확인 횟수만으로 모든 도전/실패 이력이 갖춰졌다고 볼 수 없다. 기록할 사전 거절/provider 실패·중복 명령·소유관계 snapshot 최소 범위를 설계한 뒤 live 장비 증거 발급 연결을 진행한다. 최종 권한 반영까지 만료 경계도 해당 구간에서 점검한다. 미합의 API/DDL/상태는 추가하지 않았다.

현재 캐릭터 제어 확인과 과거 원정대/캐릭터 ID 연결·소멸 확정은 별도다. 10분 장비 challenge와 24시간 운영자 수동 분쟁 방어를 합치지 않는다. 후자는 기존 의미만 설계 근거로 보존하며 새 분쟁 API/통지·자동 이전을 임의 구현하지 않는다. 새 UI/반복시험·Firebase 자료 이관·환경 전환은 요청하지 않았다.

## 핵심 데이터 정의 — 79번째 보충

[79번째 Flutter 정의](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213474915)·[80번째 Backend 코드 대조](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6213521483): 앱 회원1명은 실제 게임 원정대 여러 개를 등록/인증한다. 실제 소속 전체 목록은API기준이며 앱의임의캐릭터그룹/활동선택/표시개수와다르다. 서버는최소요약/설정을저장해반복provider호출을줄인다. 기존목록GET은DB만읽고provider를호출하지않으며유지한다. 실제provider갱신은앱실행회원별1회등합의시점에수행하고이후저장자료를사용한다. 전체Armory원문/Firebase자료이전없음. 78번째Backend구현→Flutter자동연결순서/사용자결정대기해소는그대로다. 이번은검토이며새owned refresh구현완료가아니다.

## 다음 개발과 담당

1. **다음 — Flutter 공개오류/등록복구 응답 소비.** [현재 소유자 정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md)을구현해본인등록/direct start·기발급pending확인의현재유효소유를409 ALREADY_VERIFIED로차단한다. 타회원/소유상실도전·기존완료replay/현재GET은유지하며동일회원삭제후재등록은기존등록POST/201에서확인가능한기존account로복구한다. owner/verified_at/ID/소유·rosterrevision/감사보존·새활동/대표unconfigured. 최종격리483PASS·기존8000반영/실행계약·health·DB0010/기존소유유지확인,[105번째 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6228173800)/구현19c2dcc로Flutter가서버ALREADY(검색/동시변경/기발급pending포함)와등록201 owned를소비한다. 실제기기의새정책/삭제재등록은미확인·반복실인증요청없음.
2. **Flutter 기존 관리 화면 연결·초기 대표 정책 대조.** [사용자 UX 정정6209360031](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209360031): 기존 CharacterManagementPage/ViewModel을 회원/등록/canonical·저장 API에 연결한다. 별도선택/복구화면을추가하지않으며미확정명령일관성은내부처리한다. 현재대표는유지·없을때만사용가능캐릭터최고item level로초기1회선정·공통사용기준1700. 전체활동자동추가/메인전환없음. [서버활동검증](../ISSUE_8_ACTIVITY_SELECTION_DEVELOPMENT.md)은전체선택/대표변경1700기준·ineligible보고·선택보존을구현해격리192PASS·기존8000반영·`47a2ce4` [인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209623492) 완료했다. 초기후보는Flutter기존관리화면에서최고레벨draft를정하고활동집합/대표를기존PUT/CAS로명시저장하는연결을 [대조요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209535500)했고 [연결완료보고](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209931176)/최종1560PASS와 [검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209973965)를수신했다. 원격게시/실소유/ON실인수는미확인이다. 서버읽기/refresh/null입력자동선정은추가하지않았다. 최신정정은기존별도E2화면/복구UX선행설명을대체한다.
3. **최초 실제 장비 인증1회는 완료됐다.** 98번째 사용자결과/서버verified·소유·감사일치를유지한다. 이번본인차단/등록복구에반복장비시험을요구하지않는다. 타회원분쟁/소유이전·다른범위인수는별도이며기존관찰CLI가완료조건을확대하지않는다.
4. **변경한 구간의 영향 검증만 수행한다.** 실제 소유/canonical·현재 등록/roster·활동 대상이 필요한 새 기능 실검증만 조건 충족 후 진행한다. 기존 완료 흐름을 처음부터 재인수하지 않는다. Flutter 변경분의 게시/통합 상태는 구현 완료와 별도로 추적한다.

## 자료 수명 기준

현재 개발자료를 유지해 개발 → 사용자 모집/베타 준비 → **사용자가 베타 시작 직전 시점을 지시할 때 대상 개발 DB의 사용자/기록 내용 초기화** → 이미 구현된 기능 동작 확인 → 큰 문제가 없으면 베타 자료를 운영에 보존한다. 지금 초기화/삭제·새 환경 채택·재설치·구자료 복사/복원을 실행하지 않는다. Firebase 전용 구현 제거는 제품 기능·현재 개발자료 제거와 구분한다. 별도8001 구성과 보존형 백업/복원 계획을 필수 절차로 확대했던 판단은 폐기했다.

## 검증 근거와 완료 경계

- Backend L1a 185PASS, L1b 113PASS/보완57PASS, P1 108PASS/최종171PASS, P2 수정후128PASS/최종143PASS는 각각 별도 격리 PostgreSQL/mock 실행이다. 실제 결과/초기 실패와 보완은 [L1](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md), [P1](../ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md), [P2](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md) 안내와 DEV_LOG가 기준이다.
- Flutter [A1](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196135272) 1432PASS, [A2](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196639685) 전체1479PASS 이후 국소47/2PASS, [B](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197379381) 전체1514PASS 이후 B35PASS, [C](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197881822) 최종전체1524PASS 보고다. 각 실행을 합산하지 않는다. 최종 lib/test 분석 문제0, 저장소 전체 analyze는 기존 사용자 tools의 info3건이 남는다. 임시 SQLite/모의 backend·provider HTTP 결과이며 Backend 자동검증/실기기 인수와 구분한다.
- 신규/claim충돌 없는 원정대의 서버 장비 검증 경로는 구현됐고 실제 게임 인수는 미실행이다. 기존ID 연결·소멸 확정/퇴역/claim 해제는 보류다. 내부 모의 retirement 정리 구현을 실제 자료 삭제·provider 전체성 증명으로 확대하지 않는다. 전체 자동 갱신의 코드 연결과 실제 운영/사용자 완료는 별도다.

## 다른 범위와 보존

#7 회원키 `9e1a255`·Flutter `8644c81`/dev `cc6a0b0` 게시·현재 구간 사용자 정상 보고와 Completed 종료는 확인 완료다. #6 회원설정 `79255f0`·Flutter `2e0764f`/dev `5cee9648` 게시·사용자3흐름·CLOSED, #5 전투력 `39188d5`·Flutter `6beb55e`/dev `ccc6b23` 게시·사용자3흐름·CLOSED다. 같은 정상 결과의 반복 시험을 요청하지 않는다.

#3/#4에서 분리한 활동/장비·삭제 후 로컬 보존, [인증 후속](../ISSUE_2_FOLLOWUP.md), 재설치/별도기기·실provider 한도/헤더·운영 TLS·탈퇴/약관·모집/파티/그룹·운영 배포는 각 후속 범위다. 완료 작업 브랜치 feat/member-settings는 정리됐으며 진행 중 #8 브랜치는 미통합이므로 유지한다.
