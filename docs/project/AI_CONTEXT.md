# LostParty Backend 기능 지도

2026-10-17. 다음실행/대기는 [NEXT_WORK](NEXT_WORK.md), 완료·검증·장애/Git이력은 [DEV_LOG](DEV_LOG.md). 기존로컬Docker/포트8000·DB0014·자료/키로개발을이어간다. 작업브랜치feat/raid-services,dev/main미병합. 이전#8구간은PR#9/dev-main860c84a로통합했다. 최신G2인계SHA/댓글은DEV_LOG기준이다.

| 영역 | 현재 상태·기준 |
|---|---|
| 협업/API | [AGENTS](../../AGENTS.md), [API협업](../API_COLLABORATION.md). 공식채널heo0328/lostparty-backend Issues,Flutter로컬소스접근/수정없음. [OpenAPI](../../openapi/openapi.yaml)가REST원본이며실행객체전체비교 |
| 인증 #2 | Google로그인/세션/복구6 API·초기완료. [인증안내](../AUTH_DEVELOPMENT.md), [운영후속](../ISSUE_2_FOLLOWUP.md). Apple/Discord/탈퇴·운영인수별도 |
| 원정대/회원 #3~#7 | 현재회원등록/복원·목록·전투력/회원설정/암호화개인키/본인키복원구현. [계정](../ISSUE_3_DEVELOPMENT.md), [전투력](../ISSUE_5_DEVELOPMENT.md), [회원설정](../ISSUE_6_MEMBER_SETTINGS.md), [키](../ISSUE_7_DEVELOPMENT.md) |
| #8 대표/활동·표시 | 현재대표/활동선택·개인역할요약/표시서버저장구현. 수동레벨하한없음/초기기본선택1700. [대표계약](../ISSUE_8_REPRESENTATIVE_CONTRACT_DRAFT.md), [수동정책](../ISSUE_8_MANUAL_ACTIVITY_POLICY_PLAN.md), [개인표시](../ISSUE_8_PERSONAL_PRESENTATION_DEVELOPMENT.md). 신규/첫1700자동추가·수동제외영속정책은122번째후속/미구현 |
| #8 소유/생명주기 | 현재/이력·claim·suspect/내부퇴역·실제목록갱신·서버장비인증/대상·현재본인ALREADY차단/동일회원재등록연결구현. [L1](../ISSUE_8_LIFECYCLE_DEVELOPMENT.md), [목록갱신](../ISSUE_8_OWNED_ROSTER_REFRESH_DEVELOPMENT.md), [장비](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md), [현재소유정책](../ISSUE_8_CURRENT_OWNER_POLICY_DEVELOPMENT.md). 타회원챌린지허용과소유이전완료는별개 |
| 실제확인 | #8 98번째사용자1회인증성공/서버대조,108번째새기기목록/인증표시정상. #11 manual true실제반영성공. 전체캐릭터자동복원/다른기기완료·수정UI/분쟁인수·모집실기기와구분 |
| #10 카탈로그/주차 | 공개GET2개·5raid/13difficulty/2026.08.20초기자료·KST수요일06시cycle. [안내](../ISSUE_10_RAID_CATALOG_DEVELOPMENT.md). Backend/로컬완료,Flutter소비보고·실제최신게임패치검증과별개 |
| #11 주간원장 | 본인최대50캐릭터배치GET/현재주차manual PUT·난이도공유원장/원자명령·점유가드구현. [안내](../ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md). 실제파티/점유중영향확인실행미연결. i는별도현재방membership이며기존완료/점유제약유지 |
| #12 그룹 G1 | 그룹7동작/본인한도GET,현재활동/소유·가입한도/CAS·검색/서명cursor·공개/회원권한구현/로컬반영. [G1](../ISSUE_12_GROUP_G1_DEVELOPMENT.md), [12번째 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6234628340). Flutter13번째는접수만/연결후속 |
| #12 공통한도 | 계정별기본15/5/10·쓰기없는조회·사용량head·서버변경권한/감사·실제그룹집계. [계약](../ISSUE_12_MEMBER_LIMITS_CONTRACT_DRAFT.md), [L0](../ISSUE_12_MEMBER_LIMITS_FOUNDATION.md). 모집은null/unavailable. 개인초과직접참가차원별제한/그룹자체정원초과그룹전용방전체제한확정,실제방guard미연결 |
| #12 그룹 G2 | 초대/신청/수락·승인/거절·취소/차단·해제/코드20동작구현·관련190PASS/77.70초·실행OpenAPI일치·0014/기존로컬반영. [계약](../ISSUE_12_GROUP_G2_SPEC.md), [개발](../ISSUE_12_GROUP_G2_DEVELOPMENT.md). 일반멤버초대·권한코드조회/복사·공개OFF숨김만·10분재생성·이전코드폐기. 실제회원쓰기/Flutter/실기기는미확인. G3는후속 |
| #13 방/통계 | 실제room/회차/신청·확정참가/주간연결미구현. [통계선행제안](../ISSUE_13_WEEKLY_STATISTICS_DRAFT.md)/8번째Backend,Flutter귀속/조회세부검토후원천→마감/집계. 개인수동체크/현재한도와통계는분리 |
| Flutter현재 | #12 13번째:시작화면뒤앱수명로그인/캐시/원정대·상세1회갱신우선,G1/G2연결은별도후속. #8 126번째실제로그화면12.936초/HTTP0캐시5.120초,개선후보확인·새Backend요청없음. 진단113/최신전체1628PASS보고와실제개선완료를구분 |
| 별도/보존 | 자동퇴역·분쟁/소유이전/방어·모든명령영속복구·WebSocket/운영배포미완료. 기존개발자료/키/flag유지·베타직전초기화별도지시. Firebase이관/삭제·새8001/백업복원이관·기본재인수없음 |

Backend완료·계약인계·Flutter적용·실기기·운영완료는서로별개다. 과거문서의당시미구현/브랜치/DB상태는현재기능상태로해석하지않는다.

G2구현/계약c06d3d2 작업브랜치push·원격확인, [#12 전체15번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6235311908). 현재Backend구간완료/Flutter연결별도·다음G3명세작업가능이다.
