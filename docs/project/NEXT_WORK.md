# 다음 실행

## 현재 기준 — 그룹 1차 Backend 구현·격리검증

현재브랜치/checkout은 `feat/group-management`, main/dev는공통출발 `1b6f57b`다. 승인범위는 **Backend 구현·격리검증·고정계약게시**이며 실제개발반영·Flutter연결/기기인수·merge/배포는별도다. [구현/검증 기록](../features/groups/implementation-2026-10-28.md)을기준으로이어간다.

핵심표시/활동/집계는 `d075def` push·원격확인후 [#12 전체24번째 Backend · 핵심구현인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6465656746)를게시했다. 이후같은브랜치에서관리프로필·조건부해산/추방/대표변경·공통활성방목록과기존레이드보존을구현·검증했다. 최종후보계약은기본123경로/140동작·two-cycle185/206이다. 관리구간게시/댓글링크는아래및DEV_LOG에마감기록한다.

## 최종 게시·인계

관리/전체계약 source `22b1620747707afaa87ba84223e5a2beb886f658`를 commit/push·원격일치확인했다. [#12 전체25번째 Backend · 최종핵심계약](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6466328231)과 [#16 전체14번째 Backend · 관리/레이드구현인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6466327755)를게시하고실제전체순번·작성측·본문을확인했다. 양Issue는OPEN이며서버미반영/다음담당을상단에명시한다. 이후마감기록은문서만갱신하며같은구현소스를유지한다.

## 다음 실행 — Native 계약 소비·실제개발반영은 별도

- Flutter: 고정 source/두OpenAPI·예시를소비해표시·활동캐릭터·집계·관리의구체차이를각 #12/#16에회신한다. gemValidationSnapshot/integrity labels의동등표시는실제DTO대조로남기며저장없는보석정상상태나개인자료를합성하지않는다. 현재개발서버는DB0033이므로신규API실회원/기기시험은아직요청하지않는다.
- Backend: 실제소비차이에대응한다. 개발반영이요청되면같은목적브랜치에서DB0034/후보이미지·기존DB/설정/키보존과반영검증을별도구간으로정한다. 이번소스push만으로개발서버가변경됐다고해석하지않는다.
- 핵심흐름은초대/가입→활동캐릭터확인→기존모집필터→상세/참가/신청이다. 관리/복구전체를Native독립연결의선행조건으로두지않는다. 현재membership/캐릭터는기존검색alias/context/candidate와대조하고변경후함께재조회한다.
- 그룹원누구나현재조건으로개설하고각실제T레이드공대장이관리한다. 그룹장이전은레이드권한을바꾸지않으며그룹장전용command-context/make-public/end는없다. 그룹탈퇴/추방/소멸후기존레이드진행/완료/탈퇴·기록은보존하고신규그룹접근은차단한다. 기본15/5·유효한도·정원초과제한·C/N독립/원ACK/재가입보호는유지한다.
- G-RECOVERY(회원disabled/소유/대표문제·유효후임/후임없음복구)는사용자선택에따라별도미정이다. 미완료활동선택로컬89a3248은보존하며Native확인후별도재착수한다. 웹소켓/통계/운영정리·자료삭제/초기화·운영배포는포함하지않는다.

## 검증과 실제 개발 실행 기준

실행한격리검증: 핵심선택70건의68PASS후실패2건수정/재검증PASS, 관리/G2/생명주기최종86PASS, 직접영향재신청/실제T관리회귀41PASS, 두후보OpenAPI객체전체일치·문서/JSON/diff/lock검사·호스트12시험PASS. 서로겹치는실행수를합산하지않는다. 상세실패원인/정정·최종추가경계는구현기록을따른다.

실제개발실행은기존기록source `c1f86d8`/이미지 `581a1a5e`·DB0033·현재178/199/기본116/133이다. [개발반영 기록](../engineering/operations/reapplication-history-rollout.md)·[공개집계](../engineering/operations/records/reapplication-history-rollout.json)를보존하며이번에컨테이너/DB를조회하거나교체하지않았다. 기존검증을현재신규API/기기통과로확대하지않는다.

## 다른 미완료 주제

모집1차인수/Issue13종료는유지하고차후정밀도/알럿/UX/소켓은 [보완대장](../features/recruitment/follow-up-backlog.md)을따른다. 다른Issue상태는 [추적표](ISSUE_TRACKER.md), 완료/결정/실패·게시이력은 [DEV_LOG](DEV_LOG.md)에보존한다. IF-001/002/003 비활성·원자료/pending/ACK·별도성능/실회원원ACK 검증경계는유지한다.
