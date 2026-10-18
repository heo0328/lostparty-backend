# 다음 실행

기준일2026-10-18. 기존로컬Docker/포트8000·현재개발자료/키로계속개발한다. 기본로그인/키/등록·갱신/장비인증을처음부터다시시작하지않는다. 개발DB는0016이며 공통 생성·최종 수정 시각 기록을 반영했다.

## 현재 완료·인계

- 작업브랜치 `feat/raid-services`, dev/main미병합. G1구현/계약73744be·후행문서3e07708을push했다. G2구현/게시SHA는이번최종인계/DEV_LOG를따른다. 이전 #8구간은PR#9/dev-main860c84a로통합했고완료브랜치만정리했다.
- **G1 Backend 완료/로컬반영:** 생성·검색/공개요약·내그룹/상세·멤버·이름수정/본인한도8동작. [개발안내](../ISSUE_12_GROUP_G1_DEVELOPMENT.md), [#12 12번째 Backend 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6234628340). 현재활동·현재소유/usable·가입한도/CAS,공개/회원DTO·검색/서명cursor를검사한다.
- **G2 Backend 완료/로컬반영:** [계약](../ISSUE_12_GROUP_G2_SPEC.md)·[개발/검증](../ISSUE_12_GROUP_G2_DEVELOPMENT.md), [#12 14번째 Backend 명세](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6235086630). 초대/신청·수락/승인/거절/취소·차단/해제·코드20동작. 관련190PASS/77.70초·기존API/DTO/정책불변·실행OpenAPI전체일치. 실제HTTP20동작비로그인차단/기존공개200확인. 실제개발회원쓰기·Flutter연결/실기기는미확인이다.
- 0014는새G2세테이블과현재membership부분unique다. 기존업무/그룹/한도행수를보존했고재가입은새membership UUID로과거종료행을보존한다. 데이터이관/초기화는없다. 테스트DB만중지했다.

## 우선 보완 — #8 영어 입력 이름

[#8 전체131번째 Flutter 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236509023)의 ASCII 입력 대소문자 해석을 구현·검증하고 기존 로컬 API에 반영했다. 관련241PASS/105.29초·실행OpenAPI전체일치·DB0014/전테이블행수보존을확인했다. API 원문을 신규 등록/챌린지·Armory/receipt에 전달하며 고정 대상·서버·UUID/claim은 exact다. [장비 안내](../ISSUE_8_LIVE_EQUIPMENT_PROOF_DEVELOPMENT.md)·DEV_LOG에 검증과 인계를 기록한다. [#8 전체134번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236754707)에서 사용자의 대소문자 혼합 검색 성공을 확인했다. 검색 오류는 완료이며 등록/인증 전체 재시험을 뜻하지 않는다.

구현/계약 `28ea022a70548d392d1d1a278440d78deccdfa63` 작업브랜치push·원격확인, [#8 전체132번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6236684349) 회신완료. **Backend 보완 완료 / Flutter 사용자 기기 검색 확인 완료**. 다음 우선 Backend 작업은 아래 24시간 챌린지 설계다. dev/main미병합이다.

[#8 128번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6235202558)의 이전 HTTP 오류3건은 현재 보존 컨테이너 시작 전이다. 당시 원인/서버 재시작 영향은 확정 불가하며 현재200응답만으로 클라이언트 timeout을 배제하지 않는다. 130번째 새 HTTP오류0 실측과 이후 preview503 3건은 별도다. 새 서버 계측/timeout 변경 요청은 없다. Flutter 주간 체크 조기 조회·캐릭터별 갱신 UI는 Flutter 후속이다.

## 다음 담당·순서

0. **V2 Backend 구현·로컬 반영 완료 / 게시 인계 준비:** [141번째 계약](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6237543030)·[142번째 Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245421798)·[143번째 Backend 접수](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6245466325)를 기준으로 11동작/별도proof·분쟁/선택방어·최대3건·일괄방어·선성립worker/원자이전을 구현했다. [개발 안내](../ISSUE_8_OWNERSHIP_DISPUTE_DEVELOPMENT.md), 실행 계약은 OpenAPI 원본이다. 관련194PASS·권한/그룹/주간 포함333PASS·최종가드21PASS(중복 포함). 기존 로컬DB0016/API에 최종 이미지를 반영했다. 전체회귀844PASS/과거API개수검사1FAIL을 수정후 관련58PASS·실행계약일치·공개4개200/비로그인11개401이다. 고정SHA push/Issue 인계 후 Flutter가 V2 DTO·복원·최소UI를 연결한다. 상단 안내는 기존 owner/active 조회 소비이며 새 배너 API는 없다. 실제 게임/기기/24시간 실경과 인수는 미실행이다. 현재 파티 영향 adapter가 없고 active 관계가 있으면 review_required로 보류한다.

   **날짜 기록 추가:** 사용자 요청에 따라 [DB 공통 날짜 기준](../DATABASE_RECORD_TIMESTAMPS.md)의 생성/최종수정 시각을48개 업무표에 추가한다. 기존 확인가능 날짜만 복사·미상과거는NULL·실제 변경에만 DB trigger 갱신. 조회/API계약은 불변이다. V2 종료24h/90일 자동정리는 승인되지 않아 미추가이며 이번에도 자료 삭제/기간정책/자동정리 worker는 없다. 0016을 기존 로컬DB에 적용하고48표필드/trigger·49표행수보존/실행계약을 확인했다. 세부 지문 비교 한계는DEV_LOG를 따른다. 실제삭제를 추가하려면 대상·기간·참조관계/보존조건을 별도 확정한다.
1. **Backend 작업가능:** G3명세(그룹장즉시이전·일반탈퇴·추방·조건부해산). 실제활성그룹모집의검사가없는상태를0건으로가정해해산하지않는다. #13원본연결이필요한동작만분리한다. 새구현전최신#12본문/댓글·기획정책을확인한다.
2. **Flutter 별도연결:** [#12 13번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6234990359)는G1인계접수만완료다. 우선작업은기존시작화면뒤앱수명로그인/캐시/원정대·상세1회갱신/최대대기후지속연결이다. G1/G2를초기로딩에강제추가하지않고별도승인된연결구간에서계약SHA·DTO/버전/멱등/권한/cursor소비결과를회신한다. Backend전체대기는아니다.
3. **Backend 별도설계 가능:** [#8 122번째](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6232394235)의신규발견/첫1700활동자동추가·수동제외영속계약. canonicalUUID별명시제외/재선택·첫관찰/문턱통과·이전불명확자료를보존한다. GET쓰기·과거미선택일괄재활성화는하지않는다. 기존수동저레벨/대표/순서·표시/count는유지한다.
4. **#13 후속:** 실제room membership/회차·조회/생성·신청/확정과주간원장을연결하는명세. 통계는 [별도선행안](../ISSUE_13_WEEKLY_STATISTICS_DRAFT.md)·[#13 8번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6232977464)의귀속/조회세부검토후원천→마감/집계순서다. 실제방/통계집계는아직미구현이며개인체크를통계완료근거로쓰지않는다.

## 확정 정책·남은 입력

- 그룹은앱회원단위. 그룹정원/개인가입/개인모집의계정별기본15/5/10은서버값이며현재관계로집계한다. 정확히한도는기존정상/해당증가만거부한다.
- [#12 9번째 확정](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6232797572): 개인모집초과=직접참가공개/그룹방,개인그룹초과=직접참가그룹방만,그룹자체정원초과=해당그룹모든그룹전용방제한. 기존그룹운영유지·회복권한보존·원인모두해소후정상화. 개인초과의광범위그룹상속은폐기했다. 실제방guard는#13구간이다.
- **G2 사용자 확정:** 일반그룹원직접초대유지. 그룹장만코드관리,공개ON그룹원조회/복사허용,OFF는화면숨김만/기존코드사용유효. 영문대문자+숫자6자리·재생성10분·이전코드폐기/폐기후생성우회금지. 추가G2제품질문대기는없다.
- #8 수동활동/대표는현재소유/usable만검사하고레벨하한없음. 1700은최초기본선택기준. d33f873/로컬반영·[#8 119번째 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230483893),120번째Flutter계약일치확인이다. 새자동추가정책은아직구현하지않았다.
- [#8 126번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6234537650): 실제1회화면사용가능12.936초중HTTP0캐시5.120초/약40%. Flutter캐시중복읽기개선후보이며새Backend변경/재시험요청없음. 기존서버로그에는duration이없어DB/서버시간분리불가다. 실제속도개선완료가아니다.
- #11 개인manual true는사용자실제반영성공. 정정/다른기기·실제파티는별도미확인. i는주간점유/완료와독립된현재방관계이며완료후잔류/다음주유지를#13에서다룬다. 현재#11 DTO/완료·점유제약을임의완화하지않는다.

## 보존·별도 범위

현재캐릭터목록의권위는실제provider정상목록이다. 이름기반신원이어받기/퇴역ID부활/다른회원소유이전은하지않는다. 본인ALREADY_VERIFIED와타회원챌린지를구분하고장비확인만으로타회원소유이전을완료하지않는다. 실제1회인증성공(#8 98번째)을미확인상태로되돌리지않는다.

타회원분쟁/소유이전·24시간방어는위범위Backend구현/자동검증이며Flutter연결·실제인수는후속이다. 자동퇴역확정·모든명령의프로세스종료후영속복구는별도다. Flutter주간원장journal을전체명령완료로확대해석하지않는다. 새8001/기초재인수·Firebase자료이관/삭제·백업복원마이그레이션·운영배포는없다. 베타직전DB내용초기화는대상/영향이명시된별도사용자지시에만수행한다.

기능지도는 [AI_CONTEXT](AI_CONTEXT.md), 상세완료·검증·장애·Git/댓글이력은 [DEV_LOG](DEV_LOG.md)다.

G2구현/계약 `c06d3d2ec6663cb3412294db6a02354f3ab03e1c`를feat/raid-services에push·원격SHA일치확인후 [#12 전체15번째 Backend — G2구현인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6235311908)로회신했다. 전체14번째는명세,15번째는구현결과다. 다음Backend G3명세/보완작업가능,Flutter현재시작준비우선/G1G2별도연결후속이다. 후행문서는게시기록만변경한다.
