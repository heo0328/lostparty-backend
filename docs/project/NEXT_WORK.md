# 현재 작업과 다음 실행

기준일 2026-10-16. **현재 사용하던 로컬 개발환경과 개발자료로 개발을 계속한다. 완료한 앱 실행·Google 로그인·키/설정·캐릭터 갱신·원정대 저장과 #8 구현을 유지한다. 새 환경 채택·초기 설정·기본 기능 전체 재인수로 되돌리지 않는다.**

최상위 실행 기준은 [긴급 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428)이다. [Backend 실행 기준 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207867594)도 게시했다. 이전 [통합 정리](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207398915)의 새8001 채택/기초 재인수 순서와 이를 수용한 Backend6207472610은 철회된 순서다.

## 유지할 완료 결과와 현재 상태

| 구간 | 상태 |
|---|---|
| 통합 기준 | dev `821c758`, main `e6c72e4`. #1~#7 CLOSED. #8은 dev/main 미통합 |
| #8 Backend | 대표 `cd3e003`, L1a/L1b `6f3d029`/`c91af2e`, P1/P2 `6e4f625`/`7027f0b` 구현·격리검증·원격 인계 완료. P2 계약 유지 |
| 현재 작업 브랜치 | `feat/representative-selection`, 준비구현 `4bdaea6`, 권한/비노출 `59b8c23`·활동1700구현/계약 `47a2ce4` push·[결과 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209623492) 완료 |
| 사용하던 개발환경 | 기존 Docker/포트8000/DB 자료를 유지해 0007~0009·최신P2 API 반영 완료. DB0009·API/DB healthy·health ok·OpenAPI 전체일치·기존 전 테이블의 원래 컬럼/행 내용 동일 확인. 초기화/새환경 전환 없음 |
| 별도8001 환경 | 구성했던 작업 이력이며 현재 개발의 기본 경로/채택 대상/선행조건이 아니다. 이번 정정으로 컨테이너/volume을 삭제·재설정하지 않는다 |
| Flutter 최신 | [기존관리/초기대표/인증전환 연결](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209931176)·[Backend검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209973965) 완료. 최종전체1560PASS/분석0 보고·ON경로구현/기본OFF·미게시/실인수미확인. feature/scoped-account-cache/HEADcc6a0b0 위 미커밋·미push·dev미반영. 앱재실행을넘는미확정원명령종결보장은미확인 |
| 소유 증거 | 관찰 도구 자동65PASS/게시 완료. 실제 게임 관찰은 사용자 결정대로 나중. live 소유/canonical·퇴역은 미완료/보류. 이를 기존 기능 전체 미완료로 확대하지 않는다 |

## 최신 사용자 채택 정책과 재검토 결과

[정책6208967265](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208967265): guest는 기본 로컬조회만, 로그인 미인증은 조회용Registration 저장/복원 유지·전투력/상세 제한, 소유인증 후 본인 상세/역할저장 및 별도 활동subset/대표 명시저장. 검색 주액션 ‘인증하고 사용하기’/보조 ‘조회 목록에 저장’. DB/캐시삭제 없이 비노출 처리한다. [Backend 현재차이 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208988839): 미인증power refresh/replay 및 V1/V2 preview cache노출의 서버권한/응답 변경 필요. 소유profile/역할저장은 기존권한을재사용한다. [Backend 구현](../ISSUE_8_BASIC_ACCESS_DEVELOPMENT.md): 미인증/소유상실power 갱신/replay403·목록/preview 과거수치 비노출 완료, 격리256PASS·기존8000 반영·`59b8c23` [인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209379848) 완료. Flutter R1 소비값과 일치하며 paths/DTO/enum불변·OpenAPI 정책3항목 보완. 실제소유증거구현과별개다.

[Flutter6208744179](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6208744179): 등록/인증UI는 있으나 registration_id 사전선택·인증성공→E2 전환/전체활동편집 미연결, E1 GET revision에의한pending해제·넓은오류종결판정·재진입미보존 보완필요. 기존질문반복없이 실제보완결과를대기한다.

## 최신 협업 순서

본문을 제외한 전체댓글작성순서: **61번째 Backend 서버1700검증 인계**6209623492 → **62번째 Flutter 기존관리/초기대표/인증전환 완료보고**6209931176 → **63번째 Backend 검토완료**6209973965. 댓글순번은작업단계번호가아니다. 59번째최종정리의관리화면/초기대표/인증전환개발은후속보고로연결완료됐으며, 현재다음담당은Backend의실제소유증거/원정대연결미완료구간이다. 사용자게임관찰/실소유조건이필요한실인수만나중이며새Flutter검토답변을필수선행으로기다리지않는다. Flutter미게시/기본OFF·실인수미확인상태는별도유지한다.

## 다음 개발과 담당

1. **Backend — 실제 증거 발급/기존 원정대 연결은 미완료.** [인증 대상/목록 고정 검사](../ISSUE_8_VERIFICATION_CONTEXT_DEVELOPMENT.md)를 구현·격리250PASS·기존8000반영했다. 이는필요조건보완이며live인증활성화가아니다. 다음실제활성에는사용자장비관찰의해석/수용근거와검증된증거를server adapter가발급하는연결이필요하다. 기존원정대/캐릭터세대연결은별도연속성근거가필요하며이름/동일목록/반복조회만으로대체하지않는다. 사용자실관찰나중지시에따라이의존구간의live활성/실인수는보류한다. Flutter검토답변을다시기다리는상태가아니다.
2. **Flutter 기존 관리 화면 연결·초기 대표 정책 대조.** [사용자 UX 정정6209360031](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209360031): 기존 CharacterManagementPage/ViewModel을 회원/등록/canonical·저장 API에 연결한다. 별도선택/복구화면을추가하지않으며미확정명령일관성은내부처리한다. 현재대표는유지·없을때만사용가능캐릭터최고item level로초기1회선정·공통사용기준1700. 전체활동자동추가/메인전환없음. [서버활동검증](../ISSUE_8_ACTIVITY_SELECTION_DEVELOPMENT.md)은전체선택/대표변경1700기준·ineligible보고·선택보존을구현해격리192PASS·기존8000반영·`47a2ce4` [인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209623492) 완료했다. 초기후보는Flutter기존관리화면에서최고레벨draft를정하고활동집합/대표를기존PUT/CAS로명시저장하는연결을 [대조요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209535500)했고 [연결완료보고](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209931176)/최종1560PASS와 [검토](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209973965)를수신했다. 원격게시/실소유/ON실인수는미확인이다. 서버읽기/refresh/null입력자동선정은추가하지않았다. 최신정정은기존별도E2화면/복구UX선행설명을대체한다.
3. **실제 장비 관찰은 나중에 수행한다.** [관찰 CLI](../ISSUE_8_OWNERSHIP_READINESS.md)는 준비됐다. 관찰 결과와 서버에서 검증 가능한 증거/연결 규칙을 검토해야 하며 ready_for_review만으로 인증을 확정하지 않는다. 이 후속으로 독립 개발을 막지 않는다.
4. **변경한 구간의 영향 검증만 수행한다.** 실제 소유/canonical·현재 등록/roster·활동 대상이 필요한 새 기능 실검증만 조건 충족 후 진행한다. 기존 완료 흐름을 처음부터 재인수하지 않는다. Flutter 변경분의 게시/통합 상태는 구현 완료와 별도로 추적한다.

## 자료 수명 기준

현재 개발자료를 유지해 개발 → 사용자 모집/베타 준비 → **사용자가 베타 시작 직전 시점을 지시할 때 대상 개발 DB의 사용자/기록 내용 초기화** → 이미 구현된 기능 동작 확인 → 큰 문제가 없으면 베타 자료를 운영에 보존한다. 지금 초기화/삭제·새 환경 채택·재설치·구자료 복사/복원을 실행하지 않는다. Firebase 전용 구현 제거는 제품 기능·현재 개발자료 제거와 구분한다. 별도8001 구성과 보존형 백업/복원 계획을 필수 절차로 확대했던 판단은 폐기했다.

## 검증 근거와 완료 경계

- Backend L1a 185PASS, L1b 113PASS/보완57PASS, P1 108PASS/최종171PASS, P2 수정후128PASS/최종143PASS는 각각 별도 격리 PostgreSQL/mock 실행이다. 실제 결과/초기 실패와 보완은 [L1](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md), [P1](../ISSUE_8_ROLE_SUMMARIES_DEVELOPMENT.md), [P2](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md) 안내와 DEV_LOG가 기준이다.
- Flutter [A1](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196135272) 1432PASS, [A2](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6196639685) 전체1479PASS 이후 국소47/2PASS, [B](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197379381) 전체1514PASS 이후 B35PASS, [C](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6197881822) 최종전체1524PASS 보고다. 각 실행을 합산하지 않는다. 최종 lib/test 분석 문제0, 저장소 전체 analyze는 기존 사용자 tools의 info3건이 남는다. 임시 SQLite/모의 backend·provider HTTP 결과이며 Backend 자동검증/실기기 인수와 구분한다.
- live 소유/장비 proof·소멸 확정/퇴역/claim 해제는 보류다. 내부 모의 retirement 정리 구현을 실제 자료 삭제·provider 전체성 증명으로 확대하지 않는다. 전체 자동 갱신의 코드 연결과 실제 운영/사용자 완료는 별도다.

## 다른 범위와 보존

#7 회원키 `9e1a255`·Flutter `8644c81`/dev `cc6a0b0` 게시·현재 구간 사용자 정상 보고와 Completed 종료는 확인 완료다. #6 회원설정 `79255f0`·Flutter `2e0764f`/dev `5cee9648` 게시·사용자3흐름·CLOSED, #5 전투력 `39188d5`·Flutter `6beb55e`/dev `ccc6b23` 게시·사용자3흐름·CLOSED다. 같은 정상 결과의 반복 시험을 요청하지 않는다.

#3/#4에서 분리한 활동/장비·삭제 후 로컬 보존, [인증 후속](../ISSUE_2_FOLLOWUP.md), 재설치/별도기기·실provider 한도/헤더·운영 TLS·탈퇴/약관·모집/파티/그룹·운영 배포는 각 후속 범위다. 완료 작업 브랜치 feat/member-settings는 정리됐으며 진행 중 #8 브랜치는 미통합이므로 유지한다.
