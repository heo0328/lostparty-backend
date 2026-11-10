# 다음 실행

## 현재 — Issue47 구현 게시·실제 dev 지원 완료 / 다음 Native 연결·기기

[전체8번째 Backend 고정 구현/지원 인계](https://github.com/heo0328/lostparty-backend/issues/47#issuecomment-6763005691): 구현 `44eb4ba34844eb81801608ed5953cf3bb1ba0852`를 feat/raid-batch-completion에 커밋·push하고 원격 일치를 확인했다. 실제 로컬 API image ae6b3e0a / healthy, 앱288파일 커밋 일치·두 전체 OpenAPI 일치·HTTP8PASS다. DB0036/118테이블512행·키4개·환경/실행 설정 보존을 확인했다. [반영 기록](../engineering/operations/records/batch-completion-local-rollout.json)·[구현 원본](../features/recruitment/completion-and-records/batch-completion-implementation.md)을 따른다.

다음 Native는 게시된 고정 v3 계약과 현재 debug 로컬 서버로 DTO/ACK·기존 복구·두 확인창을 연결하고 자체 검증·실제 연동 결과를 Issue47에 기록한 뒤 사용자 기기 인수를 진행한다. 같은 계약 재수용 대기는 없다. Backend는 구체 차이에 대응한다. Native 연결/기기 인수는 미완료다. 기존 고유123PASS·도구63PASS는 격리 시험이며 실제 회원 명령/기기 또는 전체 프로젝트 회귀 완료가 아니다. merge·운영/APK·자료 삭제·Issue 종료는 하지 않았다. 반영 기록 후행 문서도 같은 브랜치에 커밋·push한다.

아래는 직전 완료 구간 기록이다.

## 현재 — 완료 기록 dev 통합·작업 브랜치 정리 완료 / 별도 배포 없음

2026-11-10 사용자 지시로 완료 문서13개를 `afd5ba21d443d85f73b98d29043eefe3583b8cd7`에 커밋·push하고, feat/character-lifecycle의 기존 개발·정리·계약/검증 이력을 dev에 이력 보존 병합했다. 병합 `aa7058c5f93ad799033116608f2b3f52931b0dfe`의 origin/dev 반영과 작업 브랜치 tip 포함·전체 tree 동일을 확인했다. 통합된 feat/character-lifecycle은 로컬·원격에서 삭제했고 현재 checkout은 **dev**다. main은3e3ddc1 그대로이며 변경하지 않았다.

이번 새 변경은 문서뿐이며 기존 업무 검증 근거를 재사용했다. 문서/동결/경로·diff 검사를 통과했고 새 서버/DB·기기 시험을 반복하지 않았다. **사용자 지시대로 별도 배포·로컬 API 교체·DB migration·환경/키 변경·태그/운영/APK 배포는 하지 않았다.** release workflow는 v* 태그/수동 실행 기준이며 이번 브랜치 push는 배포 트리거가 아니다. 통합 결과/현재 브랜치 기록은 dev의 후행 문서 커밋으로 게시한다.

이번 완료 오류·계정 복구 구간은 사용자 기기 인수와 Native5df515f 게시까지 완료다. 누락 캐릭터/부분 완료 개발 자료 준비·해당 기기 검증은 별도 미완료, 묶음 레이드 체크박스 선택/일괄 완료는 기록만 된 미구현 기획이다. 다음 기능은 사용자 지시에 따라 최신 dev에서 목적 브랜치를 만들고 범위를 정한다. 이미 통과한 계정 복구 재시험·기존 구간 재수용 대기는 없다. Issue17 전체 종료·dev→main 통합·배포는 하지 않는다.

[인수 결과 원본](../features/recruitment/completion-and-records/completion-recovery-acceptance-20261110.md)·[통합 이력](DEV_LOG.md)을 따른다. 아래 feat/character-lifecycle checkout·미커밋/미push 표기는 당시 구간 기록이며 현재 상태가 아니다.

아래는 직전 구간 기록이다.

## 직전 — Backend 복구·충돌 조사 회신 완료 / Native 대조·사용자 협의 대기

Issue17 [전체39번째 Backend 미해결 명령 복구·충돌 범위 조사 회신](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6737640898)을 게시하고 전체 댓글39개/본문 일치·Issue 상단 상태를 확인했다. [조사 원본](../features/recruitment/completion-and-records/pending-recovery-and-conflicts.md)은 Native38의6개 요청에 기존 지원/정의·Native 변경 필요/서버 변경 필요/현재 불가능·미결정을 구분한다. 원요청 재전송은 조회 전용이 아니며 미실행 요청을 실행할 수 있다. ACK24시간/48시간 식별 기록 삭제와 Native24시간 보류 시계도 구분했다. 현재 GET·ACK 부재나 일반 거절만으로 과거 불명 결과·늦은 실행 불가를 증명할 수 없다. 별도 시각 효과의 선행 commit도 사용자 명령 rollback과 구분한다.

다음 Native는 원ACK/오류별 복구 의미와 owner 단일 slot·업무 충돌 후보를 대조하고 사용자와 최소 변경 범위를 협의한다. 같은 실제 T는 공유 일정/멤버/종료 효과를 고려하고, 다른 room/T도 주간 점유·회원 예약/한도·C/N 원천·방 전체 명령을 대조한다. 알려진 독립 작업을 허용하려면 UI뿐 아니라 Native 저장/transport 설계가 필요하다. 취소는 첫 오류부터 안내만 종료하며 원pending/늦은 ACK는 보존한다. 장기 미해결을 미처리로 종결하려면 지연/in-flight 요청 차단과 원자적 fence·보관 보장이 필요하지만 **미합의·미구현 제안**이다. 새 code/details.reason은 필요성이 확인되지 않아 추가하지 않았다.

Backend 다음은 Native 대조/사용자 선택에 따른 구체 계약 질문 대응이다. 추가 계약/보관 정책을 임의 확정하거나 구현하지 않는다. Native 계약 연결·자동 검증·사용자 기기 확인은 미완료이며 기존16c9cd4/계약864de38b·로컬API101cd82d/DB0036 인계는 유지한다. 이번은 소스/계약·기존 시험 대조와 문서 검사이며 서버/DB/실자료 재실행·기능/OpenAPI 변경·commit/push·배포·Issue 종료는 없다. 회신/조사 문서는 현재 미커밋·미push다.

아래는 직전 구간 기록이다.

## 직전 — Backend 보정·게시·로컬 반영·인계 완료 / Native 연결 대기

Issue17 [전체36번째 Backend 계약 보정·개발 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6735265341) 완료. 고정 구현 `16c9cd4b9016a881bbb26c8438f3347049603902` / feat/character-lifecycle는 origin push·원격 SHA 일치 확인, 실제 로컬 API image101cd82d와 앱285파일/282모듈·두 전체 계약이 같다. 새 two-cycle SHA256 `864de38b53ec23a305074bb3844a7a603ba1f992815427fdba3e6931793119b6`, 선택 query 누락10개 보완·지원/선언65개 일치다. 기본 계약/DTO·본문·권한·토큰·DB 동작은 유지했다. 영향 회귀 최종 고유114PASS·도구63PASS/신규 미해결0이며 과거 전체1921PASS/기존2FAIL과 합산하지 않는다.

실제 로컬 API만 교체했고 DB0036·117표355행의 전체 hash/구조/sequence·키4개·환경/보안/포트·DB컨테이너/볼륨 보존, healthy·listener7개·새 실행 로그17이벤트 오류0을 확인했다. migration·실자료 명령·새 키/환경·dump·운영/APK 배포·merge·Issue 종료는 없다. [구현·검증·인계 원본](../features/recruitment/completion-and-records/completion-profile-contract-fix.md)·[집계](../engineering/operations/records/completion-profile-contract-verification.json)를 따른다.

다음 담당 Native: 전체35번째 오류 안내 결과를 유지하고, 게시된 새 계약을 새 조회·새 명령에 채택해 일관된 participation_profile 연결·자동 검증을 진행한다. 저장 원query·본문·키·검증 snapshot·pending/ACK는 바꾸지 않는다. 이후 사용자 실제 기기 완료 성공을 별도 확인한다. Backend는 구체 차이 회신에 대응하며 같은 안내/계약의 반복 수용을 요청하지 않는다. 후행 문서 커밋/푸시는 이번 승인 범위의 결과 기록이며 새 서버 교체는 필요하지 않다.

아래 상태는 각 이전 구간 기록이다.

## 직전 — Native 오류 안내 완료 / Backend 보정 계약 대기

사용자 지시로 현재 게시 소스ccf091d의 구조 정리를 실제 로컬 API image2f86172d에 반영하고 [전체34번째 Backend](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733877672)로 인계했다. [반영 기록](../engineering/operations/source-layout-local-rollout.md)·[집계](../engineering/operations/records/source-layout-local-rollout.json)를 따른다. 같은 feat/character-lifecycle 유지, 이번 변경은 반영/조사 문서만 미커밋·미push이며 새로운 구현 SHA는 없다.

- 확인: 실제 앱285파일·Python282모듈·두 전체 계약이 후보/현재소스/게시ccf091d와 같다. DB0036·117표357행의 전체 행 hash/구조/sequence·키4개 내용/권한·환경/보안/포트·DB컨테이너/볼륨을 보존했다. API/DB healthy, 실제listener200/401/404·no-store, 새 실행 로그 오류0이다. DB migration·새 키/환경·dump/실자료 쓰기·Native 기기는 변경하지 않았다.
- 완료 프로필 불일치는 아직 수정 전이고 계약 hash2aeca907도 같다. 구조 기동 성공을 완료 버그 해소로 표시하지 않는다. 기존 전체1921PASS/기존2FAIL과 조사8PASS는 각 해당 범위로 재사용했으며 반복 전체 회귀·실회원 완료/교체/기기 성공으로 확대하지 않는다.
- [전체35번째 Native 결과](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733937729): 기존 code/status/request_id 보존·안전한 오류정보 펼침/복사, 완료 ACK/성공 이벤트와 후속 GET 실패 분리·조회만 복구를 일반 앱에 연결했다. Native 자체 전체2832PASS/68s·analyze0, 신규6개 포함이다. 기준7a165ac1 위 변경은 미커밋·미push이고 실제 회원 명령/기기 인수는 미실행이다. 현재 query/schema를 추측 변경하지 않고 Backend의 새 계약/hash·동작 목록/HTTP 검증·개발 적용 결과를 기다린다. 같은 Native 안내/시험 수용을 다시 요청하지 않는다.
- Native 전체32번째에서 기존 코드/status/request_id 분류 방향을 수용했고, [전체33번째 사용자 승인 구현·Backend 요청](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733769180)을 접수했다. 실제 제보 request_id/profile의 상관은 아직 확인되지 않았으며 보정 착수의 선행 기기 자료 요청으로 확대하지 않는다.
- 다음 Backend: 요청된 완료 POST2개의 participation_profile 선언을 실제 허용/검증과 일치시키고 추가8동작을 토큰/CAS/능력표식별 대조·보정한다. 계약 기반 query→실제 HTTP 연결 회귀, 새 OpenAPI hash/고정 소스·변경 동작·개발 반영 결과를 인계한다. 새 wire code/필드 추가·권한 완화·원query/키/본문/ACK 변경·자동 새 명령은 범위 밖이다. Native는 기존 오류 안내를 구현하고 이후 새 계약을 소비한다. 이번 사용자 지시는 현재 소스 로컬 반영으로 마쳤으며 계약 수정·추가 Git 게시·운영 배포·Issue 종료를 완료한 것은 아니다.


## 직전 조사 — Issue17 기기 완료 차단 / 계약 보완·기기 재확인 미완료

[전체30번째 Native 제보](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6732895692)에 [전체31번째 Backend 조사·오류 분류](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733182655)로 회신했다. [조사 원본](../features/recruitment/completion-and-records/completion-context-profile-audit.md)을 따른다. 완료 context GET에는 participation_profile이 선언돼 있으나 공대/개인 완료 POST에는 누락돼 계약 기반 자동 query에서1/0 조합이 발생한다. 서버는 두 POST 모두 profile을 실제 허용하고 토큰/요청 일치를 검사한다.

- 확인: 실제 dev imagece59926c/DB0036의 같은 계약 누락·완료400/CONTEXT_INVALID3건을 읽기 전용으로 확인했다. 실제 사용자 요청의 내부 분기는 로그상 미확정이다. 격리 DB/실제 HTTP에서 두 완료 경로×4조합8PASS/111.54s, 불일치 거절 시 업무 표 hash 보존·합성 통제 재시도/원ACK를 확인했다. 이는 버그 경로 진단이며 수정 완료가 아니다.
- 추가: 같은 CycleRoute의 선언 누락은 완료2개 포함10동작이다. 다른8개는 단순 조회·CAS 명령·양쪽 선언이 빠진 완료 정정을 구분해 검토한다. 현재 외부 오류 코드/필드 추가보다 기존 code/status/request_id 활용을 권장하며 details.reason 임의 확장은 금지한다.
- 다음 Native: 기존 오류 분류·결과불명/원pending 보존·향후 계약 소비 범위와 제보 request_id/profile 유무 상관 여부를 필요한 차이만 확인한다. Native의 전체29번째 구현7a165ac1 게시·전체2826PASS는 확인했으나 이번 기기 오류 해소 근거는 아니다.
- 다음 Backend: 완료2경로 선언/실제 지원 불일치를 보완하고 추가8동작·계약 기반 GET/POST 연결 회귀를 수정 범위로 제안했다. 사용자 구현 지시/소비 범위 협의 후 진행하며 지금은 조사·회신이다. 새 오류 계약/정책은 임의 확정하지 않는다. 앱/실행 OpenAPI·서버/DB·실자료·키/환경·Native 코드는 변경하지 않았고 이번 문서는 미커밋·미push다. 직전 정리의 게시 승인을 새 작업의 자동 게시 승인으로 적용하지 않는다.


## 완료 — 1·2차 폴더 정리·문서 게시 / 서버 미반영

사용자 지시로 개발 현황·1차 정리·2차 계획을 `34a2a4789c62e4beb7dccaef033e655341acb548`에 커밋했고, 후속 게시 승인으로 2차 정리·탐색 안내를 `6a87e143e651bd9fc51129f969bfd9ced314a5a1`에 커밋해 두 커밋을 `origin/feat/character-lifecycle`에 push했다. 구조 구현6a87e14의 원격 SHA 일치를 확인했으며 게시 상태 기록은 같은 브랜치의 후행 문서 커밋으로 남긴다. 같은 `feat/character-lifecycle`에서 [2차 계획](../engineering/development/source-layout-phase2-plan.md)을 실행해 Python77개 이동/분리·init2개 유지·JSON1개 이동을 완료했다. 두 기능 루트에는 init만 남기고 HTTP·DTO·ORM·계약과 실제 업무 책임을 분리했다. [대응표](../engineering/development/folder-layout-phase2-map.json)·[최종 검증](../engineering/development/folder-layout-phase2-verification.json)을 따른다.

- 완료: 앱 Python282개 import, 두 전체 OpenAPI·독립 draft2개·전 패키지 ORM117테이블 DDL/인덱스 동일, 기존1916개+새7개=1923개 수집. 기존3682개 함수/클래스 정의 누락0·경로 정규화 후 기존 변경은 main의 계약 ID 보존 호출1개다. 최종 이미지의 앱/시험/도구439파일은 현재소스와 바이트 일치한다.
- 전체1923개를8개 독립 tmpfs PostgreSQL로 검증했다. 최초1919PASS/4FAIL 중 정리로 생긴 메타데이터 도우미의 모델 참조 문제2사례를 고치고 각각1PASS(4.03s/3.00s)로 확인했다. 최종 고유1921PASS·이동 전에도 확인된 기존 기대 불일치2FAIL이다. 재실행을 중복 합산하지 않고 신규 미해결 실패0이며 전체 통과로 표시하지 않는다. 모든 시험 컨테이너/네트워크 cleanup0을 확인했다.
- 기존 후속: 그룹 활동 해제 뒤 기존 참가 거절 기대와 stopped 상태 뒤 미선택 N 개설 허용 기대2개다. 업무 정책/기대값을 정리 작업에서 바꾸지 않았다. 도구63PASS·계약 보존 단위7PASS(업무 수집에도 포함)·문서/동결/경로/diff 검사를 통과했다.
- 게시 전 새 파일/이동 파일 끝 빈 줄39개를 제거했다. AST 동일·회귀 이미지 대비 차이 재검토와 최종 후보439파일/소스 바이트 일치를 확인했다. 전체 업무 회귀는 기존1921PASS/기존2FAIL 근거를 재사용하며 도구63PASS·계약 보존7PASS·문서/동결/diff를 확인했다. 코드 위치는 [현재 파일 찾기](../engineering/development/source-layout.md#현재-파일을-찾는-순서)와 모집 README를 사용한다.
- 다음 Backend: 사용자 다음 지시/구체 차이에 대응한다. 1·2차와 후속 문서는 같은 목적 브랜치에 게시했으며 이번 사용자 지시를 후속 작업의 상시 게시 승인으로 확대하지 않는다. **실제 dev/운영 미반영**이며 merge·서버 반영은 별도 지시다. 개발 API imagece59926c/DB0036·키/환경·Native 소스/기기는 변경하지 않았다. 아래 미커밋/미push·이전 경로·Native 대기는 각 당시 기록이다.

## 1차 정리 결과 — 34a2a47 커밋 전 기록

2026-11-09 사용자 승인 계획을 feat/character-lifecycle·기준dd7d68b에서 구현했다. 앱 업무95파일과 시험103파일을 기능별 하위 패키지로 이동하고 모든 참조·시험 검색을 보완했다. 공개 DTO/이를 포함한 라우터·OpenAPI 자원·ORM 모델의 기존 경로79개는 유지했다. [분류 기준](../engineering/development/source-layout.md)·[이동표](../engineering/development/folder-layout-map.json)·[최종 검증](../engineering/development/folder-layout-verification.json)을 따른다.

- 완료: 이동 전후1916개 수집 일치, 업무/시험349파일 AST 보존, 앱256모듈 import, 모델116개 등록/PostgreSQL DDL 동일, 기본125/142·two-cycle188/209 전체 계약 일치, 도구63PASS와 문서/동결 자료·diff 검증. 최종 시험 소스413파일은 작업 소스와 일치한다.
- 전체1916사례를 초기 실행+4개 독립DB 묶음으로 검증했다. 최종고유1914PASS·기존 기대값 불일치2FAIL이며 전체 통과가 아니다. 분할 중복14개·단일 재실행은 합산하지 않는다. 이동 원인의 subprocess import1은 수정 후 해당1PASS로 해소했고 시험DB/network는 모두 정리됐다.
- 별도 후속: `tests/groups/test_group_raid_lifecycle.py::test_group_leave_preserves_actual_c_but_does_not_admit_new_n`의 활동 해제 후 기존 참가 거절 기대, `tests/raid_rooms/participation/test_recruitment_cycle_lifecycle.py::test_closed_c_opening_respects_completed_archive[stopped]`의 미선택 개설 허용 기대는 이동 전 고정 이미지에서도 동일 실패했다. 사용자 선택 시 현행 합의 정책과 기대를 대조하는 별도 구간으로 다루며 이번에 임의 변경하지 않았다.
- 다음 Backend: 사용자 다음 지시/구체 차이에 대응. 새 업무코드 위치는 이동표를 사용한다. 현재 변경은 미커밋·미push·실제 dev 미반영이며 commit/push/merge·서버 반영·운영은 별도 지시다. 실제 dev imagece59926c/DB0036·키/환경/자료와 Native 소스/기기를 변경하지 않았다. 아래 폴더 보류/실행소스 일치는 각 이전 구간 기록이다.

Issue17 게시 최신: 사용자 지시로 보완 구현 `caffaf3405a53be941250132a2b50779943b15f6`를 origin/feat/character-lifecycle에 push하고 원격 SHA 일치를 확인했다. [전체27번째 Backend 고정 구현 인계](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722956197) 기준이다. 커밋의 앱247파일은 실제 dev imagece59926c/DB0036과 일치하며 새 서버 반영은 없다. Native26 실행 지원 접수·추가 요청 없음, 다음 Native 기능 구현/연결이다. 아래 미커밋·미push/원격 기준 없음은 당시 기록이며 폴더 이동 보류·미병합/운영 미반영을 유지한다.

Issue17 [전체25번째 Backend 실제 로컬 보완 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722917497) 인계 완료. Native24 소비 수용·실행 지원 대기 해소, 다음 Native 기능 구현/연결이며 소스 미커밋·미push와 폴더 이동 보류를 유지한다.

## 현재 — Issue17 Native 소비 수용·로컬 개발서버 보완 반영 완료

[전체24번째 Native 보완/소비 대조 수용](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6722805010)에서 추가 제품 결정·계약 질문/Backend 수정 요청이 없음을 확인했다. 사용자 조건부 로컬 반영 지시로 API만 새 imagece59926c로 교체했고 한국2026-11-08 23:43:37 시작·DB0036 유지다. [반영 집계](../engineering/operations/records/roster-participation-followup-local-rollout.json)·[보완 계약/검증](../features/rosters/lifecycle/roster-participation-followup.md)을 따른다.

- 현재 지원: active0 완료P 신규 선택 제거·CHARACTER_SELECTION_REQUIRED, 명시 선택의 현재 자격/CAS·원ACK, 혼합M/P 후속 경계 보완이 실제 로컬 소스에 있다. 실행247파일/후보·작업소스 바이트 일치, 두 전체 생성 계약 일치·healthy·실제 listener200/보호된 신규 context401 확인. 실자료 방0으로 신규 참가/교체 쓰기는 실제 dev에서 실행하지 않았고 기존 격리 근거와 구분한다.
- 보존: DB0036 그대로,117업무표99행/열·sequence·키4개·환경/보안/포트·DB컨테이너/볼륨 동일. migration·DBdump/자료복구·키생성 없음. 기존 유효 환경/키 보관본을 재사용하고 로컬 dump 제외 결정을 유지했다.
- 다음 Native: 기존 debug 로컬 대상에서 지원되는 계약으로 사용자 지시 범위의 기능 연결/구현을 진행하고 구체 차이가 있으면 같은 Issue에 회신한다. 이미 수용한 계약/격리 시험의 반복 수용·기기 재시험을 요구하지 않는다. Native 신규 DTO/실연결/기기는 미완료이며 Native가 주도한다.
- 다음 Backend: 구체 차이/추가 요청에 대응. checkout feat/character-lifecycle, 보완 구현caffaf3을 원격 게시했고 실제 dev imagece59926c와 앱 소스가 같다. 같은 브랜치의 후행 문서는 게시 결과만 기록한다. commit/push/merge·운영 배포·자료 변경·Issue 종료는 별도 사용자 지시다.
- **사용자 지시: 폴더 분류·파일 위치 이동은 하지 않는다.** 해당 작업에 착수/구조 지침 변경을 하지 않았고 이번 API 반영에도 포함하지 않았다. Penpot 선확인 제외→Native 기능 개발 후 사용자 기기 확인 순서 보고를 유지한다.

## Issue34·38·46 완료 종료 — 2026-11-08

Native의 본문 최신화와 [#34 전체15번째](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6718443740)·[#38 전체10번째](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6718445004)·[#46 전체7번째](https://github.com/heo0328/lostparty-backend/issues/46#issuecomment-6718450091) 회신을 Backend에서 확인했다. 세 원요청 구간 모두 완료·종료 가능이며 추가 Backend 구현/회신 요청·Native 재수용 대기는 없다. 변화 없는 수용 댓글은 추가하지 않는다. 후속 사용자 명시 지시에 따라 세 Issue를 모두 CLOSED/completed로 종료하고 반환 상태를 확인했다. 본문 상단에 Backend 최종 종료 기록을 추가했으며 새 댓글은 작성하지 않았다.

- #34: Backend v2.0.0 운영 반영·Native 서명 APK 게시 완료. 과거 통합/APK 게시 대기는 해소됐다. 새 APK 운영 전체 인수·다음 서명 전환은 별도 후속이며 완료로 확대하지 않는다.
- #38: 양측 구현·자동검증·사용자 로컬 변경 구간 인수·운영 반영·후속 APK 게시 근거 확인. 추가 수정/시험 대기 없음.
- #46: 합의한 조사·수동 백업·PC 보관 확인·문서 게시 완료. 외장 사본 미확인·실제 복원/정기 자동화 미실행은 보존하며 개발 재개/이번 종료의 선행 조건으로 추가하지 않는다. Native 로컬 문서는 미커밋·미push이며 원격 게시 완료로 표시하지 않는다.

종료 전 세 Issue의 최신 본문/전체 댓글을 재확인했고 완료 근거와 별도 후속을 보존해 completed 종료했다. 새 배포·자료/키 변경·commit/push는 포함하지 않는다. 아래 OPEN 유지·다음 APK 게시·이전 checkout은 당시 기록이며 현재 대기는 이 절을 따른다.

## 남은 Issue 권장 처리 순서

다음은 사용자에게 제시한 권장 순서이며 세부 정책/계약 확정이나 새 기능 구현 착수를 뜻하지 않는다. 열린 작업은 #17·#15·#18·#19이며 기능 구현 때 최신 Issue/코드/계약을 재대조한다.

1. **#17 캐릭터 생명주기:** Backend가 외부 API 증거와 현재 차단/이력 구현의 공백부터 정리하고 소멸·재등장·이름 재사용 기준을 Native와 합의한다. 확보 불가능한 증거는 보류 기준으로 명시한다.
2. **#15 소유권 분쟁 후처리:** #17에서 확인한 자격 상실/보존 경계를 참고해 영향 원정대만 처리하는 그룹·레이드 정책을 사용자와 결정하고 Native 회복 동선→계약→구현·검증으로 진행한다. #17 전체 완료가 강제 선행 조건은 아니며 정책 검토는 독립 진행 가능하다.
3. **#18 활동 자동 추가·명시 제외 보존:** 앞선 소유/생명주기 기준과 충돌하지 않게 신규 발견·첫 기준 도달·직접 제외/재등록·동시 명령을 확정하고 최소 영속 모델·API와 Native 연결을 구현한다.
4. **#19 주간 통계:** 앞 단계의 관계/상태 전환을 반영해 통계 귀속·분모·권한을 확정하고 원천 보존→마감/재처리→집계/조회 순으로 구현한다. 과거 원천 미확보 주차는 0으로 합성하지 않는다.

각 구간은 합의→Backend 구현/격리·계약 검증→로컬 dev 반영→필요한 Native 연결·사용자 변경 범위 확인→완료 기록으로 마감한다. 배포·자료 삭제·commit/push는 별도 지시 기준을 유지한다.

2026-11-07 게시 권한 변경: 통상 작업은 로컬에 누적하고 commit/push/merge는 사용자 직접 지시로 수행한다. 기존 마감·인계 상시 승인은 철회하며 제한된 예외는 [작업과 Git](../engineering/development/workflow.md#section-2)을 따른다. 이번 지침 변경은 이후 사용자의 명시적인 dev/main 통합·push 지시 범위에 포함한다.

<a id="recovery-backup-closeout"></a>

## 복구·백업 기록 마감 — 다음 개발자 작업 선택

2026-11-07 로컬 개발 환경·앱 Google 로그인과 Git push 복구, 운영 온라인 기준본의 생성·사용자 내장 SSD 저장·읽기/내용 비교를 완료했다. 로컬 DB dump는 사용자 지시로 제외, 실제 서비스 복원·정기 백업 자동화는 미실행이며 외장 매체 사본은 미확인이다. [백업 원장과 안내 시점](../engineering/operations/backup-and-recovery.md)·[검증/오류 이력](DEV_LOG.md#development-recovery-20261107)·[집계](../engineering/operations/records/backup-recovery-2026-11-07.json) 기준이다. 이전 운영 백업 보류는 사용자 후속 승인으로 이번 수동 기준본에 한해 해제됐다.

- 다음 Backend: 개발자 작업 선택/구체 장애에 대응. 복구 문서 구간은 c62f2a7 게시와 Issue46 전체6번째 Backend 회신으로 마감했다. 백업 자료를 다시 만들거나 Native 정상 로그인/같은 기준 재수용을 반복 요청하지 않는다. Issue46은 OPEN 유지한다. 사용자가 후속 지시한 dev/main 통합에 문서를 포함하며 Issue 종료·추가 배포는 포함하지 않는다.
- 다음 사용자: 현재 PC 백업 파일 보관 유지, 원하는 때 외장 매체에 복사. 자동 배포 개인키 원본은 분실로 확정했으므로 다시 보유 여부를 묻지 않는다. 정상인 배포 Secret은 유지한다.
- 선택 후속: 대표 회귀 묶음의 ACCESS_INVALID 준비 오류1/CLIENT_UPGRADE_REQUIRED 실패1은 두 사례만 재실행 시2PASS였으나 최초 원인은 미확정. 사용자 선택 시 표적 조사하며 환경 복구/백업 마감의 전체 미완료로 확대하지 않는다. 세션 갱신·실제 복원/복구시간·정기 자동화는 이번 신규 완료 근거가 없다.
- 실행 구성 단일화는 아래 독립 후속 그대로 구현 미착수. 서울 리전 이전·Native 새 release 서명 적용도 이번 범위 밖이다.

사용자의 2026-11-07 명시 지시로 실행 구성 조사2dd3a06·복구/백업 기록c62f2a7·게시 권한 변경을 dev에 통합하고 main도 같은 커밋으로 동기화하는 구간이다. 완료 checkout은 dev로 두며 통합·원격 게시 확인 후 두 문서 작업 브랜치를 정리한다. 실제 Git 결과는 최종 보고로 확인한다. 아래 checkout은 각 기록 당시 상태다. Native v2.0.0 APK 게시는 [Issue34 전체14번째 Native](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6609824463)로 완료 보고를 확인했으며 아래 APK 게시 대기는 현재 대기가 아니다.

<a id="runtime-consolidation-followup"></a>

## 후속 선택 — Backend 실행 구성 단일화(구현 미착수)

2026-11-06 조사·후속 등록 완료. 다음 담당 Backend이며 개발자가 이 구간을 선택할 때 [개선 대장](backend-improvement-plan.md#runtime-consolidation)·[조사 보고서](../engineering/development/runtime-consolidation-review.md)의 선행 확인/수정안·검증 조건으로 이어간다. 최신 기본 실행 통일과 기존0023 회귀용 실행 분리를 권장하며, 기존 API/원 ACK·이력/DB 보존은 별도 책임이다. 즉시 구현·서버 재기동·migration·운영 반영 대기로 지정하지 않는다. [수행 이력](DEV_LOG.md#runtime-consolidation-review).

실행 구성 조사 당시 문서 작업 checkout은 `chore/backend-runtime-consolidation`, 시작 기준은 dev/main 원격 `f211342`다. 아래 checkout·로컬 실행 이미지·APK 게시 대기는 각 기록 당시 상태다. 이번 사용자 로컬 기동 결과와 이후 Native 게시 회신의 구분은 조사 보고서를 따른다.

## 완료 — Backend v2.0.0 운영 반영 / 다음 Native APK 게시

개발자 승인 PR45·source51b1cb3·v2.0.0 태그1회 게시, Actions41674801953/production Deployment7524537038 success로 한국2026-11-04 01:31:59 운영 반영 완료다. AWS imagef33f4c6c·DB0035에서 이슈41 일괄 GET/POST와 이슈42 참가 유지 예방 수정을 지원한다. [배포 집계](../engineering/operations/records/backend-v2.0.0-deployment.json)·[이력](DEV_LOG.md#backend-v2-release) 기준이다.

이번 한정 로컬 검증 기록/소스 일치를 재사용했고 신규 앱 회귀0·scripts61PASS, 두 로컬 전체 생성 계약/게시 증거 대조·독립 공개 최소 점검을 완료했다. DB/Caddy·환경/키 보존, migration·기존 review 복구·로컬 dev 교체·롤백 없음. 운영 실회원 쓰기/새 APK 실기기 전수 인수와 구분한다.

[Issue34 전체13번째 Backend 운영 완료](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6609667274)로 전체11/12번째 Native의 운영 지원 확인 대기를 해소했다. 다음 담당 Native는 기존 승인 범위의 v2.0.0 태그/서명 CI/APK 게시를 진행한다. Backend 추가 기능/정상시험 반복 요청은 없고 다음 개발자 지시 또는 구체 장애에 대응한다. 이슈41/42 완료 종료는 유지하며 운영 추적 #34는 종료하지 않았다. 후행 완료 기록도 dev/main 같은 기준으로 모으며 아래 운영 미반영/진행 문장은 이전 이력이다.

## 완료 — Backend dev/main 통합·Issue41/42 종료 / 다음 개발자 지시 대기

사용자 승인으로 최신 인수 기록9d0a7b7을 [PR44](https://github.com/heo0328/lostparty-backend/pull/44)·병합4231a58에 dev 통합하고 main도 fast-forward·원격 동일 SHA를 확인했다. [Issue41 전체15번째 Backend 완료 결과](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6609216803)·[Issue42 전체9번째 Backend 완료 결과](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6609226056) 회신 후 두 이슈를 completed로 종료했다. 후행 종료 기록까지 dev/main 같은 최종 커밋으로 보존한다. [최종 이력](DEV_LOG.md#issues-41-42-integration-closeout) 기준이다.

현재 checkout dev. 완료 fix/raid-participation-continuity는 dev 포함·원격 게시·미커밋 없음 확인 후 로컬/원격 정리했고 미완료 feat/activity-selection은 보존한다. 두 이슈의 개발·로컬 인수·양측 게시·Backend Git 정리 대기는 모두 해소됐다. 추가 수정/시험 요청은 없으며 다음 개발자 지시 또는 구체 차이에 대응한다.

AWS 운영v0.1.2와 로컬 실행 imagebe56f76c/DB0035는 Git 통합으로 교체하지 않았다. 운영 배포·태그·APK·DB/키/자료 변경은 없다. 운영 테스터 전 게시 시점은 개발자 별도 지시이며 기존 운영 추적은 [Issue34](https://github.com/heo0328/lostparty-backend/issues/34)·배포 기록을 따른다. 기존 dev review 복구는 제외된 최종 범위이며 후속 필수 과제가 아니다.

## 완료 — Issue42 예방 수정·사용자 로컬 변경 구간 인수

[전체6번째 Flutter 사용자 로컬 실기기 인수 통과](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6607158974)를 확인했다. 활동 해제 후 기존 방의 데이터 보존/정상 이용, 신규 생성·교체 후보와 그룹 활동 목록 제외, 다른 활동 캐릭터로 참가 변경 성공·해제 캐릭터 재노출 없음의 변경 구간은 인수 완료다. [전체5번째 Flutter 보완/자동검증](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6606255488)·[수신 이력](DEV_LOG.md#activity-continuity-local-acceptance)을 따른다. Backend 업무0207d0f·로컬 imagebe56f76c/DB0035·고유57PASS와 Flutter관련321PASS·사용자 보고를 구분하며 Backend 독립 재현이나 모든 C/N·역할·타 계정 전수 인수로 확대하지 않는다.

추가 Backend 수정/재시험 요청은 없고 구체 차이 또는 다음 개발자 지시 대기다. [Issue41 전체14번째 Flutter 원격 인계](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6608982829)·[Issue42 전체8번째](https://github.com/heo0328/lostparty-backend/issues/42#issuecomment-6608986700)로 Flutter dev/main 원격 게시·통합 대기는 해소됐다. 실제 두 원격 head가 `11e9c847900441417c373452fa6fce8dfcf743db`임을 읽기 전용으로 대조했다. 전체2817PASS/analyze0은 Flutter 자체 결과이며 기존 부분집합 시험과 합산하지 않는다. Issue41은 [전체12번째 사용자 선택](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6608556182)으로 LostArk 기본 동시2를 확정했고 구현/기기 비교·원격 인계까지 완료했다. 추가 Backend 요청이나 반복 시험은 없다. 기존 dev review 복구는 사용자 최종 범위에서 제외했고 후속 필수 과제로 남기지 않는다.

운영 테스터 전 예방 수정의 배포는 개발자의 별도 지시 대상이다. 사용자 승인 Git 통합·Issue 종료는 위 최신 기록대로 완료했다. 운영 배포/태그/APK/자료 초기화·복구는 하지 않는다. [동작 계약](../features/recruitment/membership-actions/activity-participation-continuity.md)·[기존 Backend 검증](../features/recruitment/membership-actions/activity-continuity-verification.json) 기준이다.

## 완료 — 초기 자동 갱신 Backend 반복 호출 축소 / Issue41

`feat/startup-batch-refresh`에서 [승인 계약](../features/rosters/bootstrap/startup-batches.md)·일괄 GET/POST를 구현했다. 신규42·관련 기존102의 고유144PASS, 기본/two-cycle 전체 계약 일치, 로컬 dev API 갱신과 Windows8000 health200/새 경로 미인증401을 확인했다. DB0035·기존 DB/키/자료 보존. [검증 집계](../features/rosters/bootstrap/startup-batches-verification.json)·[결과 이력](DEV_LOG.md#startup-batches) 기준이다.

구현 `b1f11bb5011056ce5dd655efe7c8efe2765960e3` 원격 게시·[전체3번째 Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6602009469) 완료. [전체4번째 Flutter 구현·자동검증](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6603057228)과 [전체5번째 Flutter 로컬 실기기 첫 측정](https://github.com/heo0328/lostparty-backend/issues/41#issuecomment-6603203545)을 수신했다. 앱 연결/인증된 양성 batch HTTP와8개 fetched/applied는 Flutter가 사용자 로그로 관측한 근거이며 Backend 독립 재현·전체8항목 DB 저장 확인과 구분한다. 상세 결과는 [DEV_LOG](DEV_LOG.md#startup-batches-native-feedback) 기준이다.

사용자는 현재 Backend의 반복 호출을 일괄 조회1회·저장1회로 줄인 성과를 확인하고 이 작업 구간을 문서 마감한 뒤 Issue42로 이동하도록 지시했다. **Backend 구간은 완료이며 네이티브 LostArk 동시 조회 조정도 사용자 기본2 선택·실기기 비교·원격 게시로 마감됐다.** 2/5 비교·실패 실기기 인수·8항목 저장 내용 독립 DB 확인의 미실행 기록은 남기되 이번 Backend 구간을 붙잡는 대기로 두거나 추가 시험을 자동 요청하지 않는다. 전체 시작시간 개선·최적 동시성·원격 Flutter 코드 인계는 확정하지 않는다. Flutter dev/main 원격11e9c847 통합·게시 대기는 해소됐다. 당시 보류 기록과 구분한다. Backend dev/main 통합·Issue 종료는 위 최신 기록대로 완료했으며 운영 배포·태그·APK·자료 초기화는 없다. 아래 운영 완료는 이전 v0.1.2이며 이번 API의 운영 지원을 뜻하지 않는다.

## 완료 — 그룹 초대 수정 운영 반영 v0.1.2

사용자가 승인한 main b649ccf의 앱 코드를 PR40·source2c6070c로 v0.1.2에 게시하고 실제 운영 API에 반영했다. [배포 집계](../engineering/operations/records/backend-v0.1.2-deployment.json)·[전체9번째 Backend 운영 결과](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6599670183)를 따른다. 운영은 image7c8b8db9·DB0035, 한국2026-11-03 18:07:40 API 시작/18:07:53 반영 완료다. Actions41608259484·production Deployment7514620773 success, 공개health200/DBok·카탈로그200·미인증me401을 확인했다.

이번에 한정 승인한 검증 재사용으로 기존 run41417066498 전체1817PASS를 source/조상 관계·변경 범위·artifact hash와 대조했다. 신규 앱 테스트/계약/교체복귀 시험0, 새 제어 스크립트59PASS·schema2 checks reused·원본 검증 JSON 보존이다. 태그 실행부터 서버 반영까지 약1분51초였다. DB/Caddy·운영환경/mount/보호파일 보존·schema 호환/health를 기존 제어기로 확인하고 API만 교체했으며 migration·키/회원 자료 변경·롤백은 없었다. 실제 운영 사용자 인수나 네이티브 APK 게시로 확대하지 않는다.

다음은 추가 지시 대기다. 기본 개발은 로컬 dev이며 다음 운영 반영/APK 게시도 개발자가 지시할 때만 진행한다. reuse는 v0.1.2만 허용하므로 다음 버전에 자동 적용하지 않고 selected/full을 정한다. checkout dev, 완료한 chore/release-group-invite는 로컬/원격 정리·미완료 activity-selection은 보존한다. 이 후행 결과 기록까지 main/dev를 동일 커밋으로 최신화하되 v0.1.2 태그·실행 source2c6070c는 보존한다.

2026-11-03 사용자 승인 [PR39](https://github.com/heo0328/lostparty-backend/pull/39)·병합323b665로 그룹 초대·상속된 검증 범위 개선과 인수 문서를 dev에 통합했다. checkout dev, 완료한 feat/group-invite-eligibility·chore/release-validation은 로컬/원격 정리했고 미완료 feat/activity-selection은 보존한다. 이 후행 마감 기록까지 포함한 최종 dev 커밋으로 main도 fast-forward 동기화한다. 다음 기능은 개발자 지시에 따라 최신 dev에서 목적 브랜치로 시작한다. 운영 태그·배포·서버/DB·Issue 종료는 이번 Git 통합 범위에 포함하지 않는다. [통합 이력](DEV_LOG.md#invite-eligibility-git-integration)을 따른다.

## 완료·다음 지시 대기 — 이슈38 초대 검색 변경 구간

[전체8번째 Flutter 사용자 로컬 변경 구간 전부 통과](https://github.com/heo0328/lostparty-backend/issues/38#issuecomment-6576244724)를 확인했다. 이번 초대 검색의 네이티브 소비·자동검증·Backend 로컬 반영·사용자 변경 범위 확인까지 완료이며, 이전 실패 검색/화면 재확인 대기를 해소한다. 앱 전체·AWS 운영 인수로 확대하지 않는다. [로컬 반영 집계](../features/groups/invite-eligibility-local-rollout-2026-11-02.json)·[완료 이력](DEV_LOG.md#invite-eligibility-local-acceptance)을 따른다.

현재 요청된 추가 Backend 작업·정상시험 반복은 없다. 실제 차이나 개발자의 추가 지시가 있을 때 해당 범위만 진행한다. **운영 배포와 네이티브 APK 게시 시점은 각각 개발자가 명시 지시한다.** 개별 수정·테스트 통과·commit/push를 배포 승인으로 해석하지 않으며 dev/main 통합·태그·운영 반영·Issue 종료도 자동 진행하지 않는다. Git 통합과 승인된 AWS v0.1.2 반영은 위 최신 기록대로 완료했고 추가 배포는 별도 지시 대상이다. [개발/운영 기준](../engineering/development/workflow.md#local-dev-and-production)을 따른다.

## 완료 — 변경 규모별 배포 검증 Git 통합

selected/full·계획 검사·불변 validation.json 개선은 그룹 초대 브랜치에 상속된 이력을 포함해 PR39로 dev에 통합했다. [운영 기준](../engineering/operations/backend-release.md)·[검증 집계](../engineering/operations/records/backend-validation-scope-verification.json)·[Issue34 전체10번째 결과](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6572819899)를 따른다. 당시 수동 Actions41410922327/sourcefbb9bc7 전체1811PASS·scripts52PASS·artifact 대조·publish/deploy skip과 로컬 selected 실DB 미실행 경계는 이력으로 보존한다.

현재0.1.1 계획을 새 운영 태그에 재사용하지 않는다. 다음 운영 릴리즈는 개발자가 구간·시점을 지시할 때 새 VERSION/계획과 태그를 준비한다. 이번 승인 v0.1.2의 한정 검증 재사용/운영 반영은 위 최신 기록을 따른다. 이후 별도 요청 전 GitHub Actions·운영 반영을 실행하지 않는다. 이전 Git 통합 당시 운영v0.1.1 보존 사실은 당시 이력이다.

## 완료 — Backend v0.1.1 첫 자동 배포 (2026-11-02)

사용자 승인으로 PR36·main/dev 동일77c9de2·v0.1.1 1회push를 완료했다. [Actions attempt2](https://github.com/heo0328/lostparty-backend/actions/runs/41323830955/attempts/2) success, 전체8그룹1811PASS·이미지/Release게시·production Deployment7475782412와 서버journal 성공을 확인했다. 실제 API source77c9de2/image259e8234·DB0035이며 한국11월2일01:30에 API만 교체했다. DB/Caddy·운영env/Google허용목록/키는 보존, 공개health200/DBok·공개조회200·미인증me401을 독립 대조했다.

[배포 집계](../engineering/operations/records/backend-v0.1.1-deployment.json)·[전체9번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6560737194)를 따른다. v0.1.0의 checkout/tag fetch 충돌은 수정했다. v0.1.1 attempt1의 SSH 인증 전 중단은 Secret 등록 시 끝 개행 제거 문제를 확인해 제한키 교체·개행 보존 등록으로 해소했고 같은 이미지로 재실행했다. 이전 전용키 폐기·임시 인증 복사본 삭제 완료다.

자동 배포 도입/실서버 반영은 완료다. 다음 릴리즈는 변경을 목적브랜치→dev→main으로 통합하고 VERSION과 새 승인 태그를 맞춘다. DB 변경은 계속 자동 migration 금지·별도 승인이다. 외부 DB/키 백업 미구성은 별도 후속이며 새 전체 기기 인수를 주장하거나 기존 release Google 로그인 인수를 반복 요청하지 않는다. 아래는 이전 준비/협의 이력이다.

## 이전 준비 — Backend 태그 기반 자동 배포 구현

사용자 확정안으로 `chore/release-management`에서 VERSION0.1.0·태그 검증/이미지·Release 게시·전용 SSH·서버 단일 실행/journal·DB/구성 사전 거절·API만 교체/복귀를 구현한다. [운영 계약](../engineering/operations/backend-release.md)을 따른다. GitHub production 환경(v*태그만)·SSH Secret/고정호스트키 변수·태그 수정/삭제 방지 ruleset 준비, 서버 root배포도구/기존 정상 복귀기준과 배포없는 preflight를 완료했다. API/DB/Caddy 시작시각은 보존했다.

**외부 조건과 다음:** OIDC는 새 AWS 가입 방식의 iam:*Provider* 제한으로 불가함을 공식문서/실제거절로확인했고 사용자승인으로전용SSH키 방식으로변경했다. Free plan/Paid전환없음. 서버 강제명령/최소sudo·GitHub production Secret·고정호스트키를 준비하며 실제 전용키 preflight/셸·포워딩 차단 확인·[전체6번째 Backend 구현/준비 인계](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6559243667) 완료. GHCR 최초 package public/익명pull·실GitHub workflow/자동배포는미확인이다. 다음은 dev/main 통합 승인 → 수동workflow검증 → 사용자승인 첫태그 → 최초GHCR공개접근확인 → 실제반영확인이다. 태그/Release/운영API교체는이번준비에서실행하지않는다. 검증은 최초8그룹1805PASS/6옛기대FAIL→테스트보정후대상11PASS다. 수정후전체8그룹재실행은미실행이며수동GitHubworkflow전체green이선행조건이다. scripts37(배포25포함)·계약·실Docker복귀/untaggedID·전용SSH점검PASS. DEV_LOG 마감기록을따른다.

## 완료 — v1.1.2 release Google 로그인

사용자 콘솔화면/정확한release client ID·반영승인으로 등록값 대기를 해소했다. [전체4번째 Backend · release azp 운영 반영](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558294576)·[반영집계](../engineering/operations/records/lightsail-release-azp-rollout.json) 기준: 기존debug ID에확정release ID추가, Web audience/인증검증유지, 동일source6154e45/image dfad04e8의 API만2026-11-01T13:00:31Z 재생성했다. DB/Caddy/키·다른환경보존·healthy/공개health200·분리검증14경계PASS다. 사용자가 반영 후 실제 로그인 성공을 보고해 [전체5번째 Backend · 사용자 인수 확인](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558340814)으로 기록했다. release 로그인 대기는 해소됐으며 추가 반복 요청은 없다. refresh·전체 기능 인수는 별도 미확인이다. 과거401/azp실패는[진단이력](../engineering/operations/records/lightsail-release-google-login-investigation.json)이며수정후성공과혼동하지않는다. 태그자동화설계는별도다.

## 현재 협의 — Native 릴리즈 방식·Backend 서버 반영 추적

[Issue34 전체1번째 Flutter · 운영 기준 회신](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558053848)을 확인하고 [전체2번째 Backend · 현재 사실 대조·최소 추적안](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558101459)으로 회신했다. Native v1.1.2/source9e4a18f7의 Actions 성공·APK/checksum 게시를 읽기 확인했다. 앱/Backend 독립 버전과 소스 통합·산출물 게시·실제 반영·사용자 인수의 4단계 분리에 의견이 일치한다. [대조·최소안](../engineering/operations/release-tracking-review.md)을 따른다. 현재 checkout은 `chore/release-management`이며 Native 운영 회신 대기는 해소됐다.

다음 담당은 Backend/사용자다. Backend 버전·태그/배포 방식은 위 확정 구현으로 진행하며 관리자 OIDC 준비와 첫 활성화가 남았다. Native release 브랜치 보존을 Backend에 자동 채택하지 않는다. 아래 최소안 회신 당시 CI/CD는 미실행이었으며 최신 구현/외부 준비 상태는 위 실행을 따른다. release 등록값 대조·운영 allowlist 반영은 위 기록으로 완료했고 게시 APK 실제 로그인은 사용자 확인 완료다. 전체 호환 기록/전체 기능 인수는 미확인이다. 기존 운영 source6154e45·이미지dfad04e8·DB0035/환경과 외부 백업 후속은 보존한다.

Git 통합 최신(2026-11-01): 사용자승인 [PR33](https://github.com/heo0328/lostparty-backend/pull/33)·병합`c0b13cc`로 Lightsail 구성·실제반영/인증보완·운영안내 기록을dev에통합했다. 현재checkout은dev이며main도후행통합기록을포함한최종dev와동일커밋으로맞춘다. 완료한chore/lightsail-deployment는원격게시/전체포함확인후로컬·원격정리대상이고미완료feat/activity-selection은보존한다. 아래작업브랜치표시는당시이력이다. 실제운영source6154e45/이미지dfad04e8·DB0035/환경/키·수동인증자료는이번Git통합으로변경하지않는다. 외부백업등남은운영후속은계속미완료다.

운영 참고 최신(2026-11-01): [짧은 운영 안내](../engineering/operations/lightsail-quick-ops.md)에 실제서버경로·상태/최근로그/API만재시작명령을정리했다. Docker부팅enabled·3서비스unless-stopped·로그10m×5실적용을읽기확인했으며실제재부팅/재시작은하지않았다. **서버외부DB/환경/키백업은미구성·전송완료미확인**이다. 다음운영작업은외부암호화보관위치/담당/주기·보관기간확정과키포함복원검증이다. [확인근거](DEV_LOG.md#lightsail-quick-ops)를따른다.

## 현재 실행 — Lightsail 첫 배포·로그인등록 보완·테스트 원정대 인증 (2026-11-01)

작업 구간: 신규 서버 설치·무료 주소 HTTPS 첫 배포 / 브랜치·checkout: `chore/lightsail-deployment` / 기본 프로젝트 경로. 실행 source는 `6154e459cbd8de7562c331eacc60928c61f8ac09`, API이미지dfad04e8·DB0035다. 후행 문서 커밋과 실행 소스를 구분한다. 아래 과거 checkout/dev 문장은 당시 이력이다.

- 공개 주소: **https://lostparty.duckdns.org**, 고정IPv4 `54.253.176.103`, 시드니 `lostparty-server`. Docker/API/PostgreSQL/Caddy를 실제 설치하고 신규DB0035·DB/APIhealthy·Let's Encrypt HTTPS/HTTP308·두 전체OpenAPI·공개조회/인증거절/no-store·8000/5432차단을 확인했다. 키4종은 신규서버 전용이며 기존 개발DB/키/Firebase/기기를 이관·변경하지 않았다.
- 테스트 원정대 수동 인증 완료: 사용자승인으로유일회원/유일미소유원정대의V2대기1개를수동처리했다. 별도새조회에서verified/owned·원정대1/캐릭터18·proof passed/verified·self를확인했고소유감사/수동테스트주석(actual_equipment_proof_passed=false)을보존했다. [집계](../engineering/operations/records/lightsail-manual-test-verification.json)·[이력](DEV_LOG.md#lightsail-manual-test-verification)을따른다. 실제장비증거인수/운영검증우회기능추가가아니며대표/활동은unconfigured상태다.
- 로그인 등록 보완 완료: 사용자승인으로확정debugAndroid ID한개를GOOGLE_AZP_ALLOWLIST에추가하고API만동일이미지로재생성했다(한국시간20:21:13). Web audience·다른환경·DB/Caddy·키보존, APIhealthy/공개health200·인증검증13경계PASS. [반영집계](../engineering/operations/records/lightsail-google-azp-rollout.json)·[이력](DEV_LOG.md#lightsail-google-azp-rollout)을따른다. 이전401/azp빈목록은진단당시이력이며실Google수정후성공은아직미확인이다.
- 비용: AWS API에서 Free plan ACTIVE·잔액$120·종료2027-05-01 한국시간18:26:57 확인. 플랜전환/추가유료리소스 생성없음, 기존22/80 규칙보존·IPv4TCP443만 추가했다.
- 검증/반영 상세 원본: [집계](../engineering/operations/records/lightsail-first-deploy.json)·[DEV_LOG](DEV_LOG.md#lightsail-rollout)·[운영 절차](../engineering/operations/lightsail-first-deploy.md). 위조XFF/Forwarded/다중hop에도 같은 출발지10회400→429, 다른 실제출발지400으로 IP제한분리를 확인했다. 실제 Google성공/refresh·로그인후그룹코드는 미확인이므로 F02전체완료는 아니다.
- 다음 사용자/Flutter: Google로그인성공사용자보고·운영회원1확인을수용해반복로그인을요청하지않는다. 현재원정대목록을새로고침해수동인증상태를확인하고대표/활동설정은기존흐름으로진행한다. 실제refresh·인증후그룹코드/기기확인은별도이며로컬개발DB를이관한것은아니다. 네이티브Issue추가댓글/요청은없다.
- 다음 운영: 초기DB덤프 생성/목록·격리PostgreSQL17복원(0035/115표) PASS. 서버밖 암호화 DB/환경/4종키백업·소유자/ACL포함전체복구·자동백업/알림·부하/장기관찰은 미완료다. 자동인증서갱신은 Caddy설정이며 미래갱신성공을 확인한 것은 아니다.
- DNS/고정IP/계정종료일 입력대기는 해소했다. 실제 배포는 이번 지시로 승인·실행됐으며 PR/merge·다른기능정책/Issue종료는 별도다. 분쟁 정책 협의는 아래 기록대로 보존한다.

문서 운영 #29는 공통 원본·양측 참조 반영 및 [상호 대조](https://github.com/heo0328/lostparty-backend/issues/29#issuecomment-6520322169) 완료로 추가 수정 대기를 해소했다. Issue 종료는 별도이며 상세 근거는 [DEV_LOG](DEV_LOG.md)에 보존한다. 기존 그룹 기기 인수와 기술 진단 후속은 별도다.

## 다음 실행 — 소유권 분쟁의 그룹·레이드 영향 정책 협의

사용자가 상세500 원인추적을 별도로 진행하지 않겠다고 확정했다. [#16 전체44/45 Flutter 탭 로딩보호·기기인수/통합](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6531439956)을 1차대응으로 수용하며 추가조사/재현·정상시험 요청은 중단한다. 과거 서버500의 원인은미확정이며 해결된 것으로 표시하지 않는다. [조사/중단 기록](../features/groups/detail-500-investigation.json)을 보존한다.

[분쟁 영향 검토](../features/rosters/ownership/dispute-impact-review.md)에 현재연결·보류가드와 미합의정책/Flutter5개검토항목을 정리했다. 원정대3개중1개상실의그룹활동/다른설정보존2PASS와기존동작4PASS를격리확인했다. 다음은 #15에서 Flutter와 최종이전의 자동정리/영향대상복구필요·그룹표시/공대장승계·예약정책을 협의하는 것이다. 사용자 제안은 검토 대상이며 일괄탈퇴·유저전체경고·자동참가 이전으로 확정하지 않는다. 실제자료/서버·계약은 합의 전 바꾸지 않는다.

현재 실행sourceb8542ef/이미지930c25f8·DB0035는 유지한다. 사용자 승인 [PR32](https://github.com/heo0328/lostparty-backend/pull/32)·병합e3a657a로 분쟁검토/합성시험·상세500조사/추적중단 기록을 dev에 통합했고 main도 dev의 후행기록 포함 같은커밋으로 맞춘다. 현재 checkout은 dev이며 통합된 feat/ownership-dispute-policy·fix/raid-detail-errors는 로컬/원격정리했다. 후속 정책협의·구현은 최신dev의 목적브랜치에서 이어가며 미완료 feat/activity-selection은 보존한다. F02 보류/F03 미착수·AWS/release·자료초기화·Issue종료와 구분한다.

## 보류 추적 — Backend 베타 개선

[F01](DEV_LOG.md#f01-registration-cleanup)은 `c94ce88`로 구현·격리 검증·commit/push 완료, PR31로 dev/main 통합하며 코드는 기존0035 이미지에 함께 반영됐다. 미처리 대상0·수동 정리 실행 없음은 [반영 기록](../engineering/operations/cycle-group-policy-rollout.md)을 따른다. [개선 계획의 F02 재개 조건](backend-improvement-plan.md#f02-resume)을 따른다. F02는 위 Lightsail 첫 배포와 실제 프록시 검증까지 진행했으며 실제 앱 인증/그룹코드 영향 확인이 남아 있다. 이전 생성 전·공개 경로 미정 보류 기록은 개선 계획에 보존한다. 테스터 총20~50명 예상이며 동시 사용자 보장은 아니다. F03 내부 장애 추적은 개선 복귀 시 다음 후보이며 미착수다. 그룹 작업을 막지 않는다.

## 이전0034 기준과 기존 변경의 기기 대기 (이력)

2026-10-30 기준, 그룹 브랜치는 dev/main 통합 후 로컬·원격 정리했으며 현재 checkout은 `feat/raid-group-policy`다. 기존 그룹 핵심 흐름·관리, 초대 후보 대소문자 검색·역할별 표시, 모집 최초 그룹 연결·목록 그룹명 표시까지 Backend 구현·검증·개발반영을 완료했다. main/dev는 그룹 병합 `fc6c06a`와 후행 통합 기록을 포함한다.

| 구분 | 확인된 기준 |
|---|---|
| 업무 구현·계약 | `6dac5ab2cc67e197979e7188a9c97ce2c27fb548` |
| 실제 개발서버 | source `2602e4595a868eebdf12b04e1fd51502142069b3` / 이미지 `5bd8dde6` / DB `0034_group_features` |
| 기존 게시 기록 | 반영 기록 `ad095c3`, 이슈 인계 링크 기록 `603fe2d`까지 commit/push 완료 |
| 문서 인계 | `48bf88c` 게시 및 PR30 dev/main 통합 완료. 문서/Git 통합과 실제 실행 소스는 구분한다. |

위 표는 이전0034 반영 당시 기준이다. 현재0035 실행은 위 다음 실행/반영 기록을 따른다. 실행 소스와 후행 문서 커밋을 구분한다. 이전 게시 이력은 유지하며 되돌리거나 재작성하지 않는다.

## 이전 계약 소비·기기 확인 대기 (새 #16 정책 요청과 구분)

[#12 전체40번째 Flutter · 목록/소속 표시 소비 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503895589)·[#16 전체26번째 Flutter · 최초 연결 소비 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503895060)를 확인했다. Flutter는 `feature/group-backend-integration`의 `5f024e536fbf4963a77903f7763b7ca460939a34` commit/push·local/origin 일치, 최초 연결 context/기존 PUT·목록 metadata·프로필별 배지 연결 완료를 보고했다. 이는 공식 Issue의 자체 보고이며 Flutter 로컬 소스는 읽지 않았다.

- Flutter 검증 보고: 전체 test 2,707PASS이며 직접 경계43PASS는 포함 수다. analyze 오류/경고0·기존 info3, 포맷/diff/review 완료다. Backend 시험과 합산하지 않는다.
- 기존 인계 대비 변경: Flutter 신규 계약 소비는 구현 완료 보고로 갱신한다. **당시 추가 API 변경이나 Backend 재검증 반복 요청은 없었다.** 이후 #16 전체27/28의 새 정책 정정은 위 다음 실행으로 별도 추적한다. 기존 그룹 정상 기기 인수는 유지한다.
- 다음 담당은 사용자 변경 경계 기기 확인과 Flutter 결과 대응이다. 일반 방 최초 그룹 연결, 같은 그룹 공개범위 왕복, 서버 그룹명/긴 이름, 비그룹원 시점 배지, 생성 선택 기본값을 확인한다. 실제 최초 연결 허용 context/명령 성공은 여전히 미확인이다.
- 비그룹원 배지 원 제보는 Backend/Flutter 합성 검사에서 미재현이다. 결함 해결 완료로 판정하지 않고 실제 기기 차이가 생기면 해당 응답/렌더링 위치를 좁혀 대응한다.
- Backend는 구체 차이가 회신되면 해당 경계만 수정·검증한다. 이전 계약의 동일 시험을 반복하지 않으며 새 #16 정책 설계는 별도 진행한다. 기존 회신 결과는 이번 진단 인계 구간에 함께 보존한다.
- Flutter의 Penpot03 갱신/시각 검수는 도구 미제공으로 대기한다는 보고이며 Backend API 추가 작업으로 확대하지 않는다. 새 기기 인수·운영배포·Issue 종료는 미완료/별도다. Backend Git 병합은 PR30으로 완료했다.

완료 조건은 연결된 새 앱의 변경 경계 기기 결과 확인이다. 이번 문서 인계에서는 Issue 변경/추가 댓글·서버/DB 작업은 하지 않는다.

## 유지할 검증·인수 근거

- [격리 검증 집계](../features/groups/raid-link-verification-2026-10-30.json): 신규/기존 회귀47PASS, 추가 경계4PASS, 토큰1PASS. 반복 합산 없이 선택49시나리오이며 전체 프로젝트 또는 동일 HEAD 일괄시험 결과는 아니다. 두 OpenAPI 전체 일치, 기본 객체·기존 schema 값 불변을 확인했다.
- [개발 반영 집계](../engineering/operations/records/raid-group-link-rollout.json): 교체 전후114업무표2,015행·sequence·설정·키·DB볼륨 보존, migration 없음. 소스274파일/runtime31·두전체계약·HTTP12·읽기전용 목록/프로필·worker·API/DB healthy를 확인했다. 이는 반영 당시 검증 결과이며 이번 문서 작업에서 서버 검증을 반복하지 않았다.
- 실제 context 샘플은 현재 G1/방 상태로 거절됐다. 긍정 경계는 격리 검증을 따르며 실서버 최초 연결 성공으로 표시하지 않는다. 실회원 변경 명령을 임의 실행하지 않았다.
- [#12 전체36번째 Flutter · 기존 그룹 사용자 기기 인수](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6502226347)·[#16 전체21번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6502226876)의 안내 범위 통과는 유지한다. 초대 검색/역할별 표시·기존 관리·필터/기존 참가 보존도 해당 보고 범위이며 새 최초 연결/표시 변경 인수로 확대하지 않는다.
- [#16 전체22번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6502336731)의 `9d1baa39` 생성 UI 기본값/기존 생성 API 1회·29PASS는 Flutter 자체 보고다. Backend 시험에 합산하지 않는다.
- 그룹원 동등 개설·실제T 공대장 관리를 유지하며 그룹장 전용 레이드 명령은 없다. 복구승계·활동 자동추가는 별도 미결정이고 로컬 활동 선택 브랜치 `89a3248`은 보존한다.

## 다른 미완료 주제

모집1차인수/Issue13종료는유지하고차후정밀도/알럿/UX/소켓은 [보완대장](../features/recruitment/follow-up-backlog.md)을따른다. 다른Issue상태는 [추적표](ISSUE_TRACKER.md), 완료/결정/검증·장애는 [DEV_LOG](DEV_LOG.md)에보존한다. IF-001/002/003 비활성·원자료/pending/ACK·별도성능/실회원원ACK 검증경계는유지한다.

상세조회500 조사 공식 회신: [#16 전체38번째 Backend · 현재미재현/추가근거 대조](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530073442). 조사기록1be55a7 commit/push·원격일치 완료, 다음 Flutter 당시기록 확인/Backend 후속대조이며 원인해소·Issue종료가 아니다.

후속 확인 회신: [#16 전체41번째 Backend HTTP 경계 대조](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530965340), 근거6279daf 게시/원격확인 완료. 과거입력 기록없음을 수용하며 다음은 자연재발근거 수신 후 표적대조다.

분쟁 협의 인계: [#15 전체10번째 Backend · 원정대별 그룹/레이드영향 검토](https://github.com/heo0328/lostparty-backend/issues/15#issuecomment-6541847499), 검토·시험7408ab0 commit/push·원격일치 확인. 다음 Flutter5항목소비검토/사용자정책확정이며 새API·실기기시험 요청이 아니다.
