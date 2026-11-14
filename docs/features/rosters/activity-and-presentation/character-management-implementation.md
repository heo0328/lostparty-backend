# Issue53 — v2 관리 원자 저장 구현

[합의 계약/예시](character-management-contract/README.md)를 구현했다. 현재 앱 전용 GET/PUT `/v2/me/game-accounts/{registration_id}/character-settings`, 기존 v1·개별 preferences·대표·예약 API와 legacy 계약은 보존한다.

## 구현 책임

- management_schemas: 닫힌 Context/PutBody, canonical UUID·정규decimal·버전/지문/목록상한·순서 생략/null/빈배열 구분.
- character_profiles.management: RR/READ ONLY 문맥 GET, 현재 소유/복구잔여 집합, bulk preferences/NameClaim, rank/정확decimal/UTF-16/UUID 정렬·전체정렬입력 지문.
- PUT: 기존 game lock·멱등 reserve/commit_result 재사용. settings/registration/ownership/roster CAS와 order_digest 재검사, 활동/대표/선택적 드롭·settings version·preferences 변경version과 원ACK를 한 트랜잭션으로 저장한다. role/visible 현재값 보존, 의미동일/동일드롭은 no-op, 첫 명시초기설정만 configured로 전환한다. 신규 namespace는 character-management-1이다.
- query/중복JSON·본문크기·표준오류/no-store를 HTTP 경계에 적용한다. 오류발생은 전체rollback·ticket 재시도 상태이며 per-item 부분성공은 없다. GET/PUT 현재 명세만 확장하고 legacy 및 기존path/component 값은 보존한다.

## 검증 범위

실제 임시 PostgreSQL과 HTTP에서 일반GET·no-op·ON/대표변경의 rank 불변·활동subset 드롭·옛ACK재생/현재GET·key/body충돌·stale·이전preferences 직접변경 감지·role/visible 보존을 검사했다. 초기/재설정/이후불완전 configured와 문맥밖퇴역대표를 허용하는 GET, PUT의유효최종선택, Configuration행이없는첫명시저장, 실제동시두명령의1성공/1충돌과ACK실패시모든변경rollback을 검증했다.

정렬fixture·고정밀decimal·지수0·null/비수치/비유한/비ASCII,1000/1001 문맥·활동200/201·원자순서199 경계를 포함한다. 최종 신규26/기존대표35=61PASS(33.76초), 문서Schema/예시/비교40사례PASS. 전체선택 회귀 수치와 실제실행/계측은 [반영 기록](../../../engineering/operations/records/character-management-local-rollout.json)에 연결한다. 최초시험의 saved_at/confirmed_at fixture 누락2건은 고쳐 재실행했으며 기존데이터삭제나정책완화로실패를숨기지않았다.

추가1,000명 합성GET 계측은 13SQL/약42ms/216488bytes였다. 단일실행·warm 격리조건이며 운영·coldcache·동시부하보장이 아니다. 개인별N+1 대신 bulk lookup을 사용한다. API 사용자전수/모든운영자료조합·Native실제화면은 미확인이다.

## 실행·게시 경계

로컬 dev는 API만 교체하고 DB container/환경/포트/mount/기존키hash를 보존한다. 신규키/DB migration/유저초기화·실회원설정쓰기·운영배포는 하지 않는다. DB초기화가 필요해져도사용자사전확인필수다. 기존사본을 재사용하고 로컬 DB dump 제외방침을 유지한다. 인증기능 검증은 격리 DB/HTTP이고 실제dev health/미인증401·생성명세/앱manifest 확인과 구분한다.

이번 구현 지시는 commit/push/merge 승인이 아니다. **신규 관리 코드·최종계약/예시는 미커밋·미push**이며 기존게시 dd69159에는 포함되지 않는다. 고정SHA를사용하는Native인계는사용자게시지시후진행한다. 기존 게시 예약GET 지원과도구분한다. 신규 OpenAPI는로컬 실행명세이며미게시파일링크로원격소비가능하다고안내하지않는다.

## 사용자 승인 고정 게시

업무/정확계약 026a74fa67c36d72fb9d6d94d8bafcf707d4ffe9를 feat/my-account-contracts에 commit/push하고원격직접SHA동일·clean을확인했다. [전체20 Backend 고정인계](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6861435507)가현재게시기준이며위의미게시표기는게시전상태다. 앱/API/실행image는기존검증/로컬반영과동일하고게시만으로재배포하지않는다. 다음Native 승인범위연동검증·구체차이대응,dev/main merge·운영배포·초기화없음.
