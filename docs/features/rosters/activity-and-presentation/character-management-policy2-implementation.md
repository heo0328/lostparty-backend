# Issue53 — 정책2 구현·검증·로컬 반영

[전체29 Backend 계약](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6873152385)과 [전체30 Native 수용](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6873213572)을 [계획](character-management-policy2-plan.md)에 따라 구현했다. 같은 feat/my-account-contracts 구간이며 **미커밋·미push/고정 구현 SHA 없음**이다. 원격 게시026a74f는 정책1이고 이번 변경을 포함하지 않는다.

## 구현

- account_representative는 정규 decimal·저장 관측의 power/실제 시각·후보/동률 비교, 유효 대표 projection과 쓰기 repair를 담당한다. cache는 bulk 조회하고 preview/타회원·다른 lifecycle을 제외한다. 기존 유효 대표를 유지하며 메인 전환은 부원정대 raw 승격 없이 후보를 다시 선정한다. GET은 쓰지 않는다.
- 현재 앱의 요청별 ContextVar를 설정/복원해 공유 v1 writer와 reader에만 정책2를 적용한다. legacy 앱은 정책1 이전 의미를 유지한다. 앱 생성 순서·전역 가변 설정/클라이언트 정책 자기주장에 의존하지 않는다. bootstrap은 이미 batch-load한 eligible/activity projection을 재사용한다.
- 같은 v2 관리 경로는 필수 policy_version=character-management-2·scope.is_main, nullable 대표·자동 선정/명시 선택, 메인199/부원정대200 movable을 지원한다. 기존 대표 OFF 금지·role/visible·비활동 상대 순서와 동일 드롭 no-op을 보존한다. 권한/CAS·지문을 다시 검사해 선택/대표/순서·버전·ACK를 원자 저장한다.
- 메인 PATCH/register/confirm·관측 reconcile/retire와 기존 v1 settings에 정책을 연결했다. 대표·state 복구와 원 ACK는 같은 게임 쓰기 lock/transaction 안에서 확정한다. retire는 기존 변경과 repair의 버전 증가를 한 번으로 합친다. 그룹 snapshot은 갱신하지 않는다.
- 기존 character-management-1 영속 멱등 namespace를 유지한다. policy1 본문은 복구 전용이며 원 성공 ACK/진행/만료만 조회하고 lease 만료·retryable·미도달은 CONTRACT_POLICY_CHANGED로 실행하지 않는다. 같은 key 다른 본문은 충돌이다. 정책1 ACK strict DTO를 보존하고 신규 관리 GET/성공은 정책2 DTO다. 현재 OpenAPI의 PUT 성공은 oneOf로 구분한다.

## 검증과 한계

격리 PostgreSQL/HTTP에서 관련9파일 **219 PASS / 169.23초**, 추가 null 자동 선정+순서 원자 저장1 PASS / 5.59초로 최종 고유220 PASS다. 선행61/83 PASS는 겹치는 확인이므로 합산하지 않는다. 기존 관리26 사례는 정책2 Schema/요청 구분자·무효 대표 null projection에 맞춰 소비 검증을 갱신했고 legacy 대표·계정·bootstrap·소유/관측·lifecycle 기대값은 보존했다.

메인 전환 원자 대표/등록·설정 버전/원ACK, 후보 없음·유효 대표 유지·부원정대 raw 제거·200 movable, 현재/legacy 앱 분리, 같은 스냅샷 bootstrap, 정책1 원문 복구의 성공/진행/만료/미도달 및 namespace 충돌을 검증했다. 기존 관리의 실제 동시2요청/CAS·ACK rollback과 추가 메인 전환 ACK 실패의 양 원정대 rollback, power만 바뀐 지문, 마지막 성공/동시각 cache tie·다른 lifecycle 제외도 포함한다. 실제 dev 회원 설정 쓰기나 Native UI 인수는 하지 않았다.

시험 대상 파일명을 처음 test_lifecycle.py로 잘못 지정한 실행은 검사 단계에서 거절되어 시험을 시작하지 않았다. 정식 test_character_lifecycle.py 등 관련 파일로 고쳐 최종 검증했다. 새 문서 검증도구의 변수 shadowing과 bootstrap의 메모리 projection 인터페이스는 최종 검증 전에 바로잡았다. 실패를 자료 삭제나 계약 완화로 우회하지 않았다.

문서 정책2 59/정책1 40 사례 PASS. 생성 현재/legacy 명세 전체 객체 일치, legacy 명세 불변 및 관리 단일 경로/Management 관련 component만 계약 diff를 확인했다. JSON key 순서 차이는 기존 순서로 보존해 무관한 대량 diff를 제거했다. 문서·상대링크/동결자료·경로 검사/diff PASS.

1,000명 warm 합성 GET은14SQL/약48.7ms/298578bytes였다(정책1 기존 측정13SQL/42.4ms/216488bytes). 같은 종류의 단일 격리 사례이며 관측 필드 추가로 응답 크기/SQL 한 건이 늘었다. 통제된 반복 부하 비교나 운영 성능 보장은 아니다. 카드별 SQL 증가는 없다.

## 로컬 지원·게시

[반영 기록](../../../engineering/operations/records/character-management-policy2-local-rollout.json)의 새 이미지에 app Python296파일이 현재 소스와 일치한다. 실제 HTTP health200/관리401/bootstrap401·현재/legacy 생성 명세를 확인했다. DB0036·118테이블의 전후 자료 지문과 기존 DB 컨테이너/환경/포트는 동일하다. .secrets bind source의 표기만 Windows UNC에서 동일 WSL Linux 경로로 바뀌었다. 원래 UNC mount를 직전 이미지의 일회성 읽기 전용 컨테이너로 다시 열어 현재 실행의 키4개와 개별 해시가 같음을 확인했다. 키 재생성·DB migration/초기화·실회원 쓰기·운영 변경은 없다.

정책2를 지원하지 않는 기존 Native의 신규 policy1 쓰기는409 CONTRACT_POLICY_CHANGED이며 원 ACK 복구는 유지한다. Native 정책2 연결과 진입/관리복귀 시 서버 저장 설정 재조회는 다음 소비 단계다. 코드가 미게시이므로 지금 원격 고정 소스 검증을 요청하지 않는다. 다음 사용자 commit/push 직접 지시 후 고정 SHA·Schema/OpenAPI·실행 버전을 연결해 인계한다. merge·운영 배포·Issue 종료는 별도이며 DB초기화는 항상 사용자 사전 확인이 필요하다.

## 사용자 승인 게시·dev 통합

사용자 지시로 업무/정확계약 9308ce7e2fb1687f29cd378f59344dbe6fffae29를 게시하고 dev 2ca80924bbc7bda563f2b7d11a1c964e06edeca6에 이력 보존 병합·push/원격 일치를 확인했다. [전체32 Backend 고정 인계](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6873586100). app/tests/openapi는 작업 tip과 dev가 같고 로컬 image9f40ecf7…401c4의 app296파일도 게시 소스와 같다. health200 확인, 기존 고유220PASS/계약·보존 검증을 재사용했다. 완료 목적 브랜치는 정리하고 현재 checkout은 dev다. 다음 Native 정책2 연결·원 pending/ACK 복구와 진입/관리복귀 저장 설정 재조회 검증이며 실제 기기 인수·main/운영 반영은 후속이다. DB초기화·이슈종료는 실행하지 않았다. 위 미게시 문구와 반영 원장의 publication은 반영 당시 기록이며 현재 소비는 이 절의 고정 SHA를 따른다.
