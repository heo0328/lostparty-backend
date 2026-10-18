# LostParty Backend 기능 지도

2026-10-18. 다음 실행/대기는 [NEXT_WORK](NEXT_WORK.md), 완료·검증·장애/Git이력은 [DEV_LOG](DEV_LOG.md). 기존로컬Docker/API8000·DB0016·자료/키로 개발한다. [PR14](https://github.com/heo0328/lostparty-backend/pull/14)에서dev병합/main동일위치push·원격확인완료(코드merge a0e2799/마감문서후행포함). 완료feat/raid-services로컬/원격정리. [#8 전체152번째Backend통합결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6249274152). 다음은최신dev기반feat/group-management의G3명세준비이며API계약/구현미착수다.

| 영역 | 현재 상태·기준 |
|---|---|
| 협업/API | [AGENTS](../../AGENTS.md), [API협업](../API_COLLABORATION.md). 공식채널heo0328/lostparty-backend Issues,Flutter로컬소스접근/수정없음. [OpenAPI](../../openapi/openapi.yaml)가REST원본이며실행객체전체비교 |
| 인증 #2 | Google로그인/세션/복구6 API·초기완료. [인증안내](../AUTH_DEVELOPMENT.md), [운영후속](../ISSUE_2_FOLLOWUP.md). Apple/Discord/탈퇴·운영인수별도 |
| 원정대/회원 #3~#7 | 현재회원등록/복원·목록·전투력/회원설정/암호화개인키/본인키복원구현. [계정](../ISSUE_3_DEVELOPMENT.md), [전투력](../ISSUE_5_DEVELOPMENT.md), [회원설정](../ISSUE_6_MEMBER_SETTINGS.md), [키](../ISSUE_7_DEVELOPMENT.md) |
| #8 대표/활동·표시 | 현재대표/활동선택·개인역할요약/표시서버저장구현. 수동레벨하한없음/초기기본선택1700. [대표계약](../ISSUE_8_REPRESENTATIVE_CONTRACT_DRAFT.md), [수동정책](../ISSUE_8_MANUAL_ACTIVITY_POLICY_PLAN.md), [개인표시](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md). 신규/첫1700자동추가·수동제외영속정책은122번째후속/미구현 |
| #8 소유/생명주기 | 현재/이력·claim·suspect/내부퇴역·실제목록갱신·서버장비인증/대상·현재본인ALREADY차단/동일회원재등록연결구현. [L1](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md), [목록갱신](../ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md), [장비](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [현재소유정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md). 타회원챌린지허용과소유이전완료는별개 |
| #8 영어 검색 입력 | 131번째 Flutter 요청 대응 구현/로컬반영·관련241PASS. ASCII 대소문자 입력만 유일한 API 원문으로 해석. 신규 등록/챌린지·Armory/receipt 원문 사용, exact 고정 대상/서버/UUID/claim·입력 cache/digest 유지. [장비 안내](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [#8 전체132번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236684349)/28ea022 push. 134번째Flutter가사용자혼합검색성공확인(검색범위완료) |
| #8 24시간 소유권 챌린지 | [V2개발](../ISSUE_8_OWNERSHIP_DISPUTE_DEVELOPMENT.md)·[기술합의](../ISSUE_8_OWNERSHIP_DISPUTE_V2_CONTRACT.md). 11동작/발견·복원/선택방어/최대3건·일괄방어·선성립worker/원자이전Backend구현·관련194/333/최종21PASS(중복). 최종이미지/DB0016로컬반영,전체844PASS/기존검사수정후관련58PASS·실행계약일치,7ba6297 push·원격확인/[144번째Backend인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245920315)완료,다음FlutterV2연결/최소UI. [142번째Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245421798)계약수용·실연결/UI후속. 실제파티active영향adapter부재는review_required. V2자동정리미구현 |
| DB 공통 날짜 | [기준](../DATABASE_RECORD_TIMESTAMPS.md). 48개 업무표 record_created_at/record_updated_at·DB trigger·알려진과거만복사/미상NULL·기존업무일자/API불변. 0016/기존로컬반영·관련58PASS·49표행수보존(지문비교한계DEV_LOG). 미래기간별정리기반이며삭제/보관정책미추가 |
| 실제확인 | #8 98번째사용자1회인증성공/서버대조,108번째새기기목록/인증표시정상. #11 manual true실제반영성공. 전체캐릭터자동복원/다른기기완료·수정UI/분쟁인수·모집실기기와구분 |
| #10 카탈로그/주차 | 공개GET2개·5raid/13difficulty/2026.08.20초기자료·KST수요일06시cycle. [안내](../ISSUE_10_RAID_CATALOG_DEVELOPMENT.md). Backend/로컬완료,Flutter소비보고·실제최신게임패치검증과별개 |
| #11 주간원장 | 본인최대50캐릭터배치GET/현재주차manual PUT·난이도공유원장/원자명령·점유가드구현. [안내](../ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md). 실제파티/점유중영향확인실행미연결. i는별도현재방membership이며기존완료/점유제약유지 |
| #12 그룹 G1 | 그룹7동작/본인한도GET,현재활동/소유·가입한도/CAS·검색/서명cursor·공개/회원권한구현/로컬반영. [G1](../ISSUE_12_GROUP_G1_DEVELOPMENT.md), [12번째 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6234628340). Flutter13번째는접수만/연결후속 |
| #12 공통한도 | 계정별기본15/5/10·쓰기없는조회·사용량head·서버변경권한/감사·실제그룹집계. [계약](../ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md), [L0](../ISSUE_12_MEMBER_LIMITS_FOUNDATION.md). 모집은null/unavailable. 개인초과직접참가차원별제한/그룹자체정원초과그룹전용방전체제한확정,실제방guard미연결 |
| #12 그룹 G2 | 초대/신청/수락·승인/거절·취소/차단·해제/코드20동작구현·관련190PASS/77.70초·실행OpenAPI일치·0014/기존로컬반영. [계약](../ISSUE_12_GROUP_G2_SPEC.md), [개발](../ISSUE_12_GROUP_G2_DEVELOPMENT.md). 일반멤버초대·권한코드조회/복사·공개OFF숨김만·10분재생성·이전코드폐기. 실제회원쓰기/Flutter/실기기는미확인. G3는후속 |
| #13 방/통계 | 실제room/회차/신청·확정참가/주간연결미구현. [통계선행제안](../ISSUE_13_WEEKLY_STATISTICS_DRAFT.md)/8번째Backend,Flutter귀속/조회세부검토후원천→마감/집계. 개인수동체크/현재한도와통계는분리 |
| 첫화면일괄조회/Flutter현재 | [145번째Flutter요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247415075)·[개발](../ISSUE_8_ACCOUNT_BOOTSTRAP_DEVELOPMENT.md). GET /v2/me/account-bootstrap 구현/로컬8000·기존표READ ONLY/RR·권한/전체활동profile/주간일관성·한도오류/16MiB. 261PASS/실행계약일치·DB0016/행수보존. 8d03e96 push·원격확인/[전체146번째Backend인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6247620588)완료. [148번째Flutter실기기로그](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6248323346)로실회원GET1회·76→29요청관찰수신/추가Backend요청없음. [151번째Flutter마감](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6248792000)54bacd2 push/전체1662PASS·analyze0보고·현재개선수용,dev/main통합예정/전체동작인수별도. G3확정범위명세/독립서버처리→#13R1/R2계약/기초작업가능. V2분쟁은144수신만/별도소비후속 |
| 별도/보존 | 자동퇴역·모든명령영속복구·WebSocket/운영배포미완료. 기존개발자료/키/flag유지·베타직전초기화별도지시. Firebase이관/삭제·새8001/백업복원이관·기본재인수없음 |

Backend완료·계약인계·Flutter적용·실기기·운영완료는서로별개다. 과거문서의당시미구현/브랜치/DB상태는현재기능상태로해석하지않는다.

G2구현/계약c06d3d2 작업브랜치push·원격확인, [#12 전체15번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6235311908). 현재G2 Backend구간완료/Flutter연결별도·다음G3명세작업가능이다.
