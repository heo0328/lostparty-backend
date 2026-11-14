# Issue53 — 정책2 구현 계획

2026-11-14 / 작업 구간: main-only 계정대표·자동 선정과 관리 계약 전환 / 브랜치: feat/my-account-contracts.

[전체29 Backend 정확 계약](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6873152385)을 [전체30 Native](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6873213572)가 수용했다. [Schema·전이·fixture](character-management-contract/policy2/README.md)가 구현 기준이다. 이번 문서는 구현 기획이며 코드/OpenAPI/실행 서버를 변경하지 않는다. 추가 제품 결정은 없다.

## 목적과 보존 흐름

계정대표는 메인 원정대의 활동·현재 소유·usable 캐릭터 한 명으로 통일한다. 대표가 없으면 레벨 DESC → 전투력 DESC(null 뒤) → 이름 UTF-16 ASC → UUID ASC로 자동 선정한다. 유효한 기존 대표는 유지하고 메인 전환에서도 별도 대표 선택 요청 없이 한 명령으로 확정한다. 후보가 없으면 실제 예외 상태로 남기고 비활동 캐릭터를 자동 활성화하지 않는다.

부원정대는 대표를 표시/선정하지 않고 활동 전체를 순서 변경할 수 있다. 수동 rank·role/visible·그룹 snapshot·원 pending/ACK는 보존한다. 내 계정 진입/관리 복귀 시 서버 저장 설정 재조회는 Native 담당이며 기존 API를 사용한다. 새 endpoint/provider refresh·주기 polling은 추가하지 않는다.

## 변경 책임과 구현 순서

| 순서 | 책임·주요 경로 | 완료 기준 |
|---|---|---|
| 1 | character_profiles의 공통 후보/관측·대표 정책 | GET projection과 쓰기 결정을 분리. 정규 숫자/실제 observed_at, bulk ScopedPowerCache 조회, 기존 유효 대표 유지·메인 전환 raw 무시·후보 없음 결정을 한 기준으로 제공 |
| 2 | common/support.py와 management의 복구 진입 | 기존 character-management-1 영속 namespace 유지. 정책1 복구 전용 조회를 reserve의 만료 lease 인계보다 먼저 처리. 새 정책 요청과 옛 원문을 구분 |
| 3 | management.py·schemas/management_schemas.py·api/management_router.py | 정책2 필수 policy_version/is_main, nullable 대표·부원정대 전체 movable, CAS/지문·선택/순서 원자 저장. GET 정책2, PUT 정책2 성공 또는 역사적 정책1 ACK |
| 4 | rosters/service.py·lifecycle.py 및 대표 전용 writer | 메인 PATCH/register·confirm/refresh·v1 settings 등 실제 명령의 업무 저장 후 ACK 구성 전에 대표 확정. 버전 중복 증가 방지 |
| 5 | representative.py·service의 settings/reg_out·bootstrap.py·lifecycle_reads.py | 같은 스냅샷의 main-only 유효 대표 projection. 부원정대/null·잘못된 raw 노출 차단, GET 무쓰기·잔여 activity 복구 보존 |
| 6 | 현재 OpenAPI·격리 시험·로컬 API | 정확 Schema 대조, 회귀/경계 검증 후 기존 DB/키/환경을 보존한 API 교체와 실행 계약 확인 |

파일 종류별 새 브랜치는 만들지 않는다. 기능별 정식 모듈 경로를 사용하고 전면 이동/일괄 리팩토링은 하지 않는다. 숫자 정규화·공통 관측/후보 코드는 management와 대표 정책에서 재사용하되 HTTP DTO나 DB 모델 정의를 업무 모듈에 새로 섞지 않는다.

## 트랜잭션과 호환 경계

- 외부 provider 관측은 기존처럼 쓰기 lock 밖에서 수행한다. 자동 선정은 저장된 관측만 사용하며 game-mutations-v1 lock과 같은 DB transaction 안에서 현재 권한·최종 활동/대표·버전·ACK를 확정한다.
- 하나의 명령에서 activity/대표/state/rank 변경을 먼저 모아 Configuration.version을 한 번만 올린다. 기존 reconcile과 retire의 증가 지점도 확인해 이중 증가를 막는다. 등록 version의 기존 CAS/demote 규칙은 유지한다. ACK 실패는 업무 변경까지 rollback한다.
- main 전환 시 새 메인의 과거 raw를 유효 대표로 승격하지 않고 후보를 다시 비교한다. 이미 메인인 등록의 반복 PATCH는 유효 대표를 유지한다. 최초 활동 미설정은 unconfigured/null, 후보 상실은 활동을 보존한 복구 상태로 처리한다.
- order_digest에는 정책/메인·등록/소유 문맥과 정규 관측·시각/자격을 포함한다. 대표 자동 선정에 전투력을 쓰더라도 카드 기본 순서는 기존 rank→레벨→이름→UUID다. 관측 변경 후 옛 드롭은409이며 자동 재적용하지 않는다.
- 정책1 DTO와 원 ACK 읽기를 보존한다. 키와 본문이 같은 성공은24시간 내 원응답, 초과는 IDEMPOTENCY_EXPIRED, 진행 중은 REQUEST_IN_PROGRESS다. 미완료 lease 만료/retryable/기록 없음의 옛 본문은 CONTRACT_POLICY_CHANGED로 실행하지 않는다. 동일 키의 다른 본문은 IDEMPOTENCY_CONFLICT다. 기존 기록 삭제·기한 갱신·namespace2 신규 실행은 없다.
- 정책2 필수 요청 구분자를 확인하기 전에 옛 요청을 새 DTO 기본값으로 채우지 않는다. 정책1 historical ACK는 정책1 strict reader로만 검증하며 현재 UI 상태는 정책2 GET으로 확인한다. 반환 모델 검증이 원 ACK를 정책2로 재작성하지 않도록 HTTP 경계도 검사한다.
- v1 신규 settings는 같은 main-only 정책을 적용하되 부원정대 현재 raw와 정확히 같은 원문 round-trip만 예외 수용한다. 저장 결과는 null, 임의 새 nonnull은 거절한다. 과거 성공 ACK는 보존한다.
- 공통 router/service를 legacy 앱도 사용하므로 현재 앱의 정책 적용을 명시적으로 구분한다. 앱별 설정/요청 진입에서 결정한 정책을 서비스 경계로 전달하고 클라이언트 입력으로 선택하지 않는다. 전역 가변 플래그·DB 단계 추정으로 앱을 전환하지 않는다. current/legacy 앱 동시 생성 순서에 영향이 없어야 하며 DB0023 시험용 앱이 새 테이블을 조회하지 않게 한다. 이 분리가 구현 전 첫 확인 항목이다.

DB migration·새 대표 저장소·일괄 자료 정리는 계획하지 않는다. 기존 DB 모델로 충족하지 못하는 문제가 나오면 구현 근거를 확인하고 계약 영향이 있는 변경만 다시 협의한다.

## 검증 계획

문서59사례와 Native의 정적 비교는 구현 검증으로 계산하지 않는다. 다음 시험은 합성 데이터의 격리 PostgreSQL/HTTP에서 수행한다.

| 경계 | 검증할 동작 |
|---|---|
| 자동 선정·관측 | 레벨 미세 소수/동률·power null/동시각·UTF-16 혼합 이름/최종 UUID, 오래된 성공값 유지, 다른 회원/preview/lifecycle/역할 분석 제외. 후보 없음·유효 대표 유지·raw 승격 금지 |
| 관리 저장 | 최초 설정/부원정대 raw 정리/메인 null 자동 선정+순서 원자성. 활동0/1/200/201, 문맥1000/1001, 메인 movable199·부원정대200, 생략/빈배열/null/중복, no-op·비활동 상대 순서·role/visible 보존 |
| 명령·reader | 메인 전환/반복 PATCH, register/confirm/refresh의 대표/버전·ACK. 대표 무효화/후보 상실 복구. 대표 GET/등록/settings/bootstrap/lifecycle의 같은 main-only 결과, GET 무쓰기, 기존 그룹 snapshot 보존 |
| 충돌·복구 | 동시 메인 전환/관리 쓰기, 관측 power만 바뀐 지문, 소유권/세션 경계, ACK 저장 실패 전체 rollback. 정책1 성공/만료/실행 중/lease 만료/retryable/미도달, 정책2와 같은 key 충돌, 동일 요청 경합 |
| 계약·구 앱 | 정책2 Schema와 실제 전체 객체/오류 일치. PUT 역사적 ACK와 새 응답의 분리. 현재 명세는 합의 diff만, legacy 명세 전체 객체·DB0023 시험 보존. 기존 예약/그룹·대표 관련 회귀 |

전투력 조회가 카드 수에 비례해 SQL을 추가하지 않는지 확인한다. 전후 동일 합성 문맥의 SQL 수/응답 크기/처리시간을 기록하며 운영 성능으로 일반화하지 않는다. 변경에 맞는 선택 검증부터 진행하고 실패·공통 코드 영향이 있는 범위로 확장한다.

## 로컬 반영·인계

구현 검증 후 로컬 Docker/API 상태를 확인하고 API만 교체한다. DB 컨테이너/볼륨·schema·키·환경·포트·mount는 보존한다. 기존 키/환경 유효 사본은 [백업 원장](../../../engineering/operations/backup-and-recovery.md)을 재사용하고 새 키나 dump를 요구하지 않는다. 반영 전후 이미지 식별자·생성 OpenAPI·health/인증 경계와 비민감 보존 근거를 기록한다. 실제 회원 설정을 임의로 쓰거나 초기화해서 성공을 만들지 않는다.

실패 시 같은 DB에 호환되는 직전 이미지/명령으로 API를 복귀한다. 다만 정책2가 이미 성공한 뒤에는 구 policy1 writer가 정책2 멱등 결과를 오해할 수 있으므로 쓰기를 중지하고 복구 호환성을 먼저 검사한다. 정책2 journal/ACK를 삭제하거나 downgrade 원문으로 바꾸지 않는다. 재기동/rollback만으로 정책2 소비를 지원한다고 인계하지 않는다.

구현 완료 회신은 테스트·로컬 실행·Native 기기 확인·Git 게시를 구분한다. commit/push 직접 지시 후 원격 SHA/Schema/OpenAPI와 로컬 실행 버전을 연결해 Native가 정책2 연결/서버 저장값 재조회를 검증할 수 있게 한다. 운영 배포·merge·이슈 종료는 별도다. DB초기화는 필요 없으며 모든 환경에서 사전 사용자 확인 없이는 실행하지 않는다.

완료 조건은 합의한 정책2 구현·격리 검증과 로컬 지원 근거, 소비 가능한 게시 시점/담당의 명확한 인계다. 현재는 이 계획과 기존 계약 문서만 준비한 상태다.
