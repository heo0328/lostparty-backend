# 그룹 핵심 흐름·관리 구현 기록

2026-10-28 / Backend / feat/group-management. 사용자 승인 범위는 Backend 구현·격리 검증·계약 게시다. 개발 API/DB 변경·merge·배포/자료삭제는 제외한다.

## 핵심 표시·활동·집계

- DB0034_group_features는 group_activity_heads·group_subject_character_references 두 확장표와 트랜잭션 활동시각 trigger만 추가한다. 기존행/과거시각/이름참조 backfill은 없다. 기본0023·기존0033은 새표를 읽지 않으며 opt-in/새경로는 GROUP_FEATURE_NOT_READY503이다.
- reader_profile=group-display-1의 멤버/차단목록/내그룹·상세와 membership별 activity-characters, 개인/그룹장 요청집계를 구현했다. 기본shape·쓰기/ACK는 보존하고 API키·회원ID·원정대/개인설정은 공개하지 않는다.
- 일반 활동조회는 현재member/canonical UUID, 모집조회는 별도 최신alias/context/candidate token으로 연결한다. 기존 그룹OR/회원AND/회원내캐릭터OR·실제T/본인방제외는 재사용한다.
- 숫자/분석누락은null·사유이고역할별last-success와현재오류를분리한다. 보석원본을합성하지않으며 과거subject는참조없음으로보존한다. GET은readonly/provider호출없음·cursor는회원/세션/권한/자료digest에결합한다.
- 새schema0034는모집/주간/worker의명시허용목록에추가했으며미지revision은여전히거절한다. 기본앱의0023실행기준을바꾸지않았다.

## 검증 결과와 미확인

핵심 구간 검증 완료. 시험 환경은 verify_isolated.py의 고유프로젝트/tmpfs PostgreSQL·제한 LOGIN이며 개발서버 자료는 사용하지 않는다.

초회 새 표시시험은6PASS/1FAIL이었다. 실패는23개모의회원생성의로그인속도제한 간섭이며집계결과실패가아니다. 해당시험에서모의로그인한도만초기화한뒤직접/회귀검증을진행한다. 결과는아래에누적하며통과수중복합산하지않는다.

실제개발실행은기존기록sourcec1f86d8/이미지581a1a5e·DB0033이다. 이번에재조회/교체하지않았으며신규API를이미실행중이라고인계하지않는다. Flutter연결·사용자기기인수·전체성능/운영시험은미실행이다.

## 구현 묶음과 인계

핵심표시/집계는 d075def로먼저게시하고 [#12 전체24번째 Backend · 구현인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6465656746)에회신했다. 같은브랜치에서관리/레이드보존을이어구현했다. 그룹장전용레이드명령·복구승계는추가하지않는다.

### 핵심 구간 검증 결과

- 선택70개 시험에서68PASS/2FAIL 후 실패2개만 수정·재검증2PASS(15.61초). 첫8개 새표시/연결시험은모두통과했고 기존그룹관리/HTTP·모집후보를포함한70개선택의미해결실패는없다. 중복실행수를합산하지않는다.
- 계약실패는시험이미지에갱신전고정계약파일이포함된구성문제였다. 후보검색실패는현재본인참가방제외정책과충돌하는소유자관찰시험이었다. 비참가제3그룹원을관찰자로변경해실제T 필터의본래검증목적을보존했고검색정책/업무코드는완화하지않았다.
- 두계약전체객체비교PASS: 기본119경로/136동작·two-cycle181경로/202동작. 기존변경은그룹GET4경로의명시프로필·추가3조회/DTO와그룹schema metadata이며 기존쓰기/과거ACK는유지한다. 기존Starlette/AnyIO경고1개는남아있다.
- 위핵심인계시점에는관리기능시험전이었다. 이후관리구간의검증은아래를따르며 실제서버반영/Flutter기기인수는여전히미실행이다.

## 그룹 관리·실제T 레이드 보존

- management_profile=group-management-1, disband/remove/representative 쓰기와 그룹원 공통 raid-rooms 목록을 구현했다. 기존 관리GET 기본shape는 유지하고 신규기능은0034에서만 제공한다.
- 해산은현재그룹장/본인1인/실효pending없음·실제활성그룹전용방없음을검사한다. 동일원본판정을목록과공유하고미확인은count=null/unavailable·DB오류503이다. 그룹종료/코드폐기/관계/사용량/revision/활동시각/ACK를원자처리하며기존행을보존한다.
- 추방·일반탈퇴의발신초대/사용량정리를공유하고원ACK/재가입새UUID를보호한다. 그룹대표는그룹장본인의유효활동캐릭터만선택하고개인대표/그룹이름은바꾸지않는다. noop은활동시각/revision을올리지않는다.
- 그룹역할은레이드개설특권/공대장권한을만들지않는다. 일반그룹원도같은조건으로개설하고각실제T레이드공대장이기존명령을사용한다. 그룹장전용명령경로는없다.
- 현재실제T의참가근거를확인한뒤그룹탈퇴/추방/소멸만으로기존진행/완료/탈퇴·기록을막지않도록그룹검사와retained group stamp를분리했다. 다른T신규참가·새그룹생성/범위전환에는현재그룹자격을유지하며 독립소유/활동/회원/한도제한을보존한다.
- detail/plan의include_group_state=true에서만root.group_state를추가한다. 기존readonly/과거anchor검사를재사용하고그룹명/식별자와active/ended/unavailable을보존한다. 미지query/중복query는거절하며 기본응답·원ACK는그대로다.
- 코드가입으로subject 표시캐릭터가바뀌는경우도canonical참조/세대를함께갱신해이전캐릭터스펙과혼합하지않는다. 과거subject이름backfill은없다.

## 관리 구간 검증

- 최종 선택86PASS/194.41초: 신규관리10·레이드생명주기5, 기존그룹관리/HTTP·G2를함께실행했다. 권한·동시해산/신청·동시이전/추방·ACK실패rollback/재가입·대표noop·DB오류/미지schema·기본0023호환·0034 API/worker readiness·공개전환→그룹해산→기존레이드보존을확인했다.
- 별도직접영향 회귀41개(재신청/실제T관리)는통과했다. 그선택묶음에서신규생명주기2건은시험보조함수의date=str 바인딩오류로실패했고date변환정정뒤생명주기4건/추가확장5건모두통과했다. 반복수를합산하지않는다.
- 최종두계약객체전체일치PASS: 기본123경로/140동작·two-cycle185경로/206동작. 이전기존component schema의값변경/삭제는0이며 프로필/명시query·추가7조회/관리동작·새DTO만반영했다. JSONkey순서는기존기준에맞췄으며계약비교는전체값을검사한다.
- 문서/JSON예시·diff/의존성lock검사통과, 격리실행기호스트12시험PASS. 호스트시험의의도적실패/cleanup모의출력은실제컨테이너실패가아니다. 기존AnyIO경고1개는유지한다.

## 완료 경계와 다음 담당

이번승인범위인Backend구현·격리검증·고정계약게시까지마감한다. 개발서버는기존sourcec1f86d8/이미지581a1a5e·DB0033기록을유지하며이번작업에서조회/교체하지않았다. 따라서원격소스가게시돼도현재서버의신규API는미반영이다.

다음Flutter는고정DTO소비/보석snapshot·integrity labels의구체차이를대조한다. 실회원/기기시험은개발반영후별도로진행한다. Backend는그차이에대응하고실제개발반영이요청되면대상/보존/이행범위를별도구간으로잡는다. G-RECOVERY·활동자동추가·운영정리/웹소켓·통계는별도미완료이며이번에완료로바꾸지않는다. main/dev통합·배포·자료삭제/초기화·새환경/복원리허설은없다.

최종 원본검토에서 generation 자체의 review와 실제 item/round 연결도 unavailable로 처리하도록 보강하고 해당 차단집합·정상 공개전환/해산의 2건만 재검증해2PASS/38.45초했다. 문서에 나열한 전체 시험범위의 중복제거 노드는152개이며, 동일HEAD 일괄재실행이라는 의미가 아니다. [검증 집계/노드 목록](verification-2026-10-28.json)에 각 실행과 미실행을 구분했다.

최종게시source는 `22b1620747707afaa87ba84223e5a2beb886f658` / feat/group-management이며 push·원격확인후 [#12 전체25 Backend](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6466328231)·[#16 전체14 Backend](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6466327755)에인계했다. 이후문서마감커밋은업무코드/두계약을변경하지않는다.


## 2026-10-29 — Native 소비 확인·개발환경 반영 준비

[#12 전체26번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6488471404)는 현재 analysis/issues로 보석·아크그리드 오류를 매핑할 수 있고 구 gemValidationSnapshot/count 복제나 추가 API가 필요 없음을 확인했다. warning을 error로 올리지 않고 unavailable/unknown을 정상으로 합성하지 않는다. 역할별 현재 분석과 마지막 성공 전투력을 분리한다. 새 계약 차단 사항은 없으며 실제 카드 어댑터·역할별 소비는 Flutter 구현/기기 검증으로 남는다. 과거 Firebase 구조의 재현은 완료 조건이 아니다.

[#16 전체15번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6488471756)의 요청은 아래 **반영 준비 범위 정리**다. 실제 서버/DB 변경·merge·운영배포·초기화/삭제는 실행하지 않는다. 이미 수행한 격리시험 전체나 빈환경/구자료 import·복원 리허설을 추가 선행조건으로 삼지 않는다.

### 적용 대상과 호환 조합

- 대상은 기존 개발 Compose 프로젝트의 기존 PostgreSQL과 two-cycle API다. 기존 계정·소유/활동·그룹·모집 C/N·과거 기록·pending/ACK 및 설정/키/볼륨을 보존한다. 새 DB/환경이나 구자료 이전을 만들지 않는다.
- 업무 소스는 고정 `22b1620747707afaa87ba84223e5a2beb886f658`의 전체 변경이다. 그룹 파일만 옮기지 않고 migration·공유 모집/주간/schema 허용 목록·worker·두 계약을 같은 소스 이미지로 반영한다. 후행 문서 커밋은 업무 소스를 바꾸지 않는다.
- DB 목표는 `0034_group_features`다. two-cycle factory/readiness·주간·실제T worker는0034를 지원하며 기본 앱의 실행 기준은0023으로 유지한다. 실제0034 DB에서 기본 앱으로 전환하지 않는다. 앱 내부 worker들도 같은 후보 이미지에서 실행한다.
- 마지막 실행 기록은 sourcec1f86d8/이미지581a1a5e·DB0033이며 이번 준비에서는 실행 컨테이너/DB를 재조회하지 않았다. 실제 적용 직전에 읽기 전용으로 재확인하며 기록과 다르면 새 기준과 차이를 먼저 확인한다.

### 실제 반영이 별도 지시된 후 실행할 순서

1. 현재 API/DB 컨테이너·이미지 ID/소스 label·실행 factory·health·alembic_version을 확인한다. 환경/키/볼륨/포트/보안 설정은 공개하지 않는 보존 비교값만 기록한다. 기존 계정/그룹·모집·ACK 등 업무 테이블과 sequence의 보존 비교 기준을 확보한다. 자격증명·개인 원본 응답은 Issue에 게시하지 않는다.
2. 기존 설정을 유지해 후보 전체 소스 이미지를 준비하고 소스/의존성 및 기본123경로/140동작·two-cycle185/206의 OpenAPI 전체 객체 일치를 확인한다. 기존 격리 검증은 재사용하고 새 차이나 실패가 있을 때만 해당 경계를 추가 검증한다.
3. 쓰기 경쟁 방지를 위해 기존 API와 그 내부 worker를 함께 중지한다. 기존 DB는 유지하고0033을 확인한 후0034만 트랜잭션 적용한다. 두 확장표·함수/trigger·FK와 실제 앱 역할의 필요한 접근 권한을 확인한다. 과거시각/이름참조 backfill이나 업무행 수정은 없다. DDL 전후 기존 업무행/sequence가 같은지 쓰기 중지 구간에서 비교한다.
4. 같은 기존 DB/설정/키를 사용하는 후보 two-cycle API를 시작한다. API readiness와 모집/주간의0034 조회·worker 실행 성공 및 오류 로그를 확인한다. 기존0023 전용 앱으로 시작하지 않는다.
5. 실제 실행 이미지의 소스/두 생성계약 전체와 health를 확인한다. 기존 로그인/계정·모집 C/N/기록의 허용된 읽기, 신규 그룹 조회·관리 프로필·집계·활동/방목록을 현재 자격 범위에서 확인한다. GET 쓰기/provider 호출 없음과 기존 상세/기록 접근을 대조한다. 실회원 가입/추방/해산 등 상태 변경 시험을 임의 실행하지 않는다. 정상회원 읽기를 확보하지 못한 항목은 미확인으로 남기고 무인증401만으로 기능 통과를 선언하지 않는다.
6. #12/#16에 실제 실행 source SHA·이미지 digest·DB revision·두 계약 비교·API/worker 상태·자료/설정 보존·실행한 확인/미확인을 인계한다. 그 뒤 Flutter가 실제 개발서버 연결 및 기기에서 핵심/관리 흐름을 검증한다. Backend는 확인된 차이에 대응하고 merge/운영배포는 별도 구간으로 유지한다.

### 실패 경계와 완료 조건

0034 DDL이 실패해0033으로 롤백된 경우에만 실제0033 호환성을 확인한 기존 이미지를 재시작할 수 있다.0034 커밋 이후에는 기존0033 전용 이미지로 되돌리지 않으며 DB/업무자료를 유지한 전진 수정으로 대응한다. migration downgrade는 지원하지 않는다. 실패 시 새 기능 연결을 완료로 알리지 않는다.

준비 완료는 대상·조합·순서·보존 확인·인계 항목이 정리된 상태다. **현재는 준비만 완료했고 개발환경 반영은 미실행**이다. 다음 Backend 작업은 별도로 지시된 개발반영 구간이며, Flutter는 어댑터/화면 연결을 진행하되 실제 신규 API 인수는 반영 후 수행한다. G-RECOVERY/활동자동추가는 계속 별도 미결정이다.


## 2026-10-29 — 기존 개발환경 반영·실행 검증 완료

사용자가 준비 계획의 실제 실행을 승인했다. 개발환경은 **source `cf214d016fc650e216782432f9c9c33823367808` / 이미지 `sha256:eecda79d926fef610cd01910cf2d6c94b07201b80a21603a1dd4a176e1a13463` / DB `0034_group_features`**로 반영했다. 업무 구현·두 계약은22b1620과 동일하다. [공개 실행 집계](../../engineering/operations/records/group-features-rollout.json)에 실제 실행 근거와 미확인을 구분한다. 위 준비단계의 미반영 기록은 당시 이력이다.

- 중지된 Docker Desktop을 시작한 뒤 기존API c1f86d8/581a1a5e·DB0033을 확인했다. 이미지 기본환경과 기존컨테이너의 PYTHON_VERSION 표시가 달랐으나 실제 실행은 양쪽3.12.16이었다. 기존 immutable runtime 이미지를 재사용해 기존 app/alembic 디렉터리를 교체한 전체소스 후보를 만들고 기존 환경값도 그대로 유지했다. 최초 일반Dockerfile 후보는 실행환경 차이검사에서 제외했고 실제 반영하지 않았다. 추후 기본이미지 갱신은 별도 판단이다.
- API/내부worker를 함께 중지한 구간에서0034만 트랜잭션 적용했다. 기존112개 업무표1,857행의 모든 행/열정의/기록시각 hash와 sequence가 동일하고 신규 두표는0행이었다. FK·앱역할 권한·활동trigger7개와 two-cycle/group/worker readiness를 확인했다. 과거시각/이름참조 backfill·자료이전/삭제는 없다.
- DB컨테이너/이미지/볼륨/환경과 API환경 전체·명령/사용자·포트·보안·로그·readonly키mount/키내용/.env를 보존했다. 민감 원문과 상세 비교근거는 gitignore backups에만 보관한다. 임시 reader는 제거했고 API/DB는 healthy다.
- 실제 실행소스272파일 일치·고정runtime31·두생성계약 전체일치PASS: 기본123경로/140동작·two-cycle185/206. health/공개주차 HTTP200 2건, 신규그룹12경로의 missing/invalid Bearer401 24건을 확인했다. 보호응답 ACCESS_INVALID/no-store/Bearer는 모두 일치한다. health에는 기존 공개헤더 동작을 유지했다.
- 실제 유효세션2명의 계정bootstrap/등록·사용한도·개인요청집계·내그룹기본/표시·주간summary와 C/N현재/역사목록을 READ ONLY로 조회했다. 현재참가항목5건의 상세/계획/명시group_state도 확인했다. SQL7,596문장은 SELECT/SET/SHOW만 허용했고 provider 호출0이었다. 정상회원 HTTP나 명령 성공을 뜻하지 않는다.
- 유효세션 회원의 현재가입그룹이 없어 멤버/활동/차단/관리/그룹방목록의 실자료 성공조회는 미확인이다. 새 그룹/가입자료를 만들거나 실회원 추방/해산으로 검증하지 않았다. 이 경계의 기존 격리검증을 재사용하고 사용자 기기 인수는 Flutter와 별도로 진행한다.
- 최종 관찰로그603줄 중ERROR0, worker ownership_settlement210/recruitment200/auth_cleanup35건 모두 success·failed_items0이다. 수치는 이 관찰구간뿐이며 이전 격리시험수와 합산하지 않는다. 읽기검증 보조스크립트의 테스트전용 httpx import 및 health no-store 가정은 보조코드만 정정했고 업무코드/API계약은 변경하지 않았다.
- 사용한도 때문에 반영 후 인계 전 중단됐으며 재개시 실행이미지·DB0034·API/DB healthy와 저장된 읽기검증 결과를 확인해 migration/교체를 반복하지 않았다.

Native 신규 [#12 전체27번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6488900145)·[#16 전체17번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6488900495)는 그룹 Router/DI/화면·명령/CAS/원ACK·표시/관리/모집연결 구현과 Flutter전체2691PASS(직접12포함)·lib/test분석지적0을 자체보고했다. Backend시험에 합산하지 않으며 실제 서버연동/기기/Penpot대조는 미완료다. 추가API 수정요청은 없다.

다음 Flutter/사용자는 기존 개발서버에서 초대/가입→활동캐릭터→모집필터→상세/참가 및 관리흐름을 정상UI로 확인하고 차이가 있는 항목만 #12/#16에 회신한다. Backend는 직접차이에 대응한다. G-RECOVERY/활동자동추가·main/dev병합·운영배포·초기화/삭제는 실행하지 않았다. 실행검증/계약게시와 실제기기인수를 구분하고 양Issue는 OPEN으로 유지한다.
