# 다음 실행

2026-11-13 KST 기준. 실제 Backend 코드/Git과 각 담당의 현재 코드 확인 결과를 사용한다. Native 코드 상태·완료 판단은 Native가 작성하며 Backend가 대신 검토하지 않는다.

## 사용자 결정 — 기존 유저 데이터 초기화 허용

2026-11-14 사용자 정정: 운영을 포함한 모든 DB 초기화는 실행 전에 반드시 사용자에게 대상·영향을 제시하고 명시 확인을 받아야 한다. 임의 실행하지 않는다. 기존자료 보존 때문에 구조/기능을 추가할 필요는 없다는 설계 기준은 유지한다. 기존 유저 자료 보존 때문에 추가 호환구조/기능을 만들 필요는 없다. 이번 개발 설계는 이를 기준으로 단순화한다.

이는 지금즉시 초기화를 실행한 결과가 아니다. 실제 필요 시 DB별 대상테이블/인증·세션·관련참조·앱pending/cache 영향과 실행/검증순서를 구체화한다. 키·환경·DB볼륨 삭제/외부Firebase·기기 저장소 삭제까지 승인된 것으로 확대하지 않는다. 기존 기본정렬·원터치/원자성·동시조작 등 제품 UX와 현재 계약협의는 데이터보존과 구분해 유지/재검토한다.

## 내 계정 리메이크 — Issue53 구현·게시 인계

feat/my-account-contracts에서 사용자 지시로 합의 계약을 구현·격리 검증하고 로컬 dev API를 반영했다. [구현/검증/실행 근거](../features/rosters/activity-and-presentation/my-account-reservations-implementation.md)·[실행 OpenAPI](../../openapi/openapi.yaml).

- 현재앱 전용 GET /v2/me/raid-reservations. 신규16+기존 일정HTTP3=19PASS, 추가 실제 동시쓰기snapshot1PASS(중복사례 구분), 두 전체계약/기존path·component 보존·문서검사PASS.
- 로컬 API image7aaba198…fffa63·DB/환경/포트/mount/키 보존. health200/예약401·생성계약/앱292파일 일치. 실제 회원 화면/Native 소비는 미확인이다.
- 다음 Native: 게시 고정SHA와 실행 계약을 소비해 DTO/조회·한정재시도/페이지·영역오류/기존availability·원pending 영향 확인. Penpot/시안·실기기 범위는 담당자 단계와 구분한다. Backend는 구체 소비차이에 대응한다.
- 사용자 승인 commit/push는 작업 브랜치 범위, dev/main 병합·운영 배포·Issue 종료는 하지 않는다. 운영은 추가 개발 후 별도다. 업무/계약 fe5e0824c28f58025af201d6ef66d8289229ae60 push·원격일치 확인. [전체9 Backend 구현 인계](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6856983342) 게시·댓글순번 확인. 후행 게시기록은 같은 브랜치에 보존한다.

## Issue53 — 캐릭터 관리 즉시 저장 추가 협의

[전체10 Native 요청](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6859431815) 수신. 사용/대표는 즉시 저장, 순서는 드롭 후 한 요청·한 트랜잭션 원자 저장을 요구한다. 저장버튼/대표 확인창 제거·화면유지·대표우선/대표OFF금지·최소1명 보존은 Native 확정 UX다.

다음 Backend: 기존 character-settings/representative의 버전·자격·초기 unconfigured 첫 명시조작 재사용 대조, 순서 원자 계약 유무/최소 확장안·scope/전체·subset·비활동/신규/누락 순서·CAS/멱등/동시조작·원ACK 보존을 조사해 회신한다. 이번은 계약 질의이며 API/DB 구현 승인이 아니다. 기존 예약 GET 구현/게시·로컬 반영은 유지한다. Native 순차 personal-preferences 저장의 부분성공을 최종안으로 권장하지 않는다.

## 운영 오류 조사 — Issue52

사용자 지시로 조사·시험·협업 기록 a790cbe를 dev dc5aab0086b81be20f8c5dfb1c8b34f4b9cfa5d6에 이력 보존 병합·push하고 원격 일치를 확인했다. 현재 checkout은 dev이며 완료 목적 브랜치는 정리한다. [조사·계약 근거](../features/recruitment/membership-actions/issue52-investigation.md).

- [전체6 Native 구현·검증](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6847142336): 합의한 선택T 표시/정책/cursor 소비 수정 연결, 직접10파일266PASS(기록27)/변경4파일 분석0은 담당자 보고다. Backend 기존 API/DB/OpenAPI 유지, 기존 회귀61/최종 합성5PASS를 재사용한다.
- [전체7 Native 사용자 확인](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6847809202): 기록 표시·새로고침·상세·주차/탭 왕복 dev 정상 보고. 더 보기/다중 페이지는 자료 부족으로 수동 미확인이고 합성 통과와 구분한다. 자료 생성/삭제·반복 재현은 요청하지 않는다.
- [전체8 Backend 수신](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6847918619) 게시·실제순번 확인. Backend 추가 코드/재검증 대기는 없다. Backend 게시/통합 완료. Native Git 게시는 담당자 회신으로 확인한다.
- 운영 웹/APK는 미반영이며 사용자가 추가 개발 후 일괄 배포하기로 결정했다. 최초 상세GET403은 과거 ACK 후보 재현/실제 원인 증거 부족을 유지한다. Backend는 main 변경·운영 배포·Issue 종료를 실행하지 않았다. 이후 전체9 Native가 사용자 승인으로 Issue52를 completed 종료한 상태를 확인·보존했다. [전체10 Backend 게시 결과](https://github.com/heo0328/lostparty-backend/issues/52#issuecomment-6848125719). 운영/더 보기 수동 미확인·과거403은 후속 릴리즈 기록으로 보존한다.

## Issue51 — Backend API·웹 운영 완료 / Native Android 공개 대기

- Backend2.2.0/source c31d90da·imagecc753718…406dae·DB0036, 고정웹2.2.0+7/source994db44a·ZIP517166ca를 일반 공개했다. Actions43274053529 success·실제HTTPS/API와34자산hash/두생성계약 확인 PASS.
- 설치common/server 선갱신·구/신메타데이터preflight PASS. 기존118표 전체 COPY행·DB/Caddy컨테이너/키·환경·mount 보존. 직전/반영후 백업과 기존PC폴더 사본hash를 확인했으며 실제복원과는 구분한다.
- [전체5 Backend 운영 결과](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6831720284) 게시/전체순번재조회, 본문상단현재상태갱신. **다음 담당 Native:** 같은source Android2.2.0 Release 공개와실제게시파일/서명/hash 확인. Backend는그회신확인 후 협의기록연결. 사용자재시험/제한접근요청없음. Issue는OPEN유지.
- dev/main은배포sourcec31d90da까지동일push, 현재release/2.2.0의후행기록을통합·게시해보존한다. 태그/이미지소스는불변이며기록수정으로재배포하지않는다.
- [실행/복귀](../engineering/operations/release-2.2.0.md)·[실제집계](../engineering/operations/records/release-2.2.0-deployment.json)·[웹원본](../engineering/operations/records/web-handoff-2.2.0.json).

## Issue50 마감 완료 / 다음 업무 선택

- 사용자지시로최종문서011375bf를커밋하고Backend업무558ee6da와함께dev `0dc381ae646fba062f008d26c58b20e653a6de67`에이력보존병합·push/원격일치확인했다. Issue50은2026-11-12T14:52:57Z(KST23:52:57) completed종료다. [전체14 Backend 마감](https://github.com/heo0328/lostparty-backend/issues/50#issuecomment-6826988036). 당시checkout은dev, 완료작업브랜치feat/recruitment-discovery는로컬/원격에서정리했다.
- Native최종dev83a55020·담당자보고2927PASS/analyze0·사용자필터성공보고/Penpot02통합과Backend13최종점검으로합의기능/협업완료를확인했다. 추가Native작업·자료/기기인수·계약확인대기는없다. [구현/검증](../features/recruitment/search/discovery-implementation.md).
- 업무/시험/계약bytes는기존검증/로컬image87a918db…5c0bd·DB0036과같아재시험/재반영을반복하지않았다. main/운영/DB·키변경은없으며전수기기/신청/성능인수완료로확대하지않는다.
- 후속선택한실행정리는위와같이완료했다. 기존#17정리후보와#15/#18/#19보류범위는아래그대로보존하며자동착수하지않는다. 마감결과기록은dev후행문서커밋으로보존한다.

## 공동 릴리즈 마감 완료

- **완료:** Backend2.1.1/source d16734d·image7aa19edf…c061d·DB0036/config lightsail-web-2.1.0 일반공개, 실제웹/새APK인수·Native최종v2.1.0 Release 및Backend공개5파일동일성검증까지완료했다. [배포·백업·최종공개/마감 원장](../engineering/operations/records/release-2.1.0-deployment.json).
- **마감:** 사용자 “마감 진행합니다” 지시로최종9문서를동일목적브랜치에서커밋·dev이력보존통합/main동일화·push하고작업브랜치를정리했다. #49는2026-11-12T08:57:44Z에completed종료했다. 실제Git게시/정리SHA근거는[#49 마감 댓글](https://github.com/heo0328/lostparty-backend/issues/49)에연결한다. 운영배포태그/이미지·코드·DB/키·접속정책은변경하지않는다.
- **추가 대기 없음:** Native회신·반복기기인수·재빌드/재압축·재배포요청은없다. 백업사본/무결성과실제복원시험·정기자동화는별개이며후자를이번마감의새조건으로붙이지않는다.
- **다음 업무:** #50은위와같이마감했다. 기존순차정리후보#17은아래보존범위에서별도선택한다. #15/#18/#19의미합의계약·자료/DB수정은자동착수하지않는다.

## 별도 보류 — 기존 기능 이슈 정리

- #47 묶음 선택 완료와 #48 복구 안내/일정 읽기는 사용자 지시로 **completed 종료**했다. 추가 구현·계약 확인·동일 시험 대기는 없다. [완료 색인](ISSUE_TRACKER.md#completed)·[개발 이력](DEV_LOG.md).
- 공동 릴리즈 이후 선택할 순차 정리 대상은 [#17](https://github.com/heo0328/lostparty-backend/issues/17)이다. 완료 오류/기존 계정 복구는 사용자 인수·양측 dev 통합 완료다. 누락/부분 완료 자료와 해당 기기 경계·원래 생명주기 요구는 별도 남아 있다. Native가 현재 코드 기준으로 최신화한 본문과 Backend 구현을 구분해 잔여 범위만 정리한다. 지금 자료 생성·DB 조정·반복 기기 시험을 시작하지 않는다.
- **#15·#18·#19의 다음 작업 선택은 전체 정리가 끝난 뒤로 보류한다.** 장기 계약/미구현 요구는 [이슈 추적표](ISSUE_TRACKER.md)에 보존한다. 자동 착수·미합의 계약 추가는 없다.

## 현재 코드·게시·실행 기준

| 구분 | 확인 기준 |
|---|---|
| checkout/배포 소스 | dev(구현 8a54c485 / 병합 e1e81b76, 미push) / 배포소스d16734d·v2.1.1 고정, #49당시최종문서는dev/main동일통합 |
| 이전 #47 업무 통합/원격 | 업무44eb4ba·반영 기록624ef00·문서962c1cd9321328f19a8e1ea6b5071fa07380782b를 dev에 이력 보존 병합·push. 원격 병합 SHA 일치/전체 feature tip 포함·동일 tree 확인. app/tests/openapi422파일은 기존 검증 코드와 동일 |
| 로컬 dev | runtime image sha256:170d3a2505963e37…3601bb / 현재 앱·DB0036·앱291파일/두 계약·실HTTP/보존 PASS. [근거](../engineering/operations/records/runtime-consolidation-local-rollout.json) |
| 전체 계약 | 현재192경로/213동작(openapi.yaml), legacy125경로/142동작(legacy.openapi.yaml). 정확한 hash는 [구현/계약 근거](../features/recruitment/completion-and-records/batch-completion-implementation.md) |
| 후행 통합 기록 | 현재 브랜치/게시 상태·기능 브랜치 정리 결과는 dev의 후행 문서 커밋으로 보존. 업무 코드/시험/계약 변경 없음 |

이전 #47 구간에서 사용자 지시로 Backend dev 병합·push를 완료하고 feat/raid-batch-completion을 로컬/원격에서 정리했다. main·로컬 서버·운영은 당시 #47 통합에서 변경하지 않았다. 이후 새 게시/병합/배포는 별도 지시 범위다. 실제 개발 DB의 행 수는 사용자 테스트로 변할 수 있으므로 반영 시점의 건수를 현재 고정값처럼 사용하지 않는다.

## 담당별 후속을 구분

Native #47 게시47a30dad, #48 후속 lib/test/문서의 미커밋·미push·dev 미통합은 Native 담당 보고다. 두 이슈의 승인 범위 연결/추가 구현 없음도 Native 확인에 따른다. Penpot 디자인은 Native 차후 후속이며 종료된 이슈의 대기 조건이 아니다. 미보고 기기 경계·후속 갱신/레드닷·웹소켓을 이미 완료로 확대하지 않는다.

<a id="runtime-consolidation-followup"></a>

## 실행 구성 단일화

사용자 승인으로 위 현재 작업에서 구현·검증·로컬 반영을 완료했다. [현재 구현/유지 조건](../engineering/development/runtime-configuration.md)·[당시 조사](../engineering/development/runtime-consolidation-review.md)·[개선 대장](backend-improvement-plan.md#runtime-consolidation)을 연결한다. 과거 코드 전체 삭제·운영 반영 승인은 포함하지 않는다.

<a id="recovery-backup-closeout"></a>

## 환경·백업 보존

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 키/환경 사본·운영 기준본을 재사용한다. 로컬 DB dump 제외 방침과 실제 복원/정기 자동화·외장 매체 미확인 상태는 그대로다. 새 백업/키 생성·자료 삭제 요청은 없다.

이전 실행/협의 경과는 [최신화 직전 기록](../archive/project/status-before-refresh-20261110/NEXT_WORK.md), 완료/결정·검증은 [DEV_LOG](DEV_LOG.md)를 따른다. 현재 상태를 과거 문단 위에 반복 누적하지 않는다.

## Issue53 — 즉시 저장 계약 조사 회신 완료

[전체11 Backend 조사·추천](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6859755753) / [제안 원본](../features/rosters/activity-and-presentation/character-management-immediate-save-proposal.md). 기존v1 character-settings는 ON/OFF·대표·최초명시설정을 한 명령으로 처리 가능. 전용대표API는 메인원정대 전용이라 일반관리 대체에 부적합. 순서 원자저장은 없어 기존v1을보존한v2 character-settings GET/PUT 통합확장을 추천한다. 대표 표시우선/rank분리·활동-대표 제외subset 슬롯치환·비활동 상대순서 보존·settings CAS+order_digest/원ACK·직렬수명 후보를 제시했다. 다음 Native 추천안/UX 소비대조, 수용후 정확DTO·상한/검증 고정. API/DB 구현·시험·게시지시 아님. 조사문서 미커밋·미push, 기존 예약API 실행은 유지한다.

## Issue53 — 전체12 Native 부분 수용·기존 기본정렬 보존 확인

[전체12 Native](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6859935888)가 v2통합·대표표시/rank분리·movable subset·CAS/멱등·직렬수명을 방향수용했다. 미해결1건: 실제 기존 기본정렬은 대표→rank/null후순위→itemLevel내림차순/null후순위→characterName→UUID라서 전체11의rank/UUID 기본안은 기존배치를 바꾼다. 다음Backend는 최초GET/ON·OFF/대표변경의무쓰기없이 기존정렬·첫드롭실제목록과지문/관측경계를 보존하는최소안을 정리한다. 정확DTO·문맥지원량/활동200구분·오류/nullable/생략vs빈배열·eligibility·옛ACK/확정GET/no-op도후속고정. 구현/게시지시가아니며기존예약API유지.

## Issue53 — 전체13 기본 정렬·계약 보완 회신

[전체13 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6860182946) / [보완 원본](../features/rosters/activity-and-presentation/character-management-sorting-contract.md). rank→level내림차순→이름→UUID로Native기본정렬을보존하고GET/ON·OFF/대표변경·동일드롭은rank를쓰지않는다. 실제드롭은같은RR canonical 문맥/level·이름 포함지문으로슬롯치환한다. 전체문맥1000/활동200분리·closed scope/data·eligibility/옛ACK현재GET/no-op후보정리. 다음Native comparator/정확DTO·상한소비대조. 초기화필요없음/실행안함,추후필요시사용자확인필수. 추가문서미커밋·미push.

## Issue53 — 전체14·15 Native 후보 수용/정확 산출물 요청

[전체15 Native 다음단계 요청](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6860661505) 확인. 전체14로 정렬/통합v2·상한·CAS/원ACK·초기화금지 후보는 수용됐으며 이전정렬질의는 해소됐다. 다음Backend는 GET/성공PUT·PUT본문/오류의 JSON Schema·합성예시, decimal/UTF-16(null·동률·비ASCII·비수치/비유한)비교fixture, unconfigured/needs_reconfiguration의외부잔여activity/대표·usable/blocked_reason 집합불변식을 고정한다. 게시SHA/경로·신규API미구현/로컬미지원과구분해인계한다. 현재단계는계약산출물이며업무/API/DB구현·초기화승인아님. Native는저장중잠금 단일write lane·원요청복구·409명시재시도/화면유지 설계, 기능미구현이다.

## Issue53 — 즉시 저장 정확 Schema/예시 작성·전체16 회신

[전체16 Backend](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6860769177)에 [계약 산출물](../features/rosters/activity-and-presentation/character-management-contract/README.md)의 정확Schema/완전합성예시·오류/전이/comparator내용을직접첨부했다. GET은모든state의잔여활동/대표를허용하고characters목록집합과저장설정집합을분리한다. PUT의현재자격은엄격검사한다. 문서38사례PASS, 실제서비스/DB/Native시험은아니다. 다음Native 정확산출물/복구문맥·비교fixture 대조. 파일미커밋·미push/고정SHA없음, 신규관리API미구현/로컬미지원, 개인예약GET은기존지원유지.

## Issue53 — 전체17 Native 정확 산출물 최종 수용

[전체17 Native](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6860821836)가 댓글Schema/예시/comparator를직접파싱·대조해설계를수용했다. 미해결질의/추가제품결정없음. 다음은별도승인범위의Backend 계약파일게시·v2관리GET/PUT구현/검증·실행인계, 이후Native DTO/명령수명/일반DI연결/연동검증. 정확산출물은현재미커밋·미push이며신규관리API미구현/로컬미지원. 기존예약GET지원과구분한다. 초기화는불필요·사용자사전확인없이실행금지.

## Issue53 — 즉시 저장 구현/로컬 반영 완료 (미게시)

[구현 원본](../features/rosters/activity-and-presentation/character-management-implementation.md): 신규관리GET/PUT·원자선택/대표/순서·정확정렬/문맥·CAS/지문/원ACK/no-op 구현. 신규26+기존대표35=61PASS, 문서40사례/두전체계약·기존path/component보존PASS. 로컬API image7e77c078…d937b4/app295파일·생성명세일치/health200·관리401, DB/키/환경/포트/mount보존. 실제dev회원설정쓰기/Native UI성공과구분한다.

신규코드·계약파일은미커밋·미push이며원격고정SHA없음. 다음사용자게시지시후고정계약인계, Native는별도승인범위내DTO/명령수명·일반DI연결/연동검증. 이번구현지시로commit/push·merge/운영배포·이슈종료는하지않는다. DB초기화불필요/미실행·사용자사전확인필수.

- [전체18 Backend 구현/검증·로컬반영 결과](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6861363598) 게시·실제순번확인. 신규관리코드는미게시로원격소비완료라고인계하지않았으며사용자게시지시후고정SHA연결. 이후Native 승인범위연동검증,이번commit/push·merge/운영배포없음.

## Issue53 — v2 관리 게시 완료

업무/정확계약 026a74fa67c36d72fb9d6d94d8bafcf707d4ffe9 commit/push·원격일치/clean확인. [전체20 Backend 고정인계](https://github.com/heo0328/lostparty-backend/issues/53#issuecomment-6861435507). 신규관리미게시대기는해소됐다. 다음Native 고정파일대조/승인범위DTO·명령수명/일반DI연동검증이며실제회원/기기결과는미확인이다. 후행게시기록도동일브랜치에보존한다. dev/main 병합·운영배포·DB초기화/Issue종료는실행하지않는다.
