# Issue53 — 개인 예약 조회 구현 결과

합의는 [설계](my-account-reservations-design.md)·[Issue53](https://github.com/heo0328/lostparty-backend/issues/53), 실행 계약은 [OpenAPI](../../../../openapi/openapi.yaml)를 따른다.

## 구현

GET `/v2/me/raid-reservations`를 현재 앱에 추가했다. 기존 overlaps·기존 component/path 값·legacy 계약은 유지했다. DB migration/신규 원장·worker/키 생성은 없다. 캐릭터 visible/count의 기존 writer도 변경하지 않는다.

calendar_week_key/limit/cursor와 닫힌 응답, KST 수00시 창/게임 수06시 분리, 본인 미해제 원장 조회를 구현했다. bulk outer join·필수 참조 검사, snapshot character_name→name·nullable, 전체 결과지문·keyset/HMAC/최초600초 만료,10000/10001 sentinel·1MiB page guard를 포함한다. 관측시각/게임06시 변화만으로 stale이 되지 않는다. 현재 소유/activity/review/종료enum만으로 원장을 제외하지 않는다.

매 요청의 구조 introspection을 피하고 기존 현재 앱의 시작 시 전체 readiness와 요청별 지원schema head 검증을 사용한다. 읽기는 RR/READ ONLY다. 원장/표시 투영에 사용하지 않는 build 등 ORM 열을 가져오지 않는다.

## 검증·한계

- 최종 선택19PASS(137.75초): 신규16/기존schedule HTTP3. 추가 동시 쓰기snapshot1PASS(26.96초)는 기존normal 사례 강화이며 고유20건으로 합산하지 않는다.
- 실제 별도 트랜잭션이 projection 읽기 중 Assignment 표시를 바꾸어도 같은snapshot은 기존결과, 다음요청은 새지문인 것을 확인했다.
- 0/1/100/200/201행·전체페이지집합, 타회원/cursor/limit·변경후 stale, nullable/타입/길이, 정상해산 후 해제, 종료enum만으로 미해제 누락 금지, UTC/수00/06,10000/10001·byte guard를 확인했다. 초기 시험의 시각helper/복제대상주/해산해제범위 기대를 수정하고 재검증했다. 실패를 업무요건 변경으로 숨기지 않았다.
- current/legacy OpenAPI 전체 객체 비교PASS, 기존path/component 값 차이 없음. 신규1경로만 추가했다. 문서분류/상대링크·동결자료/diff 검사PASS.
- 합성10000행에서 추적기 없는 단일요청1.926초,200행page116731bytes. 추적기 사용 복수읽기11.322초/Python 할당 peak128607848bytes. EXPLAIN 실행109.590ms/계획0.855ms. 서로 다른 측정값이며 운영·동시부하/cold cache 보장이 아니다. 요청당 원장projection은1SQL이고 예약 수에 비례하는 추가 SQL이 없다. 전체결과지문의 O(N) 비용은 page마다 남는다.

## 로컬 반영·인계

[반영/계측 원본](../../../engineering/operations/records/personal-reservations-local-rollout.json)에 image/source hash와 보존 검사를 남겼다. API만 교체해 DB container/환경/port/mount/기존키 hash를 유지했다. health200/미인증예약401·현재생성계약 일치·app Python292파일 hash 일치를 확인했다. 운영 변경/실회원쓰기/새로그인 시험은 없다. 기존 키·환경의 유효 사본과 로컬 DB dump 제외 방침을 유지했다.

인증 기능 검증은 격리 DB/HTTP이며 실제 dev 회원 화면/Native 소비 성공과 구분한다. 다음 Native는 게시 고정SHA/OpenAPI와 실행 버전으로 신규 DTO/페이지/영역오류·기존 availability/원pending을 검증한다. Penpot/시안승인·기기확인도 별도 단계다. 운영 배포는 추가 개발 후 별도 지시다.

사용자 지시의 commit/push 대상이며 dev/main merge·Issue 종료는 포함하지 않는다. 실제 고정SHA는 Issue53 구현 인계 댓글에 기록한다.
