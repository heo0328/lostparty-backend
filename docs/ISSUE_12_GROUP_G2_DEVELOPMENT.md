# 그룹 G2 구현·검증 안내

2026-10-17. 기준: [G2 계약/예시](ISSUE_12_GROUP_G2_SPEC.md), [#12 전체14번째 Backend 명세](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6235086630). 사용자 G2 구현 지시와 후속 코드 정책 답변을 반영했다. 기존 feat/raid-services·로컬 Docker/포트8000을 이어간다.

## 구현

- `admission_models.py`/0014: subject(회원별 누적신청·현재차단/표시), relation(초대/신청/상태/선택 snapshot), encrypted code3테이블. 그룹/subject/대상회원·발신membership의복합FK와요청종류/선택·현재pending unique를보장한다.
- 기존 membership의전체group+user unique를**현재행의부분unique**로교체했다. 현재중복은계속금지하고재가입은새membership UUID로생성해과거종료시각/표시/권한이력을덮지않는다. 기존자료삭제·복사/이관은없다.
- `admission_core.py`: 현재소유/등록/claim/usable·현재활동선택·입력revision·현재그룹장정원/대상개인가입수·활성회원을최종transaction에서검사한다. 별도1700/레이드한도/표시수검사는없다.
- `admissions.py`: 일반그룹원직접초대·본인신청/취소·수신초대수락/거절·그룹장승인/거절·차단/해제·현재권한별조회/목록·서명cursor. 정확한캐릭터명검색은현재인증소유/claim의저장자료만사용하고provider/게임키를호출하지않는다. 회원전역UUID나원정대전체/개인설정은반환하지않는다.
- 초대/신청24시간·DB논리만료/발신자membership종료·기존관계우선·신청재시도누적·코드가입시pending종료. pending은정원예약이아니며최종실패는보존한다. 권한있는회복/차단해제가끝난관계를자동부활시키지않는다.
- 그룹/회원확정·members/directory/사용량head·pending종료·성공ACK는같은game-mutations락/transaction이다. 최종시각이만료를넘으면ACK까지rollback한다. 생성·명령replay는현재session/기본접근권한을검사하며과거ACK를현재권한으로재실행하지않는다.
- `join_codes.py`: 영문대문자·숫자를각각최소1개포함한6자리코드,혼동문자0/O/1/I제외. 그룹장만생성/공개설정/재생성/폐기. 공개ON일반멤버도GET/복사,OFF는원문만숨기고기존복사코드사용은유효하다. 재생성10분·기존코드즉시폐기·폐기후재생성우회금지,기간만료없음.
- 코드원문은HMAC검색digest/AES-GCM암호문으로보관한다. URL/로그/멱등result에는원문을넣지않고입력코드는해결된code UUID로명령digest에묶는다. 생성/재생성ACK의원문은현재그룹장권한으로복호화하며GET도현재공개/멤버권한을확인한다. 코드명령의metadata ACK와현재GET은별개다.
- G1요청/응답/permissions는바꾸지않고G2별도20동작을추가했다. 실제그룹G3/방/통계는구현하지않고없는동작권한을추가하지않았다.

## 검증

최종 관련 격리 PostgreSQL/모의로그인 HTTP **190PASS / 77.70초**, 기존Starlette/AnyIO경고1개다. G2 26개와G1 HTTP/내부기초/L0/모델일치/대표/주간회귀를포함한다. 최초81PASS/14FAIL은새다중회원테스트에단일회원용fixture를재사용해첫회원UUID를재선택/메인등록중복한문제다. 실제각로그인회원UUID·고유주소fixture로분리후G2 17PASS/15.55초,경계/권한/제약검증을추가하고최종190PASS를확인했다. 중간과최종숫자는중복이므로고유수로합산하지않는다.

확인한동작: 일반멤버초대/관리거부·신청누적/충돌/취소·차단후다른캐릭터/코드우회거부·현재정원/활동재검사·마지막자리경합·발신자탈퇴논리종료·만료/마지막시각경계전체rollback·GET쓰기0/actor cursor/만료stale·비공개코드사용/공개조회·10분쿨타임/폐기+생성우회거부·이전코드무효/과거가입ACK유지·현재권한상실후replay거부·원문미보관·재가입시과거membership보존·복합FK/model일치다. fixture의탈퇴/이전상태는후속G3명령통과가아니다.

기존모든OpenAPI paths/DTO/정책객체가동일함을대조하고19새경로/20동작만추가했다. 실행OpenAPI전체일치다.

## 로컬 실행·미확인

기존로컬DB0013→0014를추가적용했고API이미지를반영했다. 기존회원/원정대/등록/캐릭터/설정/활동/주간·그룹/회원/한도/head/감사행수전후동일,신규G2세테이블0행을확인했다. 실제HTTP의새20동작401/Bearer/no-store와기존health/그룹공개/카탈로그/주차200을확인했다. 테스트DB만중지했고기존개발자료/키/flag를유지했다. **실제개발회원으로초대/가입·코드발급은실행하지않았고Flutter연결·실기기도미확인**이다.

0014는이력보존방향이며downgrade로테이블/이력을삭제하지않는다. 코드복구시이전API이미지와추가자료를유지하고필요하면전진수정migration을사용한다. DB초기화/기존Firebase·기기자료이관/삭제/백업복원·운영배포는없다.

구현/계약SHA·push/댓글결과는NEXT_WORK/DEV_LOG/최종인계댓글이기준이다. Flutter의현재시작준비작업우선을유지하고G1/G2를초기로딩에강제로추가하지않는다. 계약소비/연결은별도후속이며Backend다음은G3명세·소비충돌보완이다.
