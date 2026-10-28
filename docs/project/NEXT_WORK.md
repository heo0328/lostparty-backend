# 다음 실행

## 현재 기준 — 그룹 1차 계약 제안

브랜치/checkout은 `feat/group-management`이며 main/dev의 공통 출발점은 `1b6f57b`다. 그룹 준비 `ea52e56` 이후 이번 구간은 **기획·API 설계 문서와 Issue 제안 게시**이며 기능코드/DDL/실행 OpenAPI는 변경하지 않는다. 기존 수신 확인의 로컬 기록도 이 설계 구간에 함께 모은다.

기준은 [#12 전체19번째 Flutter · 표시 조회 개발 요청](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6464116834), [#16 전체9번째 Flutter · 관리 1차 개발 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464117245), 원격 고정설계 f04f482e·제품 그룹정책/모집37이다. 현재 코드와 대조한 [표시 조회 제안](../features/groups/discovery/display-contract-proposal.md)·[관리/레이드 제안](../features/groups/management/phase-one-contract-proposal.md)을 기준으로 이어간다. 게시 결과와 실제 댓글 순번은 아래 인계기록 및 DEV_LOG에 남긴다.

## 다음 실행 — 제안 계약 대조 후 구현 구간

- Backend: 같은 그룹 목적 브랜치에서 위 두 제안·최신 Issue 회신을 확인한다. 이번 사용자 지시는 설계까지이므로 현재 새 기능 구현/서버반영을 시작하지 않는다. 다음 구현 구간에서는 확정 범위부터 코드/최소 migration/두 OpenAPI·직접경계 검증을 진행하고 UI시안·단순소비회신을 전체 선행조건으로 두지 않는다.
- Flutter: #12에서 조회profile/스펙·보석 표시/활동목록/정확한배지 소비 차이를 대조한다. #16에서는 그룹장의 비참가 방관리를 기존1인해산 제한에 연결한 범위를 대조한다. 다인 방 강제종료까지 뜻한다면 정책차이로 분리한다. 기초/동일코드 반복시험 요청이 아니다.
- 자격상실/복구: 사용자는 모든 인증소유권 상실을 그룹 자격상실로 확정하지 않고 **정책 미정으로 분리**했다. 회원disabled/대표문제/소유권상실·유효후임/후임없음복구 질문만 #16에 남긴다. 다른 그룹 기능 전체를 대기시키지 않는다.
- 기존 그룹탈퇴/추방/소멸 후 레이드관계/진행/완료/기록은 보존하고, 신규 그룹 검색/참가/신청은 별도 검사한다. 기본15/5·유효한도·그룹자체 정원초과 제한과 원ACK/재가입 보호는 유지한다.
- 미완료 `feat/activity-selection` 로컬89a3248/3개 문서커밋은 보존한다. 활동 자동추가·명시제외는 Native 확인 후 별도 재착수한다. Issue 종료·merge·서버/DB재실행·배포/자료변경은 이번에 없다.

## 개발 실행·검증 기준

현재 개발 API sourcec1f86d8/이미지581a1a5e·DB0033·현재178/199/기본116/133. [재신청 구현](../features/recruitment/participation/reapplication-history-fix-plan.md)·[개발 반영](../engineering/operations/reapplication-history-rollout.md)·[공개 집계](../engineering/operations/records/reapplication-history-rollout.json)를 따른다. 고유 격리20PASS, 실행262소스/runtime31/두 계약·HTTP6·READONLY 목록/한도2계정 일치·anchor34/종료근거13·health/주기작업 확인이다. DDL 전후112업무표1,883행/sequence와 기존 DB/환경/키/API 설정을 보존했다.

이번은 코드/DB/실행계약을 바꾸지 않는 그룹 설계 문서 작업이다. 기존 기능·실행 검증을 재사용하며 문서 참조/diff·원격/포함 관계를 확인한다. 전체 회귀/DB 복원·실회원 명령·서버 재시작은 반복하지 않는다. DB33에서 구420 API만 단순 복귀하지 않고 자료·구조 유지 전진 수정이다.

## 다음 기능 작업·차후 보완

모집 관련 추가 Backend 구현·시험 요청은 없다. 그룹 신규 요청과 분리한다. [전체190 Native 인수/후속](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437933418)과 [전체191 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437976324)의 정밀도 소비·개방 알럿·제안 발견성/소켓 등은 [차후 보완 대장](../features/recruitment/follow-up-backlog.md)에 담당·재착수 조건으로 보존했다. 현재 착수/인수 선행 조건이 아니며 사용자와 별도 구간을 재시작할 때 최신 계약/코드·UX 및 새 주제 Issue를 확인한다.

다른 그룹·V2 분쟁·생명주기·활동 선택/통계 등의 열린 주제는 [ISSUE_TRACKER](ISSUE_TRACKER.md)를 따른다. 이번 준비로 다른 Issue를 종료하지 않으며 그룹 구현은 다음 구현 구간에서 제안/정책 차이를 확인한 뒤 진행한다. IF-001/002/003 비활성·구명령/자료/원pending·ACK 보존과 별도 성능/실회원 원ACK 키 검증·출시 경계는 유지한다. Native 시험 순서와 구현 내부 이력은 Native가 관리한다. 과거 완료/결정/오류·사용자 정정은 [DEV_LOG](DEV_LOG.md)에 누적 보존한다.
