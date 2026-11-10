# 이슈 주제별 추적표

2026-11-10 Issue17 현재: [Native52 기기 인수](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756433040)·[Native53 게시](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756529672)로 이번 완료 오류/계정 복구 구간의 사용자 통과·기존 막힘 해소를 확인했다. 문구 수정 전에 이미 복구됐으며 같은 복구 재시험 대기는 없다. Native 구현 5df515f7841a7963faa7d3c6ed930cd31ab8b3bf/feature/raid-character-missing-recovery push·clean은 공식 보고, 자동2856PASS/analyze0과 실제 기기 통과는 구분한다. [인수 원본](../features/recruitment/completion-and-records/completion-recovery-acceptance-20261110.md)을 따른다. 누락 캐릭터/부분 완료 자료·기기 검증과 일괄 완료 기획은 별도 미완료이며 Issue17 전체 종료는 아니다. Backend 추가 수정 요청 없음, 이번 문서는 미커밋·미push다.

아래는 이전 구간 기록이다.

Issue17 최신: [Native48 계정 막힘 지속](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6742031537)에 [Backend 전체49번째 현재 상태 채택 확인](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6742169727) 회신. 기존 계정 사용 복구는 미완료다. [원본](../features/recruitment/completion-and-records/bug033-current-state-adoption.md)의 좁힌 원무옵션 correction/gate 거절+GET 성공+사용자 명시 선택 조건으로 과거 결과 미확인 상태에서 로컬 활성 대기를 해제할 수 있다. 과거 전체 거절 증명을 이 경로의 필수 조건으로 뒀던 이전 안내는 정정했다. 다음 Native는 기존 v3의 현재 상태 유지 연결·검증/계정 사용 복구를 우선하고 그 전 정상 흐름 기기 재시험을 반복 요청하지 않는다. 실제 DB0036/소스 해시 읽기 확인·격리 HTTP1PASS/22.79s, 실자료/서버 변경 없음. 문서는 미커밋·미push다. [NEXT_WORK](NEXT_WORK.md)를 따른다.

아래는 이전 구간 기록이다.

Issue17 최신: [Native 전체46번째 진행/이력 한계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6741157735)·[전체47번째 최종 결과](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6741254789) 확인. 신규 계정 group 옵션·주간 schema4의 원옵션/불명 이력 보관·CLIENT_UPGRADE_REQUIRED 반복 안내 보완, Native 자체전체2845PASS/analyze0이다. 미커밋·미push이며 기존 v3 요청의 이력/안전 정리와 사용자 기기 인수는 미완료다. 다음 Backend는 이 특정 요청을 기존 서버 로그/저장 근거로 판별 가능한 최소 증거를 확인·회신해야 한다. 아직 추가 대조/회신은 미실행이다. 현재 API/DB·계약은 유지하며 신규 문서는 미커밋·미push다. [NEXT_WORK](NEXT_WORK.md)를 따른다.

아래는 이전 구간 기록이다.

Issue17 최신: [전체45번째 Backend BUG-033 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6740367084) 완료. [원본](../features/recruitment/completion-and-records/account-completion-group-profile-bug033.md)에 계정 정정 GET/POST·수동 PUT의 group_policy_version 최소 연결과 기존 recruitment-v2 namespace 유지, 알려진 무옵션 원요청의 gate 전 거절을 근거로 한 조건부 failed 정리 범위를 기록했다. 격리 HTTP2PASS/48.98s이며 실제 DB/API/업무 코드/계약은 변경하지 않았다. 앞선 계정3경로 무옵션 소비안은 정정한다. 다음 Native는 옵션/원옵션 보관·해당 거절 분류/반복 안내 보완·자동 검증 후 사용자 기기 재확인이다. Native43의2840PASS·미커밋 구현을 BUG-033 해결로 표시하지 않는다. 이번 문서는 미커밋·미push다. [NEXT_WORK](NEXT_WORK.md)를 따른다.

아래는 이전 구간 기록이다.

Issue17 최신: [전체42번째 Backend 완료 경합 확인](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6738491069) 회신 완료. [원본](../features/recruitment/completion-and-records/completion-retry-order-check.md)에서 같은 대상/종류 두 key의 stale 거절·원ACK/반대주차 보존, 공대/개인 종류 차이를 좁혀 검증6PASS/96.21s했다. 다음 Native는 짧은 안내·취소/표시 수명·기존 복구·새 profile 계약 연결/자동 검증, Backend는 구체 차이에 대응한다. 새 종결 API/fence·복구 큐·다중 저장은 이번 범위에서 제외하며 선행 조건이 아니다. GET만으로 원pending 삭제/무조건 새 key 전송을 승인한 것은 아니다. 실제 로컬 API/DB·업무 코드/계약은 유지하고 기기 확인은 미완료다. 이번 문서는 미커밋·미push다. [NEXT_WORK](NEXT_WORK.md)를 따른다.

아래는 이전 구간 기록이다.

Issue17 최신: [Native 전체40번째 조사 수용](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6737786058)·[전체41번째 사용자 범위 축소](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6738162109) 확인. 명령 종결 API/fence·복구 큐·다중 저장 확대는 이번 범위에서 제외하며 앞선 제안을 선행 조건으로 두지 않는다. 다음 Backend는 완료/개인 완료만 대상으로 현재 완료 조회의 표시·미완료 조회 후 새 context/새 명령과 옛 요청 경합·기존 복구로 충분/지원 불가 구간을 짧게 대조해 답변한다. GET만으로 원pending 삭제/무조건 새 key 전송은 승인되지 않았고 단일 slot 제한도 미해결이다. Native는 확정 문구/표시·기존 복구·새 계약 연결을 설계한다. [NEXT_WORK](NEXT_WORK.md)를 따른다. 이번 회신 기록은 미커밋·미push며 코드/서버 변경은 없다.

아래는 이전 구간 기록이다.

Issue17 현재: [전체39번째 Backend 조사·정의 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6737640898) 완료. [복구·충돌 조사 원본](../features/recruitment/completion-and-records/pending-recovery-and-conflicts.md)에 ACK24h/식별 기록48h·원요청 재송신의 실행 가능성·종결 증거/장기 미해결 한계·업무 충돌/Native slot 구분을 기록했다. 다음 담당 Native의 대조·사용자 최소 범위 협의이며 Backend는 추가 계약 질문에 대응한다. 장기 미해결 종결 fence는 미합의 제안, 새 서버 기능/계약/DB 구현·시험/배포는 없다. 기존 보정/로컬 반영은 유지하고 신규 연결/기기는 미완료다. 이번 문서는 미커밋·미push다. 자세한 다음 실행은 [NEXT_WORK](NEXT_WORK.md)를 따른다.

아래는 이전 구간 기록이다.

Issue17 최신: [Native 전체37번째 소비 설계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6736308942)·[전체38번째 오류 복구/충돌 범위 협의 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6737308328) 확인. 기존 보정16c9cd4/계약864de38b·로컬API101cd82d 수용은 유지하며 다음 담당은 **Backend 조사·정의/회신**이다. 처리 의미·버튼 행동·복구 종료 증거·장기 미해결·업무 충돌 범위·최소 오류 세분화 필요성을 기존 코드/계약으로 대조해야 한다. 첫 오류 취소/확인창 한정 표시는 Native 사용자 확정 UX이며 원요청은 보존한다. 새 기능/API/DB 구현이나 정책 확정은 아직 없다. Native 소비 구현·기기 확인도 미완료다. 자세한 요청은 [NEXT_WORK](NEXT_WORK.md)를 따른다. 이번 기록은 미커밋·미push이며 기존 Backend 답변/코드 게시·로컬 반영은 유지한다.

아래 상태는 직전 구간 기록이다.

Issue17 [전체36번째 Backend 계약 보정·개발 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6735265341) 완료. 고정 구현 `16c9cd4b9016a881bbb26c8438f3347049603902` / feat/character-lifecycle는 origin push·원격 SHA 일치 확인, 실제 로컬 API image101cd82d와 앱285파일/282모듈·두 전체 계약이 같다. 새 two-cycle SHA256 `864de38b53ec23a305074bb3844a7a603ba1f992815427fdba3e6931793119b6`, 선택 query 누락10개 보완·지원/선언65개 일치다. 기본 계약/DTO·본문·권한·토큰·DB 동작은 유지했다. 영향 회귀 최종 고유114PASS·도구63PASS/신규 미해결0이며 과거 전체1921PASS/기존2FAIL과 합산하지 않는다.

실제 로컬 API만 교체했고 DB0036·117표355행의 전체 hash/구조/sequence·키4개·환경/보안/포트·DB컨테이너/볼륨 보존, healthy·listener7개·새 실행 로그17이벤트 오류0을 확인했다. migration·실자료 명령·새 키/환경·dump·운영/APK 배포·merge·Issue 종료는 없다. [구현·검증·인계 원본](../features/recruitment/completion-and-records/completion-profile-contract-fix.md)·[집계](../engineering/operations/records/completion-profile-contract-verification.json)를 따른다.

다음 담당 Native: 전체35번째 오류 안내 결과를 유지하고, 게시된 새 계약을 새 조회·새 명령에 채택해 일관된 participation_profile 연결·자동 검증을 진행한다. 저장 원query·본문·키·검증 snapshot·pending/ACK는 바꾸지 않는다. 이후 사용자 실제 기기 완료 성공을 별도 확인한다. Backend는 구체 차이 회신에 대응하며 같은 안내/계약의 반복 수용을 요청하지 않는다. 후행 문서 커밋/푸시는 이번 승인 범위의 결과 기록이며 새 서버 교체는 필요하지 않다.

아래 이전 상태·미커밋·기존 계약 표기는 당시 기록이다.

Issue17 최신 수신: [Native 전체35번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733937729)가 오류 안내/진단정보 보존·완료 성공/조회 오류 분리 구현과 자체2832PASS/analyze0을 보고했다. 미커밋·미push·기기 미확인이며 완료 차단 해결은 아니다. 현재 다음 담당 Backend는 전체33번째 요청에 따른 완료2/추가8동작 계약 대조/보정·새 hash/HTTP 검증·개발 적용 인계다. Native는 보정 계약 소비 대기이며 반복 안내 시험을 요구하지 않는다. [NEXT_WORK](NEXT_WORK.md)를 따른다.

Issue17 현재: [Native 전체32번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733447639)의 오류 분류 수용과 [전체33번째 사용자 승인 Backend 계약 보정 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733769180)을 접수했다. 사용자 별도 로컬 업데이트 지시로 [Backend 전체34번째 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733877672)에서 구조 소스ccf091d/API2f86172d·DB0036 보존/실행 일치를 확인했다. 완료 profile 오류 수정·새 계약·기기 해소는 미완료다. 다음 Backend는 완료2/추가8동작 보정·계약 연결 검증과 새hash 인계이며 Native는 오류 안내/후속 계약 소비다. [현재 실행](NEXT_WORK.md)·[반영 기록](../engineering/operations/source-layout-local-rollout.md)을 따른다. 아래 미반영/조사 단계 문장은 당시 기록이다.

Issue17 현재: [Native 전체30번째 완료 차단 제보](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6732895692)에 [Backend 전체31번째 조사·오류 분류](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733182655)를 회신했다. 완료 profile 선언 누락 경로8PASS 재현이며 기능 수정은 아니다. 다음 Backend는 계약/연결 회귀 보완 범위, Native는 오류 분류·최소 요청 상관/향후 소비 검토다. [조사 원본](../features/recruitment/completion-and-records/completion-context-profile-audit.md)·[현재 실행](NEXT_WORK.md)을 따른다. OPEN 유지, 실제 서버/DB·코드/계약·기기 해소 미완료다. Native 전체29번째의 구현7a165ac1 게시도 확인했으며 아래 추가 Backend 요청 없음·Native 미게시 문장은 각 당시 상태다.

Issue17 게시 최신: 사용자 지시로 보완 구현 `caffaf3405a53be941250132a2b50779943b15f6`를 origin/feat/character-lifecycle에 push하고 원격 SHA 일치를 확인했다. [전체27번째 Backend 고정 구현 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722956197) 기준이다. 커밋의 앱247파일은 실제 dev imagece59926c/DB0036과 일치하며 새 서버 반영은 없다. Native26 실행 지원 접수·추가 요청 없음, 다음 Native 기능 구현/연결이다. 아래 미커밋·미push/원격 기준 없음은 당시 기록이며 폴더 이동 보류·미병합/운영 미반영을 유지한다.

Issue17 [전체25번째 Backend 실제 로컬 보완 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722917497) 인계 완료. Native24 소비 수용·실행 지원 대기 해소, 다음 Native 기능 구현/연결이며 소스 미커밋·미push와 폴더 이동 보류를 유지한다.

Issue17 최신: [Native 전체24번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722805010)에서 잔여2항목/계약 소비 수용·추가 Backend 요청 없음을 확인했다. 사용자 지시로 실제 dev API imagece59926c·DB0036에 보완을 반영하고247파일/두 계약·자료/키 보존·healthy를 검증했다. 보완 소스는 여전히 미커밋·미push, Native 신규 연결/기기·운영은 별도다. [로컬 반영 집계](../engineering/operations/records/roster-participation-followup-local-rollout.json)·[다음 실행](NEXT_WORK.md) 기준이며 폴더 분류/파일 이동은 사용자 지시로 보류한다. 아래 미반영/소비 대기·이전 실행 이미지는 당시 기록이다.

Issue17 [전체23번째 Backend 보완·검증 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722487011) 게시 완료. 다음은 Native 소비 대조이며 보완 소스의 commit/push·실제 dev 반영은 미실행이다.

Issue17 잔여2항목 Backend 로컬 보완·해당 검증 완료. 사용자 확정 범위의 신규 N 미선택 reason과 명시 선택·기존 참가 보존을 인계하며 다음은 Native 소비 대조다. 새 보완은 미커밋·미push·실제 dev 미반영, 기존 게시 구현4c37c2b·image4ac36fdb/DB0036을 유지한다. [보완/실제 응답 발췌](../features/rosters/lifecycle/roster-participation-followup.md)·[다음 실행](NEXT_WORK.md) 기준이며 아래 감사/진행 중/사용자 답변 대기는 당시 기록이다.



[전체20번째 Native](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721323343)는 추가 Backend 요청 없이 Native 구현 설계를 정리했다. 그러나 사용자 잔여 감사에서 [전체21번째 Backend 공백 확인](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721435909)을 회신했다. active0/현재 선택null인데 공통 source가 옛 완료P 캐릭터를 다음주 기본 선택으로 반환하는 경계를 격리 재현했다. 혼합 M/P 이후 일정·실제 탈퇴/승계·신규 주차 명령 회귀도 보강 대상이다. **현재는 Native 대기만 남은 상태가 아니다.** [감사 기록](../features/rosters/lifecycle/roster-participation-backend-audit.md)에 따라 다음 Backend 보완/직접 검증을 진행하며, 기존 게시·로컬0036 지원 근거는 유지한다.

아래 구현 완료/Native 대기만 표기는 이번 감사 이전의 범위 판단이다. 게시/로컬 반영 사실은 유지하되 전체 후속 경계 완료로 해석하지 않는다.



[전체17번째 Native 인계 접수](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721152982)를 확인했고 사용자 승인으로 [전체18번째 Backend 로컬 반영·실행 지원](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721249386)을 인계했다. 실제 로컬 API image4ac36fdb·DB0036_roster_presence·기존 app 소스247파일 일치, 두 OpenAPI 전체 비교/기존114업무표99행·sequence·키4개 보존·API/DB healthy 확인. [로컬 집계](../engineering/operations/records/roster-participation-local-rollout.json)를 따른다. 로컬 신계약 미지원 대기는 해소했고 Native 신규 DTO/실제 연결·기기 인수는 별도다. 사용자 명시 승인으로 구현·실행 계약·검증·로컬 반영 기록을 `4c37c2bebbb9eb8950770a240b6e20b7b468399c`에 커밋하고 origin/feat/character-lifecycle에 push·원격SHA 일치를 확인했다. [전체19번째 Backend 원격 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721299358) 기준이며 원격 소스 미게시 대기는 해소됐다. 같은 브랜치의 후행 문서 커밋은 이 게시 결과만 기록하며 실행 app/API/DB를 바꾸지 않는다. 운영 미반영·Penpot/화면·기기 보류 유지.

## Issue17 최신 — 2026-11-08

[전체7번째 Native 사용자 범위·4항목 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6719797227) 수신·[전체8번째 Backend 서버 계약 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6719925630) 게시. Native가 기획/UX/Penpot·화면 주도, Backend는 서버 계약/권한/자료/검증만 판단한다. 사용자는 구버전의 부분 완료 구조 영향 방·실제 주차만 업데이트 필요로 제한하는 안을 선택했다. 다음 Native는 wire/능력 표식·옵션·M/P 교체의 소비 대조, Backend는 합의 후 공개 API·관찰 상태·공통 참가/부분 완료 교체/후속 명령을 보완한다. Issue OPEN·미커밋/미push·실DB0036 미적용. 현재 화면/Penpot·기기는 별도 지시 전 보류한다. [설계](../features/rosters/lifecycle/roster-participation-issues.md)·[NEXT_WORK](NEXT_WORK.md).

## 최신 완료 종료 — 2026-11-08

사용자 명시 지시로 [#34](https://github.com/heo0328/lostparty-backend/issues/34)·[#38](https://github.com/heo0328/lostparty-backend/issues/38)·[#46](https://github.com/heo0328/lostparty-backend/issues/46)을 CLOSED/completed로 종료했다. Native 최신 댓글(각 전체15·10·7번째)을 재확인했고 본문 상단에 Backend 최종 상태를 추가했다. 새 댓글·추가 시험/배포는 없다. 미확인·미실행 후속은 보존하며 완료 범위를 확대하지 않는다.

현재 완료 범위·회신 링크·남은 #17→#15→#18→#19의 권장 처리 순서는 [NEXT_WORK](NEXT_WORK.md), 확인/종료 이력은 [DEV_LOG](DEV_LOG.md)를 따른다. 아래 OPEN·통합/APK 게시 대기는 당시 기록이다.

## 백업 주제 최신 — 2026-11-07

[#46 백업 조사·사용자 보관 안내](https://github.com/heo0328/lostparty-backend/issues/46)는 [전체4번째 Native 범위 정정](https://github.com/heo0328/lostparty-backend/issues/46#issuecomment-6705693077)과 사용자 후속 실행 승인에 따라 [전체5번째 Backend 운영 기준본/PC 보관 결과](https://github.com/heo0328/lostparty-backend/issues/46#issuecomment-6706589300)까지 회신했다. [백업 원장·안내 시점](../engineering/operations/backup-and-recovery.md)·[집계](../engineering/operations/records/backup-recovery-2026-11-07.json)에 현재 상태를 기록한다. 로컬 고정자료는 사용자 보관 보고, 로컬 DB는 제외, 운영 기준본은 생성/PC 전송/무결성 확인 완료다. 실제 복원·정기 자동화·외장 매체 보관은 완료로 표시하지 않는다. 다음 Backend 문서 구간 게시/결과 인계·사용자 파일 보관이며 추가 Native 기능/반복 시험 대기는 없다. Issue OPEN·종료는 별도다.

최신 종료(2026-11-04): 사용자 승인 [PR44](https://github.com/heo0328/lostparty-backend/pull/44)·Backend 통합4231a58/후행 마감 기록까지 dev/main 동일 시점 게시, 완료 브랜치 정리·미완료 activity-selection 보존. [Issue41 전체15번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6609216803)·[Issue42 전체9번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6609226056) 회신 후 둘 다 completed CLOSED. 개발·사용자 로컬 인수·양측 원격 인계/Backend Git 정리 완료, 추가 요청 없음. [NEXT_WORK](NEXT_WORK.md)·[최종 이력](DEV_LOG.md#issues-41-42-integration-closeout) 기준이다.

| 종료 주제 | 완료 근거·별도 경계 |
|---|---|
| [#41 초기 자동 갱신 일괄 처리](https://github.com/heo0328/lostparty-backend/issues/41) | 일괄 API·Backend144PASS·로컬 지원·사용자 반복 호출 축소 확인·Flutter 기본동시2/기기 비교·원격11e9c847 인계 완료. 개발자 승인 운영v2.0.0 반영 완료, 추가 최적화는 별도. |
| [#42 활동 해제 후 기존 참가 유지](https://github.com/heo0328/lostparty-backend/issues/42) | 예방 수정·Backend57PASS·로컬 지원·Flutter 보완/사용자 변경 구간 통과·원격 인계 완료. 기존 dev review 복구는 최종 범위에서 제외, 개발자 승인 운영v2.0.0 예방 수정 반영 완료. 전수 조합 인수는 별도. |

종료 당시 AWSv0.1.2 보존 기록은 이후 개발자 명시 승인 v2.0.0 반영으로 갱신됐다. 현재 운영 imagef33f4c6c·로컬 imagebe56f76c/DB0035다. 이슈 종료 자체를 배포 승인으로 해석하지 않으며 실제 반영은 아래 Issue34·배포 집계를 따른다.

| 현재 추가 주제 | 상태·다음 담당·완료 조건 |
|---|---|
| [#38 초대 검색 본인·기존 그룹원 판정](https://github.com/heo0328/lostparty-backend/issues/38) | 로컬17PASS·Flutter 소비/41PASS·사용자 변경 구간 통과 후 개발자 승인 PR40/source2c6070c/v0.1.2·image7c8b8db9·DB0035 운영 반영 완료. [전체9번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6599670183)·[배포 집계](../engineering/operations/records/backend-v0.1.2-deployment.json). 기존1817PASS 한정 재사용·신규 앱시험0/scripts59PASS, 공개health·조회·인증거절 확인. 운영 사용자 전체 인수/APK게시·Issue종료는 별도이며 추가 요청·반복시험 없이 지시 대기, Issue OPEN 유지. |
| [#34 Native 태그·Release APK/Backend 반영 추적](https://github.com/heo0328/lostparty-backend/issues/34) | 사용자 승인 Backend v2.0.0/source51b1cb3·imagef33f4c6c·DB0035, Actions41674801953/Deployment7524537038 success. [집계](../engineering/operations/records/backend-v2.0.0-deployment.json)·[전체13번째 Backend 운영 완료](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6609667274)로 #41/#42 운영 지원 확인 대기 해소. 이번 한정 로컬 검증 재사용·앱 회귀0/scripts61PASS·최소 공개 점검/DB·키 보존 확인. 다음 Native v2.0.0 태그/서명CI/APK 게시, 운영 실회원/새 APK 전체 인수·외부백업 후속은 별도. Issue OPEN 유지. |

**현재 Git 통합 완료:** [재신청 수정 브랜치 통합 기록](../features/recruitment/reapplication-integration-2026-10-27.md)·[PR28](https://github.com/heo0328/lostparty-backend/pull/28)/병합41a47ed의 dev 원격 반영과 완료 브랜치 로컬/원격 정리를 확인했다. 2026-10-28 main/dev를1b6f57b로동기화·원격확인후동일지점에서feat/group-management분기·checkout. 미완료 활동 선택 브랜치와 실행 API·DB는 보존. 최신 실행/다음 작업은 NEXT_WORK이며 아래 종료 전 검토 문장은 당시 이력이다.

## 최신 Git 통합 — 2026-10-30

사용자 승인으로 그룹 작업 `48bf88c`를 [PR30](https://github.com/heo0328/lostparty-backend/pull/30)·병합 `fc6c06a`로 dev에 통합하고 main도 fast-forward하여 원격 일치를 확인했다. `feat/group-management`는 로컬·원격 정리하고 checkout은 dev다. 위 2026-10-28 분기 상태는 과거 기준이며 미완료 활동 선택 브랜치는 보존한다. 그룹 새 기기 확인·Issue 상태·실제 실행 서버는 변경하지 않았다.

## 2026-10-31 그룹 Git 통합

사용자 승인으로 [PR31](https://github.com/heo0328/lostparty-backend/pull/31)·병합9fa0f7e에 그룹 주차정책/F01·개선 인계/상세500 조사기록을 dev 통합했다. main은 dev의 최종 기록 커밋으로 동기화하며 통합된 그룹·베타 인계브랜치는 로컬/원격 정리했다. 실제실행b8542ef·DB0035와 상세500 미해결/Flutter 근거대기·Issue OPEN은 유지한다. 후속 코드착수는 최신dev 목적브랜치에서 이어간다. 아래 이전 브랜치/미통합 설명은 당시 이력이다.

## 2026-10-31 현재 그룹 상태 — 기기 인수 완료·상세500 조사 미완료

[#16 전체37번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6529987970)의 현재 그룹·레이드 앱 기기 전체통과를 수용했다. 연결/그룹변경/승계·개방/상속·표시·이름안내는 현재 안내범위 인수완료이며 아래 과거 기기대기는 해소됐다. [전체36번째 상세500 조사요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6529904340)은 과거2건 확인·현재READ ONLY 미재현/원인미확정, [조사 집계](../features/groups/detail-500-investigation.json)·NEXT_WORK 기준으로 Flutter 당시 입력/동작근거 대기·Backend 후속대조다. 실행b8542ef/DB0035 유지, 서버교체/자료변경·Issue종료/merge 없음. Penpot은 Flutter/디자인도구 대기다.

## 최신 그룹 후속 — 주차별 그룹 변경·승계 정책 정정

[#16 전체27번째 Flutter · 정책/구현 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521839291)·[전체28번째 Flutter · 문서78e53aa0 게시](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521897849)에 대응해 [전체29번째 Backend 계약 후보](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6522746434)를 먼저 인계했다. feat/raid-group-policy에서0035 주차/세대 원본·설정/승계/개방·조회/그룹판정과 원ACK 보존 전환을 구현했다. [소비 계약](../features/groups/cycle-group-policy.md)·[검증 집계](../features/groups/cycle-group-policy-verification.json)·NEXT_WORK 기준이며 새 Flutter 미연결이며 사용자 승인으로 sourceb8542ef/이미지930c25f8·개발DB0035 반영/실행검증을 완료했다([반영 기록](../engineering/operations/cycle-group-policy-rollout.md)). 구현b212ad0 commit/push·원격일치 및 [전체30번째 Backend 고정 계약 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6523975291) 완료, 다음 Flutter 연결/소비 차이 회신 대기다. [전체31번째 Backend 개발반영 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6524503597) 완료. 다음은 새 계약 연결/기기 결과이며 Issue종료·dev/main통합은 별도다. 기존 그룹 기기 인수·Issue13 completed는 유지한다.


## 2026-10-27 마감 — Issue13 사용자 승인 종료

사용자가 이슈13 클로즈를 명시적으로 지시했고 **closed/completed**를 실제 확인했다. [전체192번째 Backend · 1차 구현/기기 인수 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)이 종료 근거다. Backend 구현/개발 반영과 Native 보고 정상 흐름·표시의 사용자 기기 인수는 완료다.190/191의 정밀도 소비·알럿·UX 등은 [차후 보완 추적](../features/recruitment/follow-up-backlog.md)에 담당·현재 보류·재착수 조건으로 보존했다. 이들은 현재 착수/1차 인수 선행 조건이 아니다.

현재 추가 Backend 구현·시험 요청은 없다. 다음은 사용자와 별도 구간을 재시작하거나 새 구체 차이가 생길 때 해당 주제 Issue에서 진행한다. dev/main18830c2·실행 sourcec1f86d8/이미지581a1a5e·DB0033 유지, 서버/DB/자료·다른 이슈 상태 변경 없음. 기기 회신 수신부터 이번 사용자 승인 종료까지의 누적 문서 기록을 같은 수정 브랜치에서 의미 있는 마감 구간으로 게시한다. 별도 merge/AWS·반복 시험은 없다. 아래 OPEN/종료 차단·확인 대기는 종료 전 각 시점의 이력이다.


## 2026-10-27 사용자 정정 수신 — 차후 보완은 현재 인수·종료의 선행 조건 아님

[전체191번째 Flutter · 사용자 정정](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437976324)을 확인했다. 실제 BetaSchedule.session_id 정밀도 판정·다음 주 개방 알럿 로그·일정 제안 확인/수락 발견성 등은 **사용자와 차후로 합의한 Native 보완**이다. 미수정/개선 기록은 보존하되 현재 착수·즉시 다음 작업·현재 베타 인수의 선행 조건으로 두지 않는다. 별도 보완 구간 재시작 시 최신 계약·코드/UX를 확인한다.

기존 모집 정상 흐름·표시의 사용자 기기 통과/1차 구현 완료는 유지한다. **이전 Backend의 ‘미수정1건 때문에 현재 인수/종료 차단’ 판단을 정정한다.** 현재 추가 Native/Backend 구현·시험·서버 변경 요청은 없다.191에서 Native는 Issue13을 종료하지 않았다고 명시했으며, 이번 최신 회신 조회에서도 이슈 상태는 OPEN이다. 1차 구현 완료와 차후 보완 추적을 구분하며 보완 착수를 다시 요청하지 않는다. 아래190 기준 즉시 다음 작업/종료 차단 표현은 이번 정정으로 대체한다.


최신 #13 종료 검토: [전체189 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437895407) 표시 기기 확인 완료·[전체190 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6437933418) 추가 Backend 누락 없음. **실제 세션 정밀도 Native 미수정1건**이 남아 OPEN 유지. 다음 Native 보완 완료 또는 별도 Issue로 담당/완료 조건 이관 확인 뒤 종료한다. 사용자 1차 구현/정상 흐름 기기 인수 완료와 구분한다.

2026-10-27 사용자 확정으로 **레이드 모집 1차 구현·네이티브 디바이스 인수 완료**를 기록한다. 추가 Backend 수정 요청은 없으며 새 구체 차이에 대응한다. 별도 성능/원ACK 검증·Git 통합·AWS/Issue 종료와 구분한다. 아래 미완료 표현은 당시 이력이며 현재 단계는 NEXT_WORK를 따른다.

모집 누적 이력은 `feat/raid-recruitment`이며 사용자 승인으로 [2026-10-27 통합 체크포인트](../features/recruitment/integration-checkpoint-2026-10-27.md)를 정리해 PR27/4a5f590으로 dev/main 같은 기준에 병합·푸시했고 완료 브랜치를 정리했다. 후행 결과 기록도 양 기준에 함께 게시하며 후속은 최신 dev에서 새 목적 브랜치로 진행한다. 이슈 OPEN과 부분/전체 인수는 Git 통합과 구분한다. 활동 선택의 미완료 로컬 작업은 별도로 보존한다. 아래 각 이슈의 고정 댓글·구현/검증 근거와 당시 이력은 유지한다.

2026-10-18 사용자 지시로 정리했다. 한 이슈의 직접 기능/완료 조건에 집중하고 독립 후속은 링크로만 연결한다. 아래 번호는 GitHub 이슈 번호이며 Backend 작업 단계 번호가 아니다. 당시 통합 기준은 dev/ce3064f·main/77a1fe5였다. 현재 개발API는 two-cycle178경로/199 operation·DB0033이며 최신실행은 NEXT_WORK를 따른다.

## 열려 있는 주제

| 이슈 | 주제 | 다음 담당·상태/완료 조건 |
|---|---|---|
| [#29](https://github.com/heo0328/lostparty-backend/issues/29) | 문서 역할·갱신·이관 기준 상호 확인 | Backend 원본c1fa205·Flutter 참조4bdec0e 원격 반영/내용 대조 완료. [전체5번째 Backend 완료 조건 확인](https://github.com/heo0328/lostparty-backend/issues/29#issuecomment-6520322169). 추가 수정 대기 없음·Issue 종료 별도/OPEN 유지 |
| [#12](https://github.com/heo0328/lostparty-backend/issues/12) | 그룹 핵심 표시·활동·집계/Flutter 연결 | 구현계약22b1620·개발실행2602e45/DB0034반영·실행검증완료. [전체27 Flutter 연결구현](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6488900145)·자동검증자체보고/추가API요청없음. 후속#12전체29/30후보검색/역할표시도5d24244/507cd78a로개발반영·실행검증완료. 전체36사용자기존그룹정상시험통과수용. 최신 [전체39번째 Backend 서버반영 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503318325). 새목록그룹명/소속배지후속은[계약](../features/groups/raid-link-contract.md)·개발반영완료. [전체40번째 Flutter 소비 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503895589)의5f024e53 연결/push·전체2707PASS자체보고 수신. 추가API요청없음·사용자새기기확인/Flutter대응대기. [반영기록](../features/groups/implementation-2026-10-28.md) |
| [#15](https://github.com/heo0328/lostparty-backend/issues/15) | V2 Flutter 인증/분쟁 | #13 전체16번째Flutter 보고기준 D1~D4 dev반영·마감, 분쟁실기기는사용자판단보류. 이후 #13 전체17번째에서 로그인화면재구성수정 별도마감·계약검토전환을보고했으며분쟁실기기보류는별도 |
| [#16](https://github.com/heo0328/lostparty-backend/issues/16) | 그룹 관리·레이드 생명주기 | 새 주차별 그룹 정책0035 구현·격리검증, 고정 계약 게시·실제0035 반영 완료/Flutter 연결 대기는 위 현재 요청을 따른다. 아래는 기존0034 실행/소비 이력이다. 관리/기존레이드보존 구현·개발실행2602e45/DB0034반영·자료보존/실행검증완료. [전체17 Flutter 연결구현](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6488900495)자체보고. 전체21기존그룹잔여기기통과수용·전체22최초그룹연결/표시승인후속구현·격리검증/개발반영/실행검증완료·[전체25번째 Backend 서버반영 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503318794) 후 [전체26번째 Flutter 소비 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503895060)의5f024e53 연결/push보고 수신·추가API요청없음·사용자새기기확인/Flutter대응대기·실서버 최초연결 성공 미확인·복구승계미정/그룹장전용레이드권한없음. [반영기록](../features/groups/implementation-2026-10-28.md) |
| [#17](https://github.com/heo0328/lostparty-backend/issues/17) | 캐릭터 소멸 근거·이력·이름 재사용 ID | Flutter전체1번째범위확인·Backend 현재기능/증거공백 검토·최소계약 보완. 기존L1/claim/조회 재사용. 실제삭제/보류해제 승인 아님 |
| [#18](https://github.com/heo0328/lostparty-backend/issues/18) | 활동 자동추가·직접제외 보존 | 활동브랜치89a3248/설계5fff83b 로컬미push보존. [전체3번째Flutter](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603)는설계접수/별도소비검토대기이며미승인·구현전 |
| [#19](https://github.com/heo0328/lostparty-backend/issues/19) | 사용자/그룹 주간 이용 통계 | Flutter전체1번째검토·type최초고정/함께집계·해산OFF/평균분모/그룹조회권한미확정·실제방원천선행. 집계/조회 미구현·개인manual결과 집계 금지 |
| [#22](https://github.com/heo0328/lostparty-backend/issues/22) | 개인 완료후 선택T 탈퇴·공대장 자동승계 | 전체2번째 Backend 표시보완 구현/개발반영 완료. [개발안내](../features/recruitment/membership-actions/README.md)·고유39PASS(23합동)/174경로·DB0030. 소비0eed67c push/원격확인·[전체3번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6362447014) 완료→[전체5번째 Flutter D22 연결결과](https://github.com/heo0328/lostparty-backend/issues/22#issuecomment-6363334658) fece2003 push/133mock·분석0 보고수신, Backend추가요청없음·다음Flutter 실회원/기기인수미완료·OPEN |
| [#23](https://github.com/heo0328/lostparty-backend/issues/23) | 현재/양T 동일회원 원자적 내보내기 | Backend0eed67c 인계·개발완료. [전체5번째 Flutter E23 연결결과](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6363846643) b6720079 push/178mock·분석0 보고수신. 추가 계약요청없음/실회원·기기전체인수미완료·OPEN |
| [#24](https://github.com/heo0328/lostparty-backend/issues/24) | 선택T 본인실제참가방 검색제외 | Flutter 전체3 계약 수용·추가 차단없음. [개발 안내](../features/recruitment/membership-actions/contract.md) [Backend 전체4 구현 인계](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371301279)·소비15e143a push/원격 확인, SQL/semantics cursor 구현·격리 검증, [전체5번째 Backend 개발 반영](https://github.com/heo0328/lostparty-backend/issues/24#issuecomment-6371617690)·실제 개발176/DB0031 완료. 다음 Flutter 캐시/직접 연결·실인수, Backend 차이 대응·OPEN |
| [#26](https://github.com/heo0328/lostparty-backend/issues/26) | 신청·변경 통합자격·본인 후보조회 | [전체6 Flutter 계약2/UX수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6381816954) 반영, [계약/구현](../features/recruitment/participation/candidate-contract.md)·고유45PASS(신규19/기존26)·177/116/기존DTO·별도factory 검증. 공통판정/정확자기제외·명시배치/승인실패pending유지/후보GET 구현 및 [실제개발 반영/자료보존검증](../engineering/operations/eligibility-rollout.md) 완료. [#26 전체7번째 Backend · 계약2 구현/검증 인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382258395)·source484ca17 push/원격확인. [전체9 Flutter 통합연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382646003) f89c009f push/493PASS·분석0 자체보고수신. 새Backend수정요청없음·개발API177 반영 완료·[전체10 Backend 반영인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6383315604)·[전체11 Flutter 가입소수3항목 정상보고/표시계약 요청](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384482003) 수신·[표시 계약 제안1](../features/recruitment/participation/application-display-proposal.md)·작성22예시/음성15 정적검증·소비합의/구현·격리28PASS완료·실제개발반영완료·[전체12 Backend 제안](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384757210)·[전체13 Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6384902537)·[전체14 Backend 구현인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385227653)·[전체16 Flutter 연결/413PASS 보고](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385536441)·상세예시8 정정/추가12PASS·API불변·[전체17 Backend 자료보완회신](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6385820194)·[전체18 Backend 실제반영인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386031663)·[전체19 레벨누락](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386174761)·[전체20 Backend 최소보완제안](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386261019)·[전체21 Flutter 소비/UX수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386405233)·신규저장/기존누락읽기구현·격리35PASS/구현 당시 실제개발미반영·[전체22 Backend 구현인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386634008)·[전체23 Flutter 연결](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386758343) 13fb5848/158PASS 자체보고 수신·[아이템레벨 실제개발 반영](../engineering/operations/application-item-level-rollout.md) 완료(sourcef471e31/6d5857b3)·[전체24 Backend 반영인계](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386808894)·[전체25 Flutter 보완인수 수용](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6386859737)·레벨표시기기통과/두예외분기자동검증근거수용·네이티브 작업순서는 해당측 관리/Backend 구체차이대응·OPEN |
| [#25](https://github.com/heo0328/lostparty-backend/issues/25) | 주차/모두탈퇴 자동승계·공대장T 해산 | Flutter 전체5 네 차이 해소. [개발 안내](../features/recruitment/membership-actions/contract.md) [Backend 전체6 구현 인계](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371301934)·소비15e143a push/원격 확인, 새 원자 명령·기록/profile·0031 이행 구현/격리 검증, [전체7번째 Backend 개발 반영](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996)·실제 DB0031/API176 완료. [Flutter A 결과](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371981415) 6968f47a push/177mock·분석0 보고수신(독립재현아님). 이후 [전체9번째 Flutter B메뉴/성공처리](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6372783376) 0487788a push/295mock·[전체10번째 Flutter C프로필/본인기록](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6373322164) 0c5ae941 push/413mock·최종분석0 보고수신(범위별 수치·미합산/독립재현아님). 다음Flutter #24검색 후속/정상로그인 실인수, Backend 재현차이 대응·복구UX제안·OPEN |


## 이번 종료

| 이슈 | 종료 구분 | 근거/보존한 미완료 |
|---|---|---|
| [#13](https://github.com/heo0328/lostparty-backend/issues/13) | completed (사용자 승인·모집 1차 구현/기기 인수) | [전체192 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779). 보고된 정상 흐름·표시 사용자 인수 완료,190/191의 Native 보완/UX·별도 검증은 [차후 보완 대장](../features/recruitment/follow-up-backlog.md)에 담당·재착수 조건 보존. 현재 착수/인수 선행 조건 아님·추가 Backend 요청 없음. 새 주제 재시작 시 별도 Issue 추적·merge/AWS/다른 이슈 종료 아님 |
| [#21](https://github.com/heo0328/lostparty-backend/issues/21) | completed (내용전달·문서정리) | 사용자 종료 지시. 공통원문62240fe·[Backend 품질/UX 기준](../engineering/development/quality-and-ux.md)을 AGENTS/개발·협업에 연결·보존, 추가댓글/회신대기없음. 이후승인작업에적용·기능/전면감사/최적화완료뜻아님·사용자지시로지침/전달정리 작업브랜치push |
| [#10](https://github.com/heo0328/lostparty-backend/issues/10) | completed | 카탈로그/주차2GET 구현/검증·Flutter소비/실기기로그. 최신게임패치 검증/기능전체인수까지 완료라는 뜻 아님 |
| [#11](https://github.com/heo0328/lostparty-backend/issues/11) | completed (개인원장 구간) | 개인GET/manual완료·정정 구현/연결·manual true 실제보고. 미완료 실제파티/membership/i/영향확인·전체완료권한은 #13 본문에 이관 |
| [#8](https://github.com/heo0328/lostparty-backend/issues/8) | not_planned (원본 보관/추적 이관) | 길어진 다주제 스레드만종료. 미완료 생명주기 #17/활동 #18/V2 #15/실제파티 #13은유지. 요구취소/기능전체완료아님 |

기존 #1~#7 종료 상태는 그대로 유지한다. #12/#13의 원문은 당시 계획/근거로 보존하고 상단에 현재 범위를 표시했다. #8의 새 작업 요청/회신은 전용 이슈에 작성한다.

## Backend 정리·이관 회신 순번

아래는 본문을 제외한 실제 전체 댓글 순서이며 모두 Backend 작성/단계 이슈 정리·완료/이관이다.

| 이슈/순번 | 결과 댓글 |
|---|---|
| #8 전체154번째 | [원본 보관 종료](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6249418070) |
| #10 전체4번째 | [카탈로그/주차 완료](https://github.com/heo0328/lostparty-backend/issues/10#issuecomment-6249415959) |
| #11 전체8번째 | [개인원장 완료/파티후속 이관](https://github.com/heo0328/lostparty-backend/issues/11#issuecomment-6249417104) |
| #12 전체16번째 | [Flutter G1/G2·G3분리](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6249414405) |
| #13 전체9번째 | [실제파티 유지/통계분리](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6249414899) |
| #15 전체1번째 | [V2 추적 유지/한주제 원칙](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6249415434) |

이번 정리는 서버 구현·DB변경·자동정리·자료삭제/초기화·기존키/로그인 재시험·운영배포 승인이 아니다. 기능코드/실행계약은 같고 새 이슈를 만들었다고 기능 구현을 시작한 것이 아니다.

상세조회500 조사 공식 회신: [#16 전체38번째 Backend · 현재미재현/추가근거 대조](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530073442). 조사기록1be55a7 commit/push·원격일치 완료, 다음 Flutter 당시기록 확인/Backend 후속대조이며 원인해소·Issue종료가 아니다.

#16 전체39 Flutter는 당시 입력/동작 원기록없음을 회신했다([근거](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530221606)). 과거기록 제공 대기는 자연재발 근거대기로 바꾸며 정상시험 반복요청은 하지 않는다. 후속 fix/raid-detail-errors의 READ ONLY ASGI 응답직렬화/조율대기 대조도 현재미재현, 과거500 미해결이다. 전체40 Flutter dev/main 통합보고는 기존 인수와 함께 수용한다.

2026-10-31 사용자 확정으로 #16 상세500 별도원인추적을중단한다. Native 탭로딩보호/기기인수·dev통합은1차대응완료이며 과거서버원인은미확정/해결주장없음으로보존한다. 반복조사/재시험/추가근거 대기는현재실행에서제거한다. 다음기능협의는 #15 원정대 소유이전 시 그룹/레이드 영향 처리다. Issue종료는별도다.

#15 사용자요청으로 소유권분쟁의 그룹/레이드영향처리협의를재개한다. 기존의room후처리제외/기기인수보류와새범위의검토착수를구분한다. [검토원본](../features/rosters/ownership/dispute-impact-review.md)·feat/ownership-dispute-policy 기준, 그룹사용자가입/다른원정대보존은현구조로가능하며활성레이드최종이전은아직보류다. 정책/API구현/실제반영완료는아니다.

#15 [전체10번째 Backend 영향검토 협의](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6541847499) 게시·실제전체순번10확인. 원문후처리제외는이전범위로보존하고본문상단을사용자요청정책검토/Flutter소비검토대기로갱신했다. 제품코드/실행반영완료와구분한다.

2026-11-01 사용자승인 [PR32](https://github.com/heo0328/lostparty-backend/pull/32)·e3a657a로 분쟁영향검토·합성시험/500추적중단기록을dev통합하고main을동일최종기록커밋으로동기화한다. 통합목적브랜치2개는로컬/원격정리·현재checkout dev, 정책미합의/미구현과#15소비검토대기는유지한다. Git통합은제품정책/API/서버/자료반영이나Issue종료가아니다.
