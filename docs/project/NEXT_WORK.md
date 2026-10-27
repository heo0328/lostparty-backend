# 다음 실행

## 현재 기준 — 모집 재신청 보완 dev 통합 완료

사용자 승인으로 [수정·검증·반영·인수 기록](../features/recruitment/reapplication-integration-2026-10-27.md)을 최신화했고, 문서 구간eb8c409를 게시한 뒤 [PR28](https://github.com/heo0328/lostparty-backend/pull/28)의 `41a47ed2ae0a0e2e4d6356b885bfd6a589b048aa`로 dev 병합·원격 확인을 완료했다. PR head와 병합 결과 파일 전체가 동일하고 구현c1f86d8 이후 코드/DDL/계약·시험 소스 변경이 없음을 확인했다.

현재 checkout은 `dev`다. 통합 완료한 `fix/raid-recruitment-reapplication`은 로컬/원격 삭제했고 미완료 `feat/activity-selection`은 보존했다. 레이드 모집 1차 구현·보고된 정상 흐름/표시의 사용자 기기 인수와 [Issue13 closed/completed](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)는 완료다. main은18830c2 유지이며 이번에는 dev만 통합했다. 후행 문서 마감 기록도 dev에 commit/push한다. 서버/DB 재실행·AWS 배포·다른 Issue 종료는 없다.

## 개발 실행·검증 기준

현재 개발 API sourcec1f86d8/이미지581a1a5e·DB0033·현재178/199/기본116/133. [재신청 구현](../features/recruitment/participation/reapplication-history-fix-plan.md)·[개발 반영](../engineering/operations/reapplication-history-rollout.md)·[공개 집계](../engineering/operations/records/reapplication-history-rollout.json)를 따른다. 고유 격리20PASS, 실행262소스/runtime31/두 계약·HTTP6·READONLY 목록/한도2계정 일치·anchor34/종료근거13·health/주기작업 확인이다. DDL 전후112업무표1,883행/sequence와 기존 DB/환경/키/API 설정을 보존했다.

이번은 코드/DB/계약을 바꾸지 않는 Git 통합/문서 정리다. 기존 기능·실행 검증을 재사용하며 문서 참조/diff·원격/포함 관계를 확인한다. 전체 회귀/DB 복원·실회원 명령·서버 재시작은 반복하지 않는다. DB33에서 구420 API만 단순 복귀하지 않고 자료·구조 유지 전진 수정이다.

## 다음 기능 작업·차후 보완

현재 추가 Backend 구현·시험 요청은 없다. [전체190 Native 인수/후속](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437933418)과 [전체191 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437976324)의 정밀도 소비·개방 알럿·제안 발견성/소켓 등은 [차후 보완 대장](../features/recruitment/follow-up-backlog.md)에 담당·재착수 조건으로 보존했다. 현재 착수/인수 선행 조건이 아니며 사용자와 별도 구간을 재시작할 때 최신 계약/코드·UX 및 새 주제 Issue를 확인한다.

다른 그룹·V2 분쟁·생명주기·활동 선택/통계 등의 열린 주제는 [ISSUE_TRACKER](ISSUE_TRACKER.md)를 따른다. 이번 통합으로 다른 Issue를 종료하거나 새 기능을 시작하지 않는다. IF-001/002/003 비활성·구명령/자료/원pending·ACK 보존과 별도 성능/실회원 원ACK 키 검증·출시 경계는 유지한다. Native 시험 순서와 구현 내부 이력은 Native가 관리한다. 과거 완료/결정/오류·사용자 정정은 [DEV_LOG](DEV_LOG.md)에 누적 보존한다.
