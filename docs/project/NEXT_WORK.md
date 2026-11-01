# 다음 실행

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
