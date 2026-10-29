# 다음 실행

## 현재 기준 — 그룹 개발환경 반영·실행 검증 완료

checkout `feat/group-management`, main/dev 공통 `1b6f57b` 유지. 사용자 승인 계획에 따라 기존 개발환경에 전체 그룹 소스와DB0034를 반영했다. 실제 실행 source `cf214d016fc650e216782432f9c9c33823367808`, 이미지 `eecda79d`이며 업무 구현/계약은 `22b1620`과 동일하다. [구현·반영 기록](../features/groups/implementation-2026-10-28.md)·[실행 집계](../engineering/operations/records/group-features-rollout.json)를 따른다.

실행기록 `9e37868` push·원격일치 후 [#12 전체28번째 Backend · 핵심 개발반영 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6489008365)·[#16 전체18번째 Backend · 관리 개발반영 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6489008735)를 게시하고 실제 전체순번을 확인했다. 양Issue 상단도 실제반영/다음담당으로 갱신·OPEN유지했다.

## 초대 후보 검색·전투력 보완 — 후보 구현/격리검증 완료·개발미반영

- #12 전체29/30 요청에따라ASCII대소문자무시정확검색과invite-candidates의reader_profile=group-display-1을구현했다. [전체31 Backend 구현전계약제안](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6496315881)·[검증집계](../features/groups/invite-candidates-verification-2026-10-29.json)를따른다. 기본DTO/단일전투력은보존하고현재owner/ownership/lifecycle의역할별자료를재사용한다.
- 최종직접/표시19PASS·기존초대/이름해석46PASS·두계약전체일치(123/140·185/206). 초회시험자료FK/NOTNULL·UUID순서가정실패는시험만정정했고실행별결과는구현기록에보존한다. READ ONLY 개발집계는적격31중summary null30,그중역할성공자료있는15/없는15다. 특정회원요청의재현은아니다.
- 다음Flutter: 고정후보DTO/현재분석·last-success분리소비의구체차이를#12에회신. 다음Backend: 그차이에대응하고별도요청된개발반영구간에서후보이미지/실행확인을진행한다. 현재개발서버에이수정의실회원/기기시험을요청하지않는다. DBmigration·중복저장·provider조회는추가하지않았다.

## 다음 담당 — 실제 연동·기기 인수

- Flutter [#12 전체27](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6488900145)·[#16 전체17](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6488900495): 연결구현/전체2691시험·직접12포함/분석지적0 자체보고, 추가API요청없음. Backend시험과합산하지않는다.
- 다음 Flutter/사용자: 반영된 기존 개발서버에서 초대/가입→활동캐릭터→기존모집필터→상세/참가와 해산/추방/대표변경·공통방안내를 정상UI로 확인하고 구체차이를 #12/#16에회신한다. 실제연동·기기/Penpot대조는미완료이며 Backend는그차이에대응한다.
- 일반활동canonical UUID와 모집alias/context/candidate는구분한다. 그룹변경후관련조회/선택을갱신하며그룹원동등개설·실제T공대장관리/그룹장전용레이드명령없음을유지한다.
- G-RECOVERY·활동자동추가는별도미결정이다. 로컬활동선택89a3248보존·main/dev병합/운영배포/자료초기화·삭제는없다. 추가요구나차이가없으면동일기능재개발/반복시험을시작하지않는다.

## 확인한 실행과 미확인

- DB0033→0034 이행전후 기존112업무표1,857행·sequence동일, 신규확장표0행/backfill없음. DB컨테이너/볼륨·환경/키/API설정보존, 임시reader제거·API/DB healthy.
- 실행소스272파일/runtime31/두OpenAPI전체일치: 기본123/140·two-cycle185/206. 실제HTTP26건(공개200 2·인증거절401 24), 실제유효세션2명의 READ ONLY 계정/내그룹·집계/주간/모집5항목상세·계획통과·provider0. worker3종성공/ERROR0.
- 실제가입그룹이없어멤버/활동/차단/관리/방목록성공실자료조회·실회원명령·정상회원HTTP·기기인수는미확인이다. 기존격리검증은구현기록대로재사용하며새결과에합산하지않는다.

## 다른 미완료 주제

모집1차인수/Issue13종료는유지하고차후정밀도/알럿/UX/소켓은 [보완대장](../features/recruitment/follow-up-backlog.md)을따른다. 다른Issue상태는 [추적표](ISSUE_TRACKER.md), 완료/결정/검증·장애는 [DEV_LOG](DEV_LOG.md)에보존한다. IF-001/002/003 비활성·원자료/pending/ACK·별도성능/실회원원ACK 검증경계는유지한다.
