# 다음 실행

## 현재 기준 — 그룹 1차 계약 제안

브랜치/checkout은 `feat/group-management`이며 main/dev의 공통 출발점은 `1b6f57b`다. 그룹 준비 `ea52e56` 이후 이번 구간은 **기획·API 설계 문서와 Issue 제안 게시**이며 기능코드/DDL/실행 OpenAPI는 변경하지 않는다. 기존 수신 확인의 로컬 기록도 이 설계 구간에 함께 모은다.

기준은 [#12 전체19번째 Flutter · 표시 조회 개발 요청](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6464116834), [#16 전체9번째 Flutter · 관리 1차 개발 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464117245), 원격 고정설계 f04f482e·제품 그룹정책/모집37이다. 현재 코드와 대조한 [표시 조회 제안](../features/groups/discovery/display-contract-proposal.md)·[관리/레이드 제안](../features/groups/management/phase-one-contract-proposal.md)을 기준으로 이어간다. 게시 결과와 실제 댓글 순번은 아래 인계기록 및 DEV_LOG에 남긴다.

## 게시·인계 상태

설계 고정 SHA `92c1702f84720ce76789f100bf0acdb1efd29c82`를 같은 그룹 브랜치에 commit/push하고 원격 일치를 확인했다. [#12 전체20번째 Backend · 표시조회 계약 제안](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6464713065)과 [#16 전체10번째 Backend · 관리/레이드 계약 제안](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464713503)을 게시하고 실제순번/내용을 재조회했다. 양 Issue 본문 상단은 현재범위·설계제안/구현미완료·다음담당으로 갱신하고 과거본문을 보존했다. Issue는 OPEN이다.

이번 문서검사·예시JSON4개·diff검사는 통과했고 기능시험/서버반영·Flutter기기인수는 미실행이다. 후행 게시/링크 기록도 이 목적 브랜치에서 보존한다. 다음 담당은 Flutter의 구체소비/정책차이대조와 Backend 명세보완·차기구현준비다.

## 최신 Native 회신 — 그룹원 개설·레이드 공대장 관리 확정

[#12 전체21번째 Flutter · 표시계약 검토](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6464852611)는 현재 제품 차단충돌없음을 확인했다. gemValidationSnapshot/integrity displayLabels의 동등표시는 실제DTO 인계때 대조하며 저장없는 보석정상합성·개인정보확대는 하지 않는다. Native1차시안/7eeca229 자체보고는 사용자검토전이며 기능/기기인수아니다.

[#16 전체11번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464853005)의 마지막1인/다인해산 질문대기는 [전체12번째 Flutter · 사용자확정정정](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6464943488)으로 해소·대체됐다. **그룹원 누구나 현재 조건으로 그룹전용 레이드를 개설하고 해당 레이드 공대장이 관리한다. 그룹장 지위의 비참가 command-context/make-public/end는 개발범위에서 제외한다.** 그룹장 이전은 레이드 공대장을 바꾸지 않는다. 기존 제안의 해당경로/DTO·토큰·시험을 같은 문서에서 교체한다.

정정 설계 `cb9b6b9` commit/push·원격확인 후 [#16 전체13번째 Backend · 설계정정 결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6465101118)에 회신했다. 실제전체순번/본문을 조회하고 Issue상단도 최신확정/다음담당으로 갱신했다. 구현/서버반영은 미완료이며 양Issue OPEN이다.

## 다음 실행 — 정정 설계 기준의 구현 구간 준비

- Backend: 현재 승인범위는 설계/정정회신이며 기능구현/서버반영을 시작하지 않는다. 다음구간은 표시/활동/배지·그룹해산/추방/대표변경·활성방공통목록과 기존레이드보존의 확정범위를 같은브랜치에서 구현·검증/인계한다. UI시안/단순소비회신은 전체선행조건이 아니다.
- 그룹해산의 실제활성전용방없음 검사는 유지한다. 공통목록에서 방/실제T 공대장을 안내하고 각 레이드공대장이 기존상세에서 정리한다. 그룹장이 다른 공대장 방을 대신 공개전환/강제해산하지 않는다. 실패/불명확=0건금지·원ACK·C/N독립·기존공대장해산조건 유지.
- Flutter: 실제 DTO 인계때 남은 보석/분석 표시매핑을 대조한다. 1인대다인해산 권한질문은 더이상 대기항목이 아니다. G-RECOVERY(회원disabled/소유/대표문제·유효후임/후임없음복구)만 별도미결정이며 독립기능을 막지 않는다.
- 그룹탈퇴/추방/소멸후 기존레이드접근/진행/완료/기록보존·신규그룹접근차단·기본15/5·정원초과제한·공개왕복/소속배지는 유지한다.
- 미완료활동선택로컬89a3248은보존한다. 서버/DB/실행OpenAPI/기능시험·배포·자료변경·Issue종료/merge없음.

## 개발 실행·검증 기준

현재 개발 API sourcec1f86d8/이미지581a1a5e·DB0033·현재178/199/기본116/133. [재신청 구현](../features/recruitment/participation/reapplication-history-fix-plan.md)·[개발 반영](../engineering/operations/reapplication-history-rollout.md)·[공개 집계](../engineering/operations/records/reapplication-history-rollout.json)를 따른다. 고유 격리20PASS, 실행262소스/runtime31/두 계약·HTTP6·READONLY 목록/한도2계정 일치·anchor34/종료근거13·health/주기작업 확인이다. DDL 전후112업무표1,883행/sequence와 기존 DB/환경/키/API 설정을 보존했다.

이번은 코드/DB/실행계약을 바꾸지 않는 그룹 설계 문서 작업이다. 기존 기능·실행 검증을 재사용하며 문서 참조/diff·원격/포함 관계를 확인한다. 전체 회귀/DB 복원·실회원 명령·서버 재시작은 반복하지 않는다. DB33에서 구420 API만 단순 복귀하지 않고 자료·구조 유지 전진 수정이다.

## 다음 기능 작업·차후 보완

모집 관련 추가 Backend 구현·시험 요청은 없다. 그룹 신규 요청과 분리한다. [전체190 Native 인수/후속](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437933418)과 [전체191 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437976324)의 정밀도 소비·개방 알럿·제안 발견성/소켓 등은 [차후 보완 대장](../features/recruitment/follow-up-backlog.md)에 담당·재착수 조건으로 보존했다. 현재 착수/인수 선행 조건이 아니며 사용자와 별도 구간을 재시작할 때 최신 계약/코드·UX 및 새 주제 Issue를 확인한다.

다른 그룹·V2 분쟁·생명주기·활동 선택/통계 등의 열린 주제는 [ISSUE_TRACKER](ISSUE_TRACKER.md)를 따른다. 이번 준비로 다른 Issue를 종료하지 않으며 그룹 구현은 다음 구현 구간에서 제안/정책 차이를 확인한 뒤 진행한다. IF-001/002/003 비활성·구명령/자료/원pending·ACK 보존과 별도 성능/실회원 원ACK 키 검증·출시 경계는 유지한다. Native 시험 순서와 구현 내부 이력은 Native가 관리한다. 과거 완료/결정/오류·사용자 정정은 [DEV_LOG](DEV_LOG.md)에 누적 보존한다.
