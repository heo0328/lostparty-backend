# LostParty Backend 기능 지도

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

Issue17 Native 안내 파트 완료 수신(2026-11-09): [전체35번째 Native](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733937729)에서 기존 오류 코드/status/request_id 보존·완료 성공/후속조회 실패 분리를 일반 앱에 구현하고 자체2832PASS/analyze0을 보고했다. 변경은 미커밋·미push·실기기 미확인이다. 다음 선행 조건은 Backend 완료2+추가8동작의 계약 보정·query→실제HTTP 검증·고정 계약/hash와 개발 적용 인계다. 현재 로컬API2f86172d는 구조 반영만 됐고 완료 profile 오류는 미수정이다. [현재 실행](NEXT_WORK.md)을 따른다.

현재 로컬 반영(2026-11-09): 사용자 지시로 게시ccf091d 구조를 실제 API image2f86172d/DB0036에 반영했다. 앱285파일·282모듈/두 계약·117표357행/sequence·키/환경/DB볼륨 보존·healthy를 확인했다. [반영 집계](../engineering/operations/records/source-layout-local-rollout.json)·[Backend 전체34번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733877672)·[NEXT_WORK](NEXT_WORK.md)를 따른다. 완료 profile 선언 오류는 아직 그대로다. Native 전체32번째 오류 분류 수용 및 전체33번째 사용자 승인 계약 보정 요청을 접수했으며 다음 Backend는 완료2+추가8동작·계약 연결 회귀/새hash 인계다. 이번은 미커밋 문서·로컬 반영이며 신규 코드/계약·운영·기기 인수는 아니다. 아래 미반영/조사만 상태는 각 이전 기록이다.

Issue17 완료 차단 조사(2026-11-09): Native 전체30번째에 [Backend 전체31번째 조사 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733182655)을 게시했다. 완료 GET/POST의 profile 선언 불일치 경로8PASS 재현, 실제 완료400로그 확인·내부 분기 미확정이다. [조사/오류 분류](../features/recruitment/completion-and-records/completion-context-profile-audit.md)와 [NEXT_WORK](NEXT_WORK.md)를 따른다. 기능 수정·새 계약·기기 해소는 미완료이며 이번은 미커밋 문서/조사다. 과거 전체29번째의 Native7a165ac1 원격 게시를 확인했고 아래 Native 미게시/추가 요청 없음은 각 이전 기록이다.

폴더 정리·게시 완료(2026-11-09): 사용자 지시로1차34a2a47과 2차 구조 구현/문서6a87e143e651bd9fc51129f969bfd9ced314a5a1을 같은 `feat/character-lifecycle`에서 커밋·push하고 원격 SHA 일치를 확인했다. 게시 상태는 같은 브랜치의 후행 문서 커밋으로 기록한다. [분류·파일 찾기](../engineering/development/source-layout.md#현재-파일을-찾는-순서)·[2차 대응표](../engineering/development/folder-layout-phase2-map.json)·[검증 기록](../engineering/development/folder-layout-phase2-verification.json)을 따른다. 두 계약·DDL·수집을 보존했고 전체 격리 회귀는 최종 고유1921PASS/기존2FAIL·신규 미해결0이다. 게시 전 EOF 서식39개 정리는 AST 동일·최종 후보439파일 바이트 일치로 확인했다. 실제 dev/운영·Native/기기는 미반영이며 [다음 실행](NEXT_WORK.md)을 따른다.

1차 구조 작업 당시 결과(2026-11-09, 후속34a2a47 커밋 전 기록): 같은 feat/character-lifecycle에서 앱 업무95파일·테스트103파일을 기능별로 이동하고 참조/시험 발견을 수정했다. 공개 DTO/라우터·OpenAPI 자원·ORM 모델 경로는 유지하며 외부 계약/업무 로직을 보존했다. 전체1916사례 대조의 최종고유1914PASS·이동 전에도 재현된 기존 기대 불일치2FAIL을 구분한다. [분류 기준](../engineering/development/source-layout.md)·[검증 집계](../engineering/development/folder-layout-verification.json)·[다음 실행](NEXT_WORK.md)을 따른다. 미커밋·미push·실제 dev 미반영이며 기존 imagece59926c/DB0036과 새 파일 경로는 다르다. 아래 폴더 보류·실행파일 일치는 각 이전 구간 기준이다.

Issue17 게시 최신: 사용자 지시로 보완 구현 `caffaf3405a53be941250132a2b50779943b15f6`를 origin/feat/character-lifecycle에 push하고 원격 SHA 일치를 확인했다. [전체27번째 Backend 고정 구현 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722956197) 기준이다. 커밋의 앱247파일은 실제 dev imagece59926c/DB0036과 일치하며 새 서버 반영은 없다. Native26 실행 지원 접수·추가 요청 없음, 다음 Native 기능 구현/연결이다. 아래 미커밋·미push/원격 기준 없음은 당시 기록이며 폴더 이동 보류·미병합/운영 미반영을 유지한다.

Issue17 [전체25번째 Backend 실제 로컬 보완 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722917497) 인계 완료. Native24 소비 수용·실행 지원 대기 해소, 다음 Native 기능 구현/연결이며 소스 미커밋·미push와 폴더 이동 보류를 유지한다.

Issue17 최신: [Native 전체24번째](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722805010)에서 잔여2항목/계약 소비 수용·추가 Backend 요청 없음을 확인했다. 사용자 지시로 실제 dev API imagece59926c·DB0036에 보완을 반영하고247파일/두 계약·자료/키 보존·healthy를 검증했다. 보완 소스는 여전히 미커밋·미push, Native 신규 연결/기기·운영은 별도다. [로컬 반영 집계](../engineering/operations/records/roster-participation-followup-local-rollout.json)·[다음 실행](NEXT_WORK.md) 기준이며 폴더 분류/파일 이동은 사용자 지시로 보류한다. 아래 미반영/소비 대기·이전 실행 이미지는 당시 기록이다.

Issue17 [전체23번째 Backend 보완·검증 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722487011) 게시 완료. 다음은 Native 소비 대조이며 보완 소스의 commit/push·실제 dev 반영은 미실행이다.

Issue17 잔여2항목 Backend 로컬 보완·해당 검증 완료. 사용자 확정 범위의 신규 N 미선택 reason과 명시 선택·기존 참가 보존을 인계하며 다음은 Native 소비 대조다. 새 보완은 미커밋·미push·실제 dev 미반영, 기존 게시 구현4c37c2b·image4ac36fdb/DB0036을 유지한다. [보완/실제 응답 발췌](../features/rosters/lifecycle/roster-participation-followup.md)·[다음 실행](NEXT_WORK.md) 기준이며 아래 감사/진행 중/사용자 답변 대기는 당시 기록이다.



[전체20번째 Native](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721323343)는 추가 Backend 요청 없이 Native 구현 설계를 정리했다. 그러나 사용자 잔여 감사에서 [전체21번째 Backend 공백 확인](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721435909)을 회신했다. active0/현재 선택null인데 공통 source가 옛 완료P 캐릭터를 다음주 기본 선택으로 반환하는 경계를 격리 재현했다. 혼합 M/P 이후 일정·실제 탈퇴/승계·신규 주차 명령 회귀도 보강 대상이다. **현재는 Native 대기만 남은 상태가 아니다.** [감사 기록](../features/rosters/lifecycle/roster-participation-backend-audit.md)에 따라 다음 Backend 보완/직접 검증을 진행하며, 기존 게시·로컬0036 지원 근거는 유지한다.

아래 구현 완료/Native 대기만 표기는 이번 감사 이전의 범위 판단이다. 게시/로컬 반영 사실은 유지하되 전체 후속 경계 완료로 해석하지 않는다.



[전체17번째 Native 인계 접수](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721152982)를 확인했고 사용자 승인으로 [전체18번째 Backend 로컬 반영·실행 지원](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721249386)을 인계했다. 실제 로컬 API image4ac36fdb·DB0036_roster_presence·기존 app 소스247파일 일치, 두 OpenAPI 전체 비교/기존114업무표99행·sequence·키4개 보존·API/DB healthy 확인. [로컬 집계](../engineering/operations/records/roster-participation-local-rollout.json)를 따른다. 로컬 신계약 미지원 대기는 해소했고 Native 신규 DTO/실제 연결·기기 인수는 별도다. 사용자 명시 승인으로 구현·실행 계약·검증·로컬 반영 기록을 `4c37c2bebbb9eb8950770a240b6e20b7b468399c`에 커밋하고 origin/feat/character-lifecycle에 push·원격SHA 일치를 확인했다. [전체19번째 Backend 원격 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6721299358) 기준이며 원격 소스 미게시 대기는 해소됐다. 같은 브랜치의 후행 문서 커밋은 이 게시 결과만 기록하며 실행 app/API/DB를 바꾸지 않는다. 운영 미반영·Penpot/화면·기기 보류 유지.

## Issue17 Backend 작업(2026-11-08)

Native가 기획·UX·화면·Penpot을 주도하고 Backend는 서버 계약/권한/자료/검증만 판단해 Issue로 협의한다. 기존 내부 기반에 공개 경고/presence·부분 완료 교체/세대 capability를 추가 구현하고 안내 범위 격리 검증을 완료했다. 실제 로컬 서버/DB0036 반영은 전체18번째로 완료했고 운영·Native 신규 연결/인수는 미완료다. Native 전체7번째에 상세 주차 버튼의 해당 주차 전체 참가자 문제 표시가 확정됐고 Backend 전체8번째에 서버4항목/구버전 영향 방·주차 제한(사용자 직접 선택)을 회신했다. Native 후보 소비 대조는 전체15번째로 수용됐고 Backend 로컬 구현/격리 검증은 전체16번째로 인계했다. 로컬 실제 지원은 전체18번째로 확인됐고 Native 신규 연결/기기는 별도 인수다. 게시·운영은 사용자 별도 지시 기준이다. [현재 설계/협의](../features/rosters/lifecycle/roster-participation-issues.md)·[NEXT_WORK](NEXT_WORK.md) 기준이며 현재 Penpot·Native 화면/기기는 보류다.

## Issue 마감 최신(2026-11-08)

사용자 지시로 #34 릴리즈 운영·#38 초대 검색·#46 합의한 복구/백업 요청을 CLOSED/completed로 종료했다. 미확인 운영 전체 인수·다음 서명 전환·외장 사본/실제 복원·정기 자동화는 별도 후속으로 보존한다. 남은 #15·#17·#18·#19의 상태와 권장 순서는 [NEXT_WORK](NEXT_WORK.md)·[추적표](ISSUE_TRACKER.md)를 따른다. 아래 OPEN·게시 대기는 당시 기록이다.

## 환경·보관 최신(2026-11-07)

로컬 two-cycle/DB0035·인증키/Google 로그인·Git/Docker 복구를 확인했다. 운영v2.0.0의 DB·설정·기존 키/복구 구성 기준본과 서버 밖 사용자 PC 사본을 확보하고 읽기·내용 일치를 검증했다. 실제 복원·정기 자동화는 미실행, 외장 매체 복사는 미확인이다. [원장/안내 기준](../engineering/operations/backup-and-recovery.md)·[DEV_LOG](DEV_LOG.md#development-recovery-20261107)·[NEXT_WORK](NEXT_WORK.md)를 따른다. 기능 계약·운영 앱/DB 버전은 변경하지 않았으며 아래 이전 checkout/로컬 실행·외부 백업 미구성·Native APK 대기는 당시 이력이다.

## 운영 최신(2026-11-04) — Backend v2.0.0

개발자 승인 PR45/source51b1cb3·태그v2.0.0·Actions41674801953·production Deployment7524537038 success. 실제 AWS imagef33f4c6c·DB0035, 한국01:31:59 반영 완료로 이슈41 일괄 API·이슈42 기존 참가 유지 예방 수정을 지원한다. 이번 한정 로컬 scoped 검증 재사용·신규 앱 회귀0·scripts61PASS·최소 운영 점검 완료, DB/Caddy·환경/키 보존·migration/기존 review 복구 없음. [배포 집계](../engineering/operations/records/backend-v2.0.0-deployment.json)·[운영 기준](../engineering/operations/backend-release.md) 기준이다.

[Issue34 전체13번째 Backend](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6609667274)로 Native 운영 지원 대기를 해소했다. 다음 Native v2.0.0 태그/서명CI/APK 게시, Backend 다음 개발자 지시 대기다. 로컬 dev imagebe56f76c/DB0035 보존, 운영 실회원/새 APK 전체 기기 인수는 별도다. 이슈41/42 완료 종료 유지. 아래 운영v0.1.2/배포 대기·미반영은 이전 상태 이력이다.

Git/종료 최신(2026-11-04): 사용자 승인 [PR44](https://github.com/heo0328/lostparty-backend/pull/44)·통합4231a58에 최신 인수 기록을 포함하고 Backend dev/main을 동일 시점으로 맞췄다. [Issue41 전체15번째](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6609216803)·[Issue42 전체9번째](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6609226056) Backend 완료 회신 후 둘 다 completed 종료, 후행 결과 기록까지 dev/main 같은 기준으로 게시한다. checkout dev·완료 참가유지 작업 브랜치 로컬/원격 정리·미완료 activity-selection 보존. [NEXT_WORK](NEXT_WORK.md)·[최종 이력](DEV_LOG.md#issues-41-42-integration-closeout) 기준이며 추가 개발/시험 요청 없이 다음 지시 대기다.

기능 완료: #41 일괄 GET/POST와 사용자 기본 LostArk 동시2 선택·기기 측정, #42 활동 해제 후 기존 참가 유지/신규 선택 제외의 사용자 로컬 변경 구간 인수가 완료됐다. Flutter dev/main 원격11e9c847·전체2817PASS/analyze0 자체보고와 Backend 각144/57·실기기 보고를 구분하며 합산/전수 인수로 확대하지 않는다. 기존 dev review 복구는 사용자 결정으로 제외했고 후속 필수가 아니다. [일괄 계약](../features/rosters/bootstrap/startup-batches.md)·[기존 참가 계약](../features/recruitment/membership-actions/activity-participation-continuity.md) 기준이다.

실행 경계: Git 통합/Issue 종료로 AWS 운영v0.1.2·로컬 imagebe56f76c/DB0035를 교체하지 않았다. 배포·태그·APK·DB/키/자료 변경 없음, 운영 반영은 개발자 별도 지시다. 아래 기록은 이전 시점의 운영/Git 이력이다.

운영 최신(2026-11-03): 사용자 승인 PR40·source2c6070c/v0.1.2·Actions41608259484·production Deployment7514620773 success로 그룹 초대 수정의 AWS 반영을 완료했다. 실제 image7c8b8db9·DB0035·한국18:07:40 API 시작, 18:07:53 완료. 앱 코드는 승인 main b649ccf/검증 fdd51c8과 같고 이번 한정 재사용으로 앱 테스트 재실행0·새 제어 scripts59PASS·원본 검증 보존, DB/Caddy·환경/키 보존·공개 health/조회/인증거절을 확인했다. [배포 집계](../engineering/operations/records/backend-v0.1.2-deployment.json)·[전체9번째 결과](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6599670183)·NEXT_WORK 기준이다. APK 게시·전체 운영 사용자 인수·Issue종료는 별도다. 아래 v0.1.1 운영 문장은 이전 시점 이력이다.

Git 최신(2026-11-03): PR39로 그룹 초대/선행 검증 개선을 통합한 뒤 사용자 승인 PR40/2c6070c로 v0.1.2 한정 재사용·버전 준비를 dev/main에 통합하고 태그를1회 게시했다. checkout dev, 완료한 chore/release-group-invite까지 로컬/원격 정리·미완료 activity-selection은 보존했다. 후행 결과 기록은 main/dev 같은 커밋에 모으고 실제 운영 source2c6070c·로컬 source737e14d와 구분한다.

개발·운영 기준(2026-11-02 사용자 확정): [로컬 dev 개발·검증 우선/개발자 지시에 따른 운영 반영](../engineering/development/workflow.md#local-dev-and-production)을 따른다. Native debug→로컬/release→AWS는 사용자 지시 기준이며 앱 실제 적용은 별도 확인한다. 이슈38의 로컬 반영·관련 검증과 debug 앱의 사용자 변경 범위 확인은 아래 최신 근거로 완료했다. 기존 CI 결과와 로컬·기기 근거는 구분한다.

이슈38: 업무 구현fdd51c8·실제 로컬 source737e14d/image1333c99d·DB0035에 API만 반영했다. [전체6번째 Flutter 미지원 조사](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6575085880) 후 [전체7번째 Backend 반영 결과](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6575270695)를 회신했다. [로컬 집계](../features/groups/invite-eligibility-local-rollout-2026-11-02.json)·[가입 계약](../features/groups/joining/README.md)·[NEXT_WORK](NEXT_WORK.md) 기준이다. Flutter 소비0bac63bf/후행97b2ec10 연결·자동검증 완료 보고를 유지하며 로컬 신계약 미지원 상태는 해소했다. [전체8번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6576244724)의 사용자 로컬 변경 구간 전부 통과 보고로 검색/화면 재확인 대기를 해소했다. 승인된 AWS v0.1.2 반영까지 위 최신 기록대로 완료했다. 추가 Backend 요청·APK 게시·Issue종료와 향후 운영 반영은 개발자 별도 지시 대상이다.

검증 범위 개선: selected/full·release-validation.json·불변 validation.json 구현과 [수동 Actions41410922327](https://github.com/heo0328/lostparty-backend/actions/runs/41410922327) 전체1811PASS·artifact 대조·scripts52PASS를 확인한 이력이 PR39에 통합됐다. [운영 기준](../engineering/operations/backend-release.md)·[검증 집계](../engineering/operations/records/backend-validation-scope-verification.json)·NEXT_WORK를 따른다. 당시 로컬 selected 실DB는 Docker 엔진 불가로 미실행이며 이번 문서/Git 통합으로 그 경계를 변경하지 않는다. 이후 v0.1.2 한정 재사용/게시 결과는 위 최신 기록을 따르며 다음 버전의 일반 재사용은 미지원이다. 운영/API/DB 입력 계약은 보존한다.

자동배포 최신(2026-11-02): 사용자 승인 PR36·source77c9de2/v0.1.1 태그1회push·Actions41323830955 attempt2 success로 첫 자동 서버 배포 완료. 실제 API image259e8234·DB0035, UTC16:30:20Z API 시작/16:30:33Z 완료. 전체회귀1811PASS·GHCR/Release·production Deployment/서버journal·공개health/조회200/me401 확인, DB/Caddy·운영환경/키보존. 태그충돌은 수정했고 SSH Secret 개행 손실은 제한키 교체/올바른 등록으로 해소했다. v0.1.0은 보존, 임시 인증 복사본 삭제 완료. [배포집계](../engineering/operations/records/backend-v0.1.1-deployment.json)·[전체9번째 Backend](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6560737194)·NEXT_WORK 기준. 전체 앱 사용자 인수/외부백업 미완료는 별도이며 다음 릴리즈는 새 VERSION/승인 태그로 진행한다.

release 로그인 최신: 사용자확정release Android ID·반영승인으로 allowlist에추가하고기존debug/Web audience·검증을유지했다. 동일이미지API만13:00:31Z재생성·health200/분리검증14PASS, DB/Caddy·키보존. [반영](../engineering/operations/records/lightsail-release-azp-rollout.json)·[전체4번째 Backend](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558294576) 이후 사용자 v1.1.2 실제 로그인 성공 보고를 [전체5번째 Backend](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558340814)으로 수용했다. release 로그인/등록값 대기를 해소했고 refresh·전체 기능 인수는 별도 미확인이다.

릴리즈 운영 협의 최신(2026-11-01): [Issue34 전체1번째 Flutter 운영 회신](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558053848) 확인·[전체2번째 Backend 최소 추적안](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558101459) 회신 완료. Native v1.1.2/source9e4a18f7의 CI 성공·APK 게시를 대조했다. 독립 버전+4단계 추적 원칙에 의견이 일치하며 [근거/최소안](../engineering/operations/release-tracking-review.md)을 따른다. 다음 Backend/사용자가 버전·태그/배포 인증·승인/실패 처리를 정한다. release ID 운영반영은위기록대로완료, 실기기 인수/전체 호환 기록과 CI/CD 구현은 미완료다. checkout `chore/release-management`, 아래최소안협의당시에는서버/자료변경없었으며후속release등록환경반영은위기록과구분한다. 아래 checkout dev는 직전 통합 이력이다.

Git 최신(2026-11-01): 사용자승인 [PR33](https://github.com/heo0328/lostparty-backend/pull/33)·병합c0b13cc로Lightsail첫배포구성/기록·Google등록보완·수동테스트원정대/짧은운영안내를dev에통합했다. checkout dev, main도최종dev의후행통합기록까지동일커밋으로동기화한다. 통합완료chore/lightsail-deployment는로컬/원격정리하고미완료activity-selection은보존한다. 아래작업checkout은당시이력이며서버source6154e45·DB0035/환경/키는이번Git통합에서변경하지않는다. [통합이력](DEV_LOG.md#lightsail-git-integration)을따른다.

운영안내 최신(2026-11-01): [Lightsail 짧은 운영 안내](../engineering/operations/lightsail-quick-ops.md)를추가했다. 실제경로/Compose·Docker자동시작·3서비스restart/log제한은확인, 실제재부팅/회복시험은미실행이다. 서버내덤프만확인했고외부DB/키백업/자동화는미구성·완료근거없음이다. [이력](DEV_LOG.md#lightsail-quick-ops)을따른다.

2026-11-01 테스트원정대 최신: 사용자명시승인으로운영회원1명의미소유원정대1개/V2대기1개를수동인증했다. 현재verified/owned·18캐릭터·소유감사/수동테스트주석을확인했으며실장비증거통과가아니다. 대표/활동은기존unconfigured흐름을유지했고앱목록새로고침이필요하다. [집계](../engineering/operations/records/lightsail-manual-test-verification.json)·[이력](DEV_LOG.md#lightsail-manual-test-verification)을따른다. Google로그인사용자성공보고/운영회원1확인도수용하며아래실로그인미확인문장은이전시점이력이다.

2026-11-01 로그인등록 최신: 사용자승인으로Lightsail의GOOGLE_AZP_ALLOWLIST에기존확정debugAndroid ID한개를반영하고동일이미지API만재생성했다. Web audience/인증로직·다른환경·DB/Caddy·키는보존했으며health200·검증기13경계를확인했다. [반영집계](../engineering/operations/records/lightsail-google-azp-rollout.json)·[이력](DEV_LOG.md#lightsail-google-azp-rollout)을따른다. 이전401/azp누락은[진단당시기록](../engineering/operations/records/lightsail-google-login-investigation.json)이다. 다음은새거래실Google로그인/refresh·인증후그룹코드확인이며아직실인증성공을주장하지않는다.

2026-11-01 Lightsail 최신: 사용자 고정IP/Duck DNS등록과 첫 배포 지시로 `chore/lightsail-deployment`의 source6154e45·API이미지dfad04e8·신규DB0035를 실제 `lostparty-server`에 설치했다. **https://lostparty.duckdns.org** 공개/HTTPS·DB/APIhealth·계약·IP제한분리·직접포트차단·초기덤프/격리복원을 확인했다. 기존 개발환경/자료는 별도로 보존했다. F02는 실제프록시검증까지 진행했으나 앱Google로그인/refresh·인증후그룹코드가 남아 전체완료가 아니다. [배포집계](../engineering/operations/records/lightsail-first-deploy.json)·[이력](DEV_LOG.md#lightsail-rollout)·[NEXT_WORK](NEXT_WORK.md)를 따른다. 아래 AWS미설치/미배포·이전checkout/F02보류 문장은 당시 이력이다.

2026-10-30 기준. 그룹 PR30/병합fc6c06a를 dev/main에 반영·원격 동기화, 그룹/F01/개선 인계·상세500 조사기록은 사용자 승인 [PR31](https://github.com/heo0328/lostparty-backend/pull/31)·병합9fa0f7e로 dev 통합했고 main도 dev의 최종 기록 커밋으로 동기화한다. checkout dev, 통합된 feat/raid-group-policy·fix/backend-beta-readiness 로컬/원격 정리·미완료 feat/activity-selection 보존. 그룹 브랜치 로컬·원격 정리 완료. 그룹1차 구현·격리검증·개발환경 반영과 실행검증 완료. 현재 실제 실행은 주차별 그룹 정책 소스b8542ef/이미지930c25f8·DB0035, 기본123/140·two-cycle185/206이다. [최신 반영](../engineering/operations/cycle-group-policy-rollout.md)을 따른다. [구현·반영기록](../features/groups/implementation-2026-10-28.md)·[NEXT_WORK](NEXT_WORK.md)를 따른다. 기존 그룹 안내범위는 Native #12 전체36/#16 전체21 사용자 기기 통과를 수용했다. 현재 그룹·레이드 앱기기는 #16 전체37 사용자보고 통과이며 별도 상세500의 Backend 원인대조가 남았다. 복구승계/활동자동추가·운영배포는별도다.

후속초대후보검색/전투력: #12전체29/30을받아ASCII대소문자무시정확검색·opt-in역할별character_spec후보구현/격리검증을완료했다. [검증집계](../features/groups/invite-candidates-verification-2026-10-29.json)·구현기록참조. 이후속도5d24244/507cd78a·DB0034로개발반영·실행검증완료했다. 기본DTO보존·migration/provider/중복저장없음. 이후 Native #12 전체36의 안내된 기존 그룹 정상시험 통과를 수용했으며 검색/profile을 다시 인수 대기로 두지 않는다.

2026-10-30 후속: [최초그룹연결/목록표시계약](../features/groups/raid-link-contract.md)·[동일참가자예시](../features/groups/raid-link-examples.json)를같은목적브랜치에서구현·격리검증·계약인계완료했다(source6dac5ab, #12전체38/#16전체24). 기존그룹잔여기기시험은Native#12전체36/#16전체21사용자보고통과이며재시험대기로돌리지않는다. 새최초연결/목록이름·소속표시도source2602e45/5bd8dde6·DB0034로개발반영/실행검증완료·Flutter 연결은 #12 전체40/#16 전체26의 5f024e53 구현·push 자체 보고 수신, 새 기기 인수는 미확인이다. 상세12조합에서대상group_member는조회자소속과무관하게일치해Backend누락미재현·프로필위치예시인계다.

레이드 모집 1차 구현·보고된 정상 흐름/표시의 사용자 기기 인수 완료, [Issue13 전체192 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438046779)으로 closed/completed다. 모집 관련 추가 Backend 요청은 없다. 차후 정밀도 소비·알럿·UX/소켓 등은 [보완 대장](../features/recruitment/follow-up-backlog.md)에 보존하며 현재 착수/인수 선행 조건이 아니다. 이전 미완료/종료 차단 판단과 사용자 정정은 [DEV_LOG](DEV_LOG.md)에서 확인한다.

| 기능 | 상태·기준 |
|---|---|
| [로그인·계정](../features/login-account/README.md) | Google/자체 세션·복구·회원 설정·개인 게임키·한도 구현. 추가 공급자·탈퇴/운영정책은 별도 미완료. |
| [원정대·캐릭터](../features/rosters/README.md) | 등록/갱신·소유 인증/V2분쟁·현재/퇴역 읽기·전투력/분석·대표/활동/표시·일괄조회 구현. V2분쟁 실인수 보류, 생명주기 증거/활동 자동추가·명시제외 후속은 별도. |
| [레이드·주간 기록](../features/raids/README.md) | 공개 카탈로그·서버 주차·개인 완료/주간 summary 구현. 최신 게임패치 검증과 실제 이용 통계 집계는 별도 미완료. |
| [그룹](../features/groups/README.md) | 생성/가입/초대·코드/차단·관리조회·그룹장 이전/일반탈퇴 구현·dev통합. 1차 표시조회/활동/집계·해산/추방/대표변경·공통방안내/기존레이드보존 구현·격리검증·개발반영완료. 안내된기존그룹정상흐름은사용자기기보고통과. 최초연결/목록표시도 Backend 개발반영·인계 완료, 새 Flutter 연결 완료 보고 수신·기기 인수 대기. 복구승계는 별도 미결정. |
| [모집·일정](../features/recruitment/README.md) | C/N 생성·참가/관리·일정/조율·완료/탈퇴·검색/후보·표시·분 단위 명시 시각과 재신청 보완까지 구현/개발 반영. 1차 사용자 기기 인수 완료·Issue13 종료. [기존 모집 통합](../features/recruitment/integration-checkpoint-2026-10-27.md)·[재신청 통합](../features/recruitment/reapplication-integration-2026-10-27.md). 다른 관련 Issue 상태는 추적표를 따르며 이번에 일괄 종료하지 않는다. |
| [공통 개발·운영](../engineering/README.md) | 현재sourceb8542ef/이미지930c25f8·DB0035. [최신 실행집계](../engineering/operations/records/cycle-group-policy-rollout.json): 기존114표2,038행 보존·정책36·소스274/runtime31·두전체계약/HTTP11·READ ONLY profile/worker/healthy 확인. |

개발 계약은 [two-cycle OpenAPI](../../openapi/two-cycle.openapi.yaml), 기본앱 보존 계약은 [기본 OpenAPI](../../openapi/openapi.yaml)다. two-cycle은 실행 구성,0035는 현재 개발 DB마이그레이션 단계다. 구현·합성 검증·실제 서비스 읽기/HTTP·사용자 기기·성능/운영 인수는 구분한다. 현재 문서 정리로 미수행 성능/실회원 원ACK 동일 키 검증을 완료로 바꾸지 않는다.

문서 운영 #29는 양측 반영·대조와 사용자 최종 확인 보고로 추가 수정 대기가 없다. [Backend 개선 계획](backend-improvement-plan.md)·[진단 근거](../engineering/development/pre-beta-diagnosis-2026-10-30.md)를 다음 작업 기준으로 연결한다. F01 정리 배치의 미처리 조건·결정적 순서를 구현하고 두 DB 단계의 격리 검증을 완료했다([결과](DEV_LOG.md#f01-registration-cleanup)). F01은 c94ce88로 게시·이번0035 이미지에 코드 포함/미처리0·수동정리 없음·PR31 Git 통합 완료다. F02는 로컬 설정 조사 후 공개 환경 미정으로 보류([재개 조건](backend-improvement-plan.md#f02-resume)), F03~F10은 미착수다. 진단·그룹 인계 문서는48bf88c로 게시 완료, PR30으로 dev/main 통합했다. 베타 개선 기록은 fix/backend-beta-readiness에 보존하고 사용자 지시로 그룹 #16의 새 정책 정정을 우선한다. [전체27번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521839291)·[전체28번째 고정 문서 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6521897849), Flutter 문서78e53aa0 기준이다. [주차별 그룹 변경·승계 계약](../features/groups/cycle-group-policy.md)을0035 원본·기존 명령/조회에 구현했다. 구현b212ad0는 commit/push·원격일치 및 [#16 전체30번째 Backend 고정 계약 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6523975291) 완료다. 격리 검증·계약 인계와 실제0035 반영/Flutter 연결/기기는 구분하며 [NEXT_WORK](NEXT_WORK.md)를 따른다. 사용자 승인으로 sourceb8542ef·이미지930c25f8·DB0035에 실제 반영/실행검증 완료다. [#16 전체31번째 Backend 반영 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6524503597) 완료, Flutter 연결·현재 안내범위 기기 인수는 전체37 보고로 완료됐고 별도 상세500 조사는 남았다. 이전 계약 소비 회신은 [#12 전체40번째 Flutter · 목록/소속 표시 소비 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503895589)·[#16 전체26번째 Flutter · 최초 연결 소비 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503895060)이며 당시 추가 API 변경/Backend 반복 검증 요청은 없었다. 기존 계약의 기기 대기는 유지하고 새 #16 정책은 위 고정 계약으로 구현·인계했으며 실제0035 반영은 위 최신 기록을 따르며 새 앱/기기는 별도다.

주제별 미완료는 [ISSUE_TRACKER](ISSUE_TRACKER.md), 과거 결정/검증/장애·통합은 [DEV_LOG](DEV_LOG.md)를 따른다. [AGENTS](../../AGENTS.md)·[협업 규칙](../engineering/collaboration/api-collaboration.md)·[문서 대응표](../engineering/documentation/README.md)를 작업 기준으로 사용한다.

2026-10-31 최신: [#16 전체37 Flutter 사용자 앱기기 전체통과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6529987970)를 수용해 현재 안내한 그룹·레이드 연결/기기대기를 해소한다. 위 기기 미확인 문장은 이전시점 이력이다. 별도 [전체36 상세500 조사요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6529904340)은 [READ ONLY 대조](../features/groups/detail-500-investigation.json)에서 과거500 확인·현재미재현/원인미확정이다. Flutter 당시 query/동작근거 대기 후 Backend 표적조사를 이어가며 서버교체/실자료변경은 하지 않았다. Penpot/운영인수·Issue종료는 별도다.

상세500 후속은 최신dev1f0b588에서 fix/raid-detail-errors로 분기했다. #16 전체39 Flutter는 당시 query/동작 기록없음·자연재발근거대기를 회신했다. 전체40 Flutter 통합b8b20b50/2,730PASS·분석0은 자체보고다. 별도 프로세스의 READ ONLY ASGI HTTP228호출은158정상/70예상거절·예상외예외0(실제리스너 인증HTTP와 구분), 추가과거17:48:47의500도 원인미확정이다. 서버/자료/제품코드는 변경하지 않았다. 최신 다음실행/집계를 따른다.

2026-10-31 사용자 확정: 상세500은 Native 탭로딩 터치제한·기기확인 완료를1차대응으로 유지하고 별도원인추적은중단한다. 과거500 원인미확정 기록은 보존하며 위 자연재발/추가근거 대기는 현재실행에서 제거한다. 다음은 #15 분쟁 소유이전의 그룹/레이드 영향 식별·타원정대보존/정리·복구정책을 Backend에서 조사하고 Flutter와 협의한다. 제안검토이며 정책구현/실자료변경 승인이 아니다.

분쟁영향 후속의 현재checkout은 feat/ownership-dispute-policy(500추적중단기록9a13af7보존 분기)다. [관계·현재가드/미합의선택지](../features/rosters/ownership/dispute-impact-review.md)에 그룹사용자가입/원정대별ownership_lost·참가character/실제T 추적을 정리했다. 현재활성레이드소유이전은보류이며자동정리/이전후복구는미구현이다. 격리기존4PASS·다중원정대2PASS는현재기능근거이고 #15 정책/소비협의가다음이다.

2026-11-01 최신 Git: 사용자승인 [PR32](https://github.com/heo0328/lostparty-backend/pull/32)·병합e3a657a에 분쟁영향검토/합성시험·500추적중단기록을 dev통합했다. main은 dev의후행기록 포함같은커밋으로동기화한다. 현재checkout dev·feat/ownership-dispute-policy/fix/raid-detail-errors 로컬/원격정리, 미완료 activity-selection보존이다. 위브랜치/미통합문장은당시이력이며 정책은여전히협의중/미구현,실행sourceb8542ef·DB0035는변경하지않았다.
