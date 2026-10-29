# 다음 실행

## 현재 기준 — 그룹 개발환경 반영·실행 검증 완료

checkout `feat/group-management`, main/dev 공통 `1b6f57b` 유지. 사용자 승인 계획에 따라 기존 개발환경에 전체 그룹 소스와DB0034를 반영했다. 실제 실행 source `5d24244bb29bc3870a4dc6dfd47decf56f194bd2`, 이미지 `507cd78a`·DB0034이며 업무 구현/계약은후속초대후보보완 `c381445`와동일하다. [구현·반영 기록](../features/groups/implementation-2026-10-28.md)·[실행 집계](../engineering/operations/records/group-features-rollout.json)를 따른다.

실행기록 `9e37868` push·원격일치 후 [#12 전체28번째 Backend · 핵심 개발반영 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6489008365)·[#16 전체18번째 Backend · 관리 개발반영 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6489008735)를 게시하고 실제 전체순번을 확인했다. 양Issue 상단도 실제반영/다음담당으로 갱신·OPEN유지했다.

## 초대 후보 검색·전투력 보완 — 개발반영·실행검증 완료

- #12 전체29/30 요청에따라ASCII대소문자무시정확검색과invite-candidates의reader_profile=group-display-1을구현했다. [전체31 Backend 구현전계약제안](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6496315881)·[검증집계](../features/groups/invite-candidates-verification-2026-10-29.json)를따른다. 기본DTO/단일전투력은보존하고현재owner/ownership/lifecycle의역할별자료를재사용한다.
- 최종직접/표시19PASS·기존초대/이름해석46PASS·두계약전체일치(123/140·185/206). 초회시험자료FK/NOTNULL·UUID순서가정실패는시험만정정했고실행별결과는구현기록에보존한다. READ ONLY 개발집계는적격31중summary null30,그중역할성공자료있는15/없는15다. 특정회원요청의재현은아니다.
- 사용자승인으로5d24244/507cd78a를기존개발서버에반영했다. [반영집계](../engineering/operations/records/invite-candidates-rollout.json): DB0034/114업무표1,833행·sequence/설정/키보존·272소스/runtime31/두계약전체일치·실제READONLY대소문자/공백18요청동등/역할표시·HTTP6·worker/healthy확인. migration없음.
- 다음Flutter/사용자: 현재개발서버에서새프로필을소비해대소문자검색·역할분리표시·정상초대전송/수락을확인하고구체차이만#12회신. Backend는차이에대응한다. 실제정상초대성공/기기인수는미확인이다.

후속 source `c38144528c42eda7fcf2912fa412d3a005fc68e7` push·원격확인후 [#12 전체32번째 Backend · 후보검색/역할전투력 구현인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6496536145)를게시·실제순번확인했고본문상단에개발미반영/다음담당을갱신했다.

실제반영기록 `0f5561015820708bab926b57b80aaf267b9b27f7` push·원격일치확인후 [#12 전체33번째 Backend · 후보검색/역할표시 개발반영 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6496785817) 게시·실제순번확인, 본문상단을최신실행/Native다음인수로갱신하고OPEN유지했다.

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
