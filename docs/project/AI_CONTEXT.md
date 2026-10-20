# LostParty Backend 기능 지도

현재 모집은 1a007eb 로컬·미push / [전체54번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284804193) / [R2-A 개인표/제출표](../ISSUE_13_R2A_AVAILABILITY_IMPLEMENTATION.md) 저장·권한/CAS/원ACK·미활성HTTP/정확한draft 계약 구현까지 진행했다. 다음 Backend R2-B 관계/캐릭터/슬롯·주간 원장 연결이며 Flutter 회신 대기가 아니다. 원본 OpenAPI/main·API8000/개발DB0016은 유지하고 통합/Flutter 적용은 미완료다. 검증/Git은 NEXT_WORK·DEV_LOG 기준. 아래는 단계별 당시 기록이다.

최신 구현: [#13 전체53번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284451921)/[R1-B 추가원천·P1 성공보존](../ISSUE_13_R1B_SOURCES_IMPLEMENTATION.md) fbf1f2f 로컬·미push. 0020/추가17원천과P1쓰기transaction연결, NULL/실패보존·낮은최신관측/지연·동시성/퇴역정리·기존자료보존검증완료. 회귀183PASS/최종보완45PASS(일부중복). 다음BackendR2 개인표/제출·관계/원장·정확한HTTP계약. 기존OpenAPI·실행API/개발DB0016·이미지/자료미반영/새모집연결미완료/Flutter시험요청없음. NEXT_WORK기준.

최신 구현: [#13 전체52번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6284008917) / [R1-A 원천·보존이행](../ISSUE_13_R1_STORAGE_IMPLEMENTATION.md) fdf2f58 로컬·미push. 7개모델/0019추가이행·기존전체자료/시각·표시빌드보존/제한계정·교차귀속/기간/슬롯/read-only준비검사등33PASS(28.78초). 다음Backend나머지원천/P1성공보존→개인표·관계원장/예약·투표·완료·필터/HTTP계약통합구현. R1전체/통합기능완료아님. 원본OpenAPI·실행API/개발DB0016·이미지/자료미변경, Flutter시험요청없음. NEXT_WORK기준.

최신: [#13 Flutter전체51번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283811575)에서R4의두기술경계소비대조마감/제품결정완료. 다음Backend정확한OpenAPI·모델/이행·읽기쓰기통합구현/내부R1~R5검증이며같은설계재협의없음. 최종검색명세에기존raid/difficulty/정렬·자리필터대응과회원조건결합을보존하고상한은측정으로고정한다. 실제API/암호화/DB동시성인수·Flutter연결은미완료, NEXT_WORK기준.

최신: [#13 전체50번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283620362)에 [49번째 대응 기술 보완4판](../ISSUE_13_R0_TECHNICAL_BOUNDARIES_R4.md) d1bdb47 로컬·미push 전문/JSON8개 게시. 회원별캐릭터AND/OR·복수그룹동일회원/그룹연결·입장scope 분리와 권한내 영향context/타인원장CAS제거·N1확정을 반영했다. 다음Flutter두경계만재대조→정확한OpenAPI/구현계약동시고정·통합구현. 최종API인수/서버DB이행·Flutter연결은미완료, NEXT_WORK기준.

최신: [#13 전체48번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6283178369)에 [46/47번째 반영 계약 보완3판](../ISSUE_13_R0_CONTRACT_R3.md) 7e9c2f2 로컬·미push 전문 게시. 확정10정책·nullable숙련도/개인profile출처·미정/요일만/전체주차·통합타입/좌석·권한내 그룹필터/JSON9개를 반영했다. 다음 Flutter 재대조→정확한 schema/통합 구현. N1 변경 제안은 아직 미채택, 자동 추가0은 제외다. 보완안 게시 완료이며 최종 인수/구현·서버/DB/Flutter 적용은 미완료. NEXT_WORK 기준.

최신: [#13 전체45번째 Backend R0 보완2판](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6272271633)에 [44번째 소비 검토 대응](../ISSUE_13_R0_CONSUMER_CORRECTIONS.md) e806ee4 로컬·미push 전문 게시. 입력/세션·버전/CAS 출처·기능 지도·점수 보존 규칙을 보완했다. 다음 Flutter 재대조·experienceLevel 실제 값 대응→필요 결정/정확한 schema 고정. P1 실제 코드는 요약 덮어쓰기이며 최근 성공 snapshot은 신규 설계/미구현이다. 계약 최종 합의·API/DB 반영·Flutter 연결은 미완료. NEXT_WORK를 따른다.

최신2026-10-20: [R0 계약 고정 초안](../ISSUE_13_FIXED_CONTRACT_DRAFT.md) 35dd5f9 로컬/미push를 [#13 전체43번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271860507)에 본문 전체 게시했다. Flutter41/42번째에 대한 DTO·명령/권한/오류·원자 효과/부분 해제·호환/구현 순서 답변이다. 다음 Flutter 실제 Router/DI/Repository·구자료 대조 → Backend 누락 DTO/정확한 요청 schema·필요 G1~G7 보완 → 계약 고정. 확정된 점수 비교/기간 합산·06 운영/10 플레이는 재질문하지 않는다. 초안 게시 완료이며 최종 합의/통합 구현·API/DB 반영/Flutter 적용은 미완료다. 코드·DDL·원본 OpenAPI·서버/자료 변경이나 새 기능 시험은 없었다. 다음 실행은 [NEXT_WORK](NEXT_WORK.md)를 따른다.

최신2026-10-20: [정책 보완안](../ISSUE_13_OCT20_POLICY_REVISION.md) c47afef 로컬/미push·[#13 전체40번째Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6271452128)은Flutter34~39번째반영(게시후39추가확인/같은본문수정). 시간중복경고/자동추천회피·인원별동의수·초록pending본인확인→참가확인/예약생성·수10시반복재개·기간대체/합산·OFF갱신/경고차단철회·공개원pending외부승인·혼합일행4·인증회원개인표가최신기준이다. 다음Backend 고정DTO/명령/호환·내부구현순서정리/Flutter대조. 아래전원동의/배타예약·확인효과미정/수10시미정/과거회신대기는당시이력이다. 코드/DDL/서버/실행계약미변경.

최신대조(2026-10-19): [#13 Flutter전체32번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6268865657) 기술보완요청에[Backend전체33번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6269041117)로답했다. [기획안9절](../ISSUE_13_INTEGRATED_BOUNDARY_PROPOSAL.md) 수정1e2f706 로컬/미push: 편집원본분리·latest후보계산정정·반복round하한·제한탐색/명시선택/계산한계·첫임계치두정책비교/귀속재검사다. 다음Flutter 제품선택/대조→Backend경계확정이며코드/DDL/실제API승인아니다. 다른열린이슈의추가회신은없다.

통합기획게시(2026-10-19): [설계안](../ISSUE_13_INTEGRATED_BOUNDARY_PROPOSAL.md) d17a89e 로컬커밋/미push·[#13 전체31번째Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6268024511)에관계도·수명/권한/명령·개인표/일정/예약DTO·마감/임계치·완료/미완료·기존이행·필수결정표본문전체를게시했다. 다음Flutter대조/Backend보완·필요사용자결정후경계확정이며구현/최종API/서버활성화는아니다. 아래 ‘다음 Backend 설계’는 게시 전 기록이다.

현재(2026-10-19): #13 Flutter전체24~29번째수신/기존후보대조. [수신대장](../ISSUE_13_INTEGRATED_REQUIREMENTS_INTAKE.md)·[전체30번째Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6267793280). 최신27번째통합목표(축소1차대체)와29번째현재참가자누구나방전체이번주미완료종료선언을보존했다. 다음Backend 통합경계설계→Flutter대조/필요결정→확정후구현이다. 실제코드/DDL/계약·서버활성화는미완료이며아래기본틀만유지/회신대기는당시기록이다.

현재브랜치feat/raid-recruitment. 활동설계feat/activity-selection/89a3248(설계5fff83b·#18전체3번째접수/별도소비검토대기)은로컬커밋/미push로별도보존한다. 기존F1/F2/F3기반을재사용하되유한단일Round/Membership/방시간겹침검사는통합모델완료가아니다. 상세다음작업은NEXT_WORK기준이다.

현재 범위(2026-10-19 사용자 정정): [#13 전체20번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6264202734). 모집 조건을 네이티브와 협의 중이므로 기본 관계/조회·원자성/중복요청·사용량/보존검증·후보 정지/정리 기반까지만 유지한다. 기본 구현은 로컬 완료·미push, 조건 의존 후보는 변경 가능한 초안이며 최종계약/실제활성화는 협의 후 반영한다. 앞선 최초지원범위 선택 질문은 재요청하지 않는다. 아래 답변대기/다음실제연결은 정정 전 기록이다.

후보 HTTP 정지 연결(2026-10-19): [준비 기록](../ISSUE_13_F3_PREPARATION.md) ffa3575 로컬커밋/미push·관련97PASS/31.73초. 후보 생성/신청/가입/승인·context/approve permissions에 정지제어를연결하고원ACK/조회/정리를유지했다. 실제main/usage GET/원본계약/개발서버DB미변경. 최초공개·현재주차유한일정·문턱없음지원결정을사용자에게질문했으며답변후실제연결한다. 아래준비기록의후보미연결은당시상태다.

F3-B 독립 보존/권한시험(2026-10-19): [준비 기록](../ISSUE_13_F3_PREPARATION.md)·시험06a530f 로컬커밋/미push, 제한 LOGIN role의0016→0017→0018·합성 기존자료/시각·legacy 신청NULL 및 실제 서비스 조회/승인/정리 검증, 관련준비25PASS/9.88초. 개발DB/이미지/API/최종계약은 미변경. 다음은 필요한 제품결정 후 실제호출부/계약연결이며 #13전체17~19번째 협업경계를 유지한다.

F3-A 독립 준비(2026-10-19): [사용량/준비검사/정지제어](../ISSUE_13_F3_PREPARATION.md) a0a515c 로컬커밋·미push·격리144PASS/42.77초, [#13 전체19번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6263654624). 기존 GET usage는unavailable, main/candidate router·permissions/context/lifespan은미연결·원본OpenAPI/개발서버DB미변경이다. 사용자결정과실제활성화/최종계약고정은별도이며아래설계기록과현재준비완료를구분한다.

F3 설계(2026-10-19): [활성화 설계](../ISSUE_13_F3_ACTIVATION_DESIGN.md)에 공유 usage 집계·기존 한도 응답 실수치 전환, main router/최종 계약·DB 준비 검사, 신규 참가 정지/조회·정리 유지,0017→0018·이미지 전환/복구·게시 순서를 기록했다. 이번은 설계 문서이며 해당 코드/설정/DB/서버는 아직 미변경이다. 설계 중 추가된 #13 전체17번째 Flutter Q1~Q3 검토를 설계7~9절에 반영했고 #18 Backend 설계를 공유했다. 최초 실제지원범위/전투력입력·수치/그룹탈퇴제한·정리공개는 사용자결정이며 독립F3-A 준비와 실제활성화/계약고정을 구분한다.

현재 통합 기준(2026-10-19): G3 완료 관리GET/이전/일반탈퇴는 [PR20](https://github.com/heo0328/lostparty-backend/pull/20) bb144e0로 **dev 통합**, 후행 기록 ce3064f까지 원격확인했다. feat/group-management 로컬/원격 정리·main77a1fe5 유지, [#16 전체6번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6262944673). 기존 feat/raid-recruitment의 c41fd03/F1·F2 커밋을 보존하고 dev를 merge했다. 모집 코드는 미push/개발서버미반영이며 다음F3다. 아래 기존 main/dev 미병합 표기는 통합 전 당시 기록이다.

모집 F2-B(2026-10-19): [후보 HTTP18동작](../ISSUE_13_F2_HTTP.md) 9fb2058 로컬커밋·미push, HTTP43+F2-A23+F1 32+시각3 **101PASS/35.00초**. [#13 전체15번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260695606). 격리 앱에서생성/신청/승인·직접가입·조회·탈퇴/이전/종료와입력/인증·원ACK/경합/rollback검증완료다. main 앱/router/OpenAPI·개발DB0016/이미지/API8000은미반영·기존서버healthy/health200이다. 다음Backend F3 최종계약·개발반영준비, Q1~Q3/Flutter #15 우선유지. 아래는이전단계기록이다.

모집 F2-A(2026-10-19): [내부 조회/권한·참가조건](../ISSUE_13_F2_READS.md) e74d850 로컬커밋·미push, 격리 PostgreSQL 조회23+F1 32+시각3 **58 PASS/23.38초**. [#13 전체14번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6260548709). 읽기전용snapshot/서명cursor·본인context·과거빌드 보존/0018 신청snapshot 열(격리DB만)이다. 다음Backend F2-B 후보HTTP연결이며 main 앱/router/OpenAPI·개발DB0016/서버는미반영, Q1~Q3/Flutter #15 우선유지. 아래 과거단계 기록과 구분한다.

모집 후속 설계: [F2 구현설계](../ISSUE_13_F2_IMPLEMENTATION_DESIGN.md)에 조회/권한별응답·정책→격리HTTP검증→F3 DB/앱/계약반영·인계 순서를 기록했다. 이번은문서설계이며API/DB·기능코드변경없음.

현재 브랜치 정정(2026-10-19): 모집 F1/F2는 **feat/raid-recruitment**에서 진행한다. G3의 feat/group-management/349fb79에서 로컬 분기해 F1 코드·문서를 보존했다. F1 구현/시험은 `9664fb4`로 로컬 커밋했고 설계·진행 문서는 후행 커밋으로 구분한다. G3 브랜치/원격은 유지·main/dev 미병합이며 모집 브랜치는 미push/추적없음이다. 아래 당시 작업 브랜치 기록과 현재 위치를 구분한다.

2026-10-19 현재: G3 관리 GET·이전/일반 탈퇴 POST 구현/기존API8000 반영·DB0016 유지. 격리 PostgreSQL/HTTP148 PASS/55.73초·실행 OpenAPI 일치. [개발 안내](../ISSUE_16_GROUP_G3_DEVELOPMENT.md), [최신 다음 실행](NEXT_WORK.md). 원본 #12의 Backend 독립 설계/구현 요청에 따라 이전 소비회신 선행 대기를 정정했다. Flutter G3 수용/연결·실회원쓰기·실기기·운영은 별도 미확인, 조건부 해산/추방/대표 변경/실제 방 처리는 미구현이다. 아래10-18 기록과 구분한다. G3 구현/계약 `332a8ab` 작업브랜치 push·원격확인/[전체4번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6258994902) 완료, main/dev 미병합. R1/R2 [상세계약초안](../ISSUE_13_R1_R2_CONTRACT_DRAFT.md)을 [#13 전체12번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259336924)에게시했다. F1[내부기반](../ISSUE_13_F1_FOUNDATION.md)작성·233회귀PASS/최종F1시각35PASS(중복)·[#13전체13번째](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6259515470)회신, 다음Backend F2지원범위/HTTP연결, Flutter Q1일정/Q2전투력근거/Q3그룹탈퇴후room경계충돌확인. 새HTTP/개발DB/서버변경없고0017파일은격리DB만적용·코드9664fb4/명세후행로컬커밋·모두미push·확인전해당분기활성화없음. [#16 전체5번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6259125692)가 G3 문서상 소비충돌 없음을 확인했다. #15는 [전체3번째 D2](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6259074435) 내부연결174고유테스트/분석0보고·미커밋/미push·UI V1, 다음D3이며 추가Backend요청없다. #19전체1번째의4미확정정책은합의완료로취급하지않는다.

2026-10-18. 다음 실행/대기는 [NEXT_WORK](NEXT_WORK.md), 완료·검증·장애/Git이력은 [DEV_LOG](DEV_LOG.md). 기존로컬Docker/API8000·DB0016·자료/키로 개발한다. [PR14](https://github.com/heo0328/lostparty-backend/pull/14)에서dev병합/main동일위치push·원격확인완료(코드merge a0e2799/마감문서후행포함). 완료feat/raid-services로컬/원격정리. [#8 전체152번째Backend통합결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6249274152). 현재feat/group-management는49cd8cc까지push완료다. [G3명세](../ISSUE_16_GROUP_G3_SPEC.md)를 [#16 전체1번째 Backend](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6250563064)에 제안 게시했다. Flutter소비계약검토/Backend합의반영후구현·실행API미반영이다.

| 영역 | 현재 상태·기준 |
|---|---|
| 협업/API | [AGENTS](../../AGENTS.md), [API협업](../API_COLLABORATION.md). 공식채널heo0328/lostparty-backend Issues·한이슈한주제/[현재추적표](ISSUE_TRACKER.md),Flutter로컬소스접근/수정없음. [OpenAPI](../../openapi/openapi.yaml)가REST원본이며실행객체전체비교 |
| 인증 #2 | Google로그인/세션/복구6 API·초기완료. [인증안내](../AUTH_DEVELOPMENT.md), [운영후속](../ISSUE_2_FOLLOWUP.md). Apple/Discord/탈퇴·운영인수별도 |
| 원정대/회원 #3~#7 | 현재회원등록/복원·목록·전투력/회원설정/암호화개인키/본인키복원구현. [계정](../ISSUE_3_DEVELOPMENT.md), [전투력](../ISSUE_5_DEVELOPMENT.md), [회원설정](../ISSUE_6_MEMBER_SETTINGS.md), [키](../ISSUE_7_DEVELOPMENT.md) |
| #8 대표/활동·표시 | 현재대표/활동선택·개인역할요약/표시서버저장구현. 수동레벨하한없음/초기기본선택1700. [대표계약](../ISSUE_8_REPRESENTATIVE_CONTRACT_DRAFT.md), [수동정책](../ISSUE_8_MANUAL_ACTIVITY_POLICY_PLAN.md), [개인표시](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md). 신규/첫1700자동추가·수동제외영속정책은#18(122번째출처)후속/미구현 |
| #8 소유/생명주기 | 현재/이력·claim·suspect/내부퇴역·실제목록갱신·서버장비인증/대상·현재본인ALREADY차단/동일회원재등록연결구현. [L1](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md), [목록갱신](../ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md), [장비](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [현재소유정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md). 타회원챌린지허용과소유이전완료는별개 |
| #8 영어 검색 입력 | 131번째 Flutter 요청 대응 구현/로컬반영·관련241PASS. ASCII 대소문자 입력만 유일한 API 원문으로 해석. 신규 등록/챌린지·Armory/receipt 원문 사용, exact 고정 대상/서버/UUID/claim·입력 cache/digest 유지. [장비 안내](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [#8 전체132번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236684349)/28ea022 push. 134번째Flutter가사용자혼합검색성공확인(검색범위완료) |
| #8 24시간 소유권 챌린지 | [V2개발](../ISSUE_8_OWNERSHIP_DISPUTE_DEVELOPMENT.md)·[기술합의](../ISSUE_8_OWNERSHIP_DISPUTE_V2_CONTRACT.md). 11동작/발견·복원/선택방어/최대3건·일괄방어·선성립worker/원자이전Backend구현·관련194/333/최종21PASS(중복). 최종이미지/DB0016로컬반영,전체844PASS/기존검사수정후관련58PASS·실행계약일치,7ba6297 push·원격확인/[144번째Backend인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245920315)완료,다음FlutterV2연결/최소UI. [142번째Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245421798)계약수용·실연결/UI후속. 실제파티active영향adapter부재는review_required. V2자동정리미구현 |
| DB 공통 날짜 | [기준](../DATABASE_RECORD_TIMESTAMPS.md). 48개 업무표 record_created_at/record_updated_at·DB trigger·알려진과거만복사/미상NULL·기존업무일자/API불변. 0016/기존로컬반영·관련58PASS·49표행수보존(지문비교한계DEV_LOG). 미래기간별정리기반이며삭제/보관정책미추가 |
| 실제확인 | #8 98번째사용자1회인증성공/서버대조,108번째새기기목록/인증표시정상. #11 manual true실제반영성공. 전체캐릭터자동복원/다른기기완료·수정UI/분쟁인수·모집실기기와구분 |
| #10 카탈로그/주차 | 공개GET2개·5raid/13difficulty/2026.08.20초기자료·KST수요일06시cycle. [안내](../ISSUE_10_RAID_CATALOG_DEVELOPMENT.md). Backend/로컬완료,Flutter소비보고·실제최신게임패치검증과별개 |
| #11 주간원장 | 본인최대50캐릭터배치GET/현재주차manual PUT·난이도공유원장/원자명령·점유가드구현. [안내](../ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md). 실제파티/점유중영향확인실행미연결. i는별도현재방membership이며기존완료/점유제약유지 |
| #12 그룹 G1 | 그룹7동작/본인한도GET,현재활동/소유·가입한도/CAS·검색/서명cursor·공개/회원권한구현/로컬반영. [G1](../ISSUE_12_GROUP_G1_DEVELOPMENT.md), [12번째 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6234628340). Flutter13번째는접수만/연결후속 |
| #12 공통한도 | 계정별기본15/5/10·쓰기없는조회·사용량head·서버변경권한/감사·실제그룹집계. [계약](../ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md), [L0](../ISSUE_12_MEMBER_LIMITS_FOUNDATION.md). 모집은null/unavailable. 개인초과직접참가차원별제한/그룹자체정원초과그룹전용방전체제한확정,실제방guard미연결 |
| #12 그룹 G2 | 초대/신청/수락·승인/거절·취소/차단·해제/코드20동작구현·관련190PASS/77.70초·실행OpenAPI일치·0014/기존로컬반영. [계약](../ISSUE_12_GROUP_G2_SPEC.md), [개발](../ISSUE_12_GROUP_G2_DEVELOPMENT.md). 일반멤버초대·권한코드조회/복사·공개OFF숨김만·10분재생성·이전코드폐기. 실제회원쓰기/Flutter/실기기는미확인. G3는#16후속/이#12는Flutter연결만유지 |
| #13 방/통계 | F1 9664fb4/F2-A e74d850/F2-B후보HTTP 9fb2058 로컬커밋·101PASS, main API/개발DB/Flutter연결은미완료. [통계선행제안](../ISSUE_13_WEEKLY_STATISTICS_DRAFT.md)은#19로분리/원본13의8번째Backend,Flutter귀속/조회검토후원천→마감/집계. 개인수동체크/현재한도와통계는분리 |
| 첫화면일괄조회/Flutter현재 | [145번째Flutter요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247415075)·[개발](../ISSUE_8_ACCOUNT_BOOTSTRAP_DEVELOPMENT.md). GET /v2/me/account-bootstrap 구현/로컬8000·기존표READ ONLY/RR·권한/전체활동profile/주간일관성·한도오류/16MiB. 261PASS/실행계약일치·DB0016/행수보존. 8d03e96 push·원격확인/[전체146번째Backend인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247620588)완료. [148번째Flutter실기기로그](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6248323346)로실회원GET1회·76→29요청관찰수신/추가Backend요청없음. [151번째Flutter마감](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6248792000)54bacd2 push/전체1662PASS·analyze0보고·현재개선수용,dev/main통합예정/전체동작인수별도. G3확정범위명세/독립서버처리→#13R1/R2계약/기초작업가능. V2분쟁은144수신만/별도소비후속 |
| 별도/보존 | 자동퇴역·모든명령영속복구·WebSocket/운영배포미완료. 기존개발자료/키/flag유지·베타직전초기화별도지시. Firebase이관/삭제·새8001/백업복원이관·기본재인수없음 |

Backend완료·계약인계·Flutter적용·실기기·운영완료는서로별개다. 과거문서의당시미구현/브랜치/DB상태는현재기능상태로해석하지않는다.

G2구현/계약c06d3d2 작업브랜치push·원격확인, [#12 전체15번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6235311908). 현재G2 Backend구간완료/#12는Flutter연결별도·다음#16 G3명세작업가능이다.


2026-10-18 주제정리: #10/#11개인구간 완료종료, #8원본은미완료요구이관후보관종료. 열린주제/담당은 [이슈추적표](ISSUE_TRACKER.md) 기준(#12그룹Flutter/#13실제파티/#15V2Flutter/#16G3/#17생명주기/#18활동정책/#19통계). #8 153번째Flutter는dev/main deb2884d동기화/새V2브랜치설계·기능미착수를보고했다. 원본종료를요구폐기로확대하지않는다. 현재feat/group-management의G3명세는#16전체1번째에게시됐고코드/DB변경은없다. 명세문서미커밋/미push·실행OpenAPI미변경이며다음계약검토후구현이다.
