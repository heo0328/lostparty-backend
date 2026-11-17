# 2.4.0 공동 운영 게시 기록

2026-11-18 B16: 공동 공개 후 사용자 “운영 정상적으로 작동합니다.” 확인 수신. 운영2.4.0/DB0038/웹2.4.0+9 정상 작동 인수 완료, 추가 사용자 확인/동일 시험 대기 없음. 개별 세부 동작 전수 확인으로 확대하지 않는다. 후행 문서 미커밋·미push이며 게시/병합·Issue 종료는 별도 지시 범위다.

2026-11-18 B15: Native 최종 게시 확인(전체30/6954801040)·사용자 진행 승인으로 기존 open 도구 성공. 고정 Backend2.4.0/source970b2f4·DB0038/웹2.4.0+9 재확인 후 maintenance 해제, public_open=true/journal succeeded. 서버 probe 및 외부 HTTPS /·/health 모두200. 다음은 사용자 운영 로그인·재등록 최소 실사용 확인/발생 문제 대응이다. 전체회귀·추가초기화 없음. 후행 기록은 미커밋·미push, Issue 종료 별도.

2026-11-18 B14: 승인된 최신 백업과 API 정지 후 최종 dump의 서버·로컬·PC 사본 일치를 확인했다. 운영 lostparty 앱 DB 전체 자료 초기화 및 Backend v2.4.0/source970b2f4·DB0038/고정 웹2.4.0+9 적용과 후보 점검을 완료했다. candidate_ready/public_open=false, 유지보수503 유지. 다음은 Issue59 Native 공동 공개 준비 회신과 최종 공개 지시 확인 후 open이다. 전체 회귀/새 CI는 실행하지 않았다. 후행 문서는 미커밋·미push다.

아래는 준비 당시 기록이며 현재 상태는 상단 B16과 운영 결과 원장을 따른다.

2026-11-17 / Issue59 / release/2.4.0. 사용자 배포 준비 재개 지시로 진행한다. Backend2.4.0 / Native2.4.0+9이며 현재는 로컬 준비다. commit/push·태그·Release/이미지 공개·운영 키 파일 공급 외 API/DB/웹 전환은 실행하지 않았다.

## 확정 기준과 포함 범위

- Backend 기능 source: main/dev/origin 일치18e6bb66283d1eb772c4eee2431eee92c1e25a62. VERSION/검증계획은 이 기준 위 미커밋 준비다. 최종 릴리즈 source/image digest는 아직 없다.
- 운영 기준은 마지막 확정 [2.3.0 원장](records/release-2.3.0-deployment.json)의 v2.3.0/source05daa42·DB0036·웹2.3.0+8. 이번 읽기전용 SSH 점검에서 같은 source/image·실제DB0036·API/DBhealthy·Caddy running을 재확인했다.
- 포함: 서버 단일 키/분석·저장, 공개탐색·로그인 경계, 개인표1분, 도화가 정식표기/호환, 신규1700 상세후보·실패/원본문복구·정책CAS/제외보존, DB0038 모집/현황 회귀복구.
- 현재 명세191경로/211동작·SHA256 12634daa64a8c4cbdfecfdb53bc7c1aca3bdb721c5ea555d098aea51544b9665. 개발image eadaa2cc…37b9는 개발 실행물이며 신규 GHCR 운영이미지로 인계하지 않는다.
- Native source/산출물은 Issue59 인계 기준을 따른다. 전체8 고정source84565024/version2.4.0+9·web14330277676/APK14330278091 최종성공/서명/hash 인계를 수신했다. Backend 독립수령/로컬 비활성 stage는 아래 B4 결과에서 완료했다.

## 자료 초기화와 전환 전제

사용자가 “운영중인 db 저장된 자료는 모두 초기화”로 운영 lostparty 앱 DB 전체 저장자료의 초기화 범위를 확정했다. 회원보존 여부 질문은 해소됐고 재질문하지 않는다. 현재는 배포준비이며 최신백업/복귀·전환절차를 먼저 준비하고 실제삭제는 별도운영반영 단계에서 수행한다. 기존0037 보호장치를 우회하지 않는다.

확정 대상은 운영 PostgreSQL의 앱 DB 하나다. 전체 초기화로 회원/세션·원정대/설정·그룹·모집/참가·주간/분석·명령 자료가 삭제되고 재로그인/재등록이 필요하다. 키·환경·PostgreSQL역할/볼륨·인증서·기존 웹/산출물은 보존한다. DB 전체를 선택해도 migration의 필수카탈로그/정책 seed는 정상 생성하며 모든테이블0행을 목표로 하지 않는다. 회원보존형 선별전환은 이번 범위가 아니다. 개발DB·외부Firebase·기기자료 삭제로 확대하지 않는다.

기존0037은 개인키/과거분석·캐시뿐 아니라 proof·모집assignment/application 등 관련자료가 있으면 DDL 전에 중단한다. 현재 일반 배포기는 운영DB revision과 새이미지0038이 다르면 manual_migration_required로 거절한다. 기존maintenance 도구는0035→0036 전용이므로0036→0038/초기화에 재사용할 수 없다.

따라서 현재 standard 태그 배포를 먼저 실행하면 안 된다. 확정된 전체초기화 범위로 검토된 게시/유지보수 실행 절차와 전환 리허설을 먼저 마련한다. 배포보호를 우회하거나 승인 없는 새maintenance 예외를 추가하지 않는다.

## 키·백업·복귀

사용자 용도 확정과 진행 지시로 현재 개발 서버용 키를 운영 `.secrets/lightsail/lostark-api-token`에 공급했다. 개인 회원키를 복호화/전용하지 않았다. 파일0600·기존 비밀파일과 동일 소유권·API 읽기/읽기전용 mount·기본 AUTH_SECRET_DIR 연결을 확인했다. 개발 키는 그대로 유지하고 별도 개발 키는 사용자가 차후 등록한다. 공급자 외부 인증/2.4.0 운영 실행은 미확인이다. 서버/로컬 제한 사본은 바이트 일치 확인, 개인 PC 백업 폴더 보관은 미확인이다. 값·Base64·토큰 해시는 출력/게시하지 않았다. 아래 B4와 [백업 원장](backup-and-recovery.md)을 따른다.

초기화 직전 최신 운영DB dump·환경/기존키·고정current/compose/복구도구·활성웹을 새날짜사본으로 확보하고 서버/로컬/PC hash·dump목차·파일무결성을 검증한다. 기존11월15일 백업을 현재최신DB로 간주하지 않는다. 로컬개발DB dump제외 결정을 운영DB백업 제외로 확대하지 않는다. [백업 기준](backup-and-recovery.md).

전환은 쓰기/공개노출을 멈춘 유지보수 구간에서 수행한다. 확정된 전체 앱DB 초기화는 백업 영수증 확인→구API정지→승인된 앱DB만 새구조 준비/0038까지 migration→필수seed/역할권한 확인→신API/고정웹 비공개확인→공동공개 순서로 계획한다. 실제 명령/잠금·복구 도구는 별도 준비 전 미확정이며 자동실행하지 않는다.

실패 시 구API2.3.0 이미지로만 되돌리면 안 된다. 초기화 이전0036 DB dump와 대응키/환경/구웹/동결구성을 함께 복원해야 한다. 새 쓰기 이후에는 그시점 이후 자료 유실/복구정책을 별도로 판단한다. 합성자료 격리DB의 실제dump/restore·구API복원 리허설은 완료했고, 실제운영최신백업과 이를 이용한복원·운영용최종apply도구는 미실행이다.

## 구 APK·공동 공개

v2.3.0 대비 현재명세에서 개인키 GET/PUT/DELETE·restore, 역할요약 PUT, role-summary-batches POST 총6동작이 제거됐다. 구 APK가 이경로를 사용하면404가 발생할 수 있어 전체호환을 보장하지 않는다. 초기화 시 기존세션도 무효화된다. Native에2.4.0 업데이트/재로그인·재등록 안내, 구버전 동작/업데이트 유도 경계를 대조 요청한다. Backend가 강제업데이트 기능을 새로 넣었다고 표시하지 않는다.

고정 APK/웹 인계 전 임의웹 활성화 없음. 서버2.4.0/신웹 검증과 APK공개 시점을 유지보수·업데이트 안내와 조율한다. 기존공개 asset을 덮어쓰거나 Issue를 닫지 않는다.

## 검증·남은 완료 조건

release-validation.json: version2.4.0/mode full/baseline v2.3.0/tests=[]로 준비했다. protected app/main·migration·공통권한/reader/writer 변경이 있어 selected/reuse 예외는 적용하지 않는다. 기존 dev136/하위13·모집67 및 Native/사용자 근거는 당시기능검증이며 이번full릴리즈 성공으로 바꾸지 않는다.

릴리즈계획 파싱 PASS, 배포/검증/maintenance/웹 도구68시험 PASS. 첫 unittest 호출은 시험경로 설정으로2 import오류가 있었고 PYTHONPATH=scripts/tests로 보완한 정규 호출이68PASS다. 기능full회귀/고정운영이미지/신규릴리즈CI는 아직 미실행이다.

다음: 실제운영apply절차·백업도구 호환 설치·초기화직전최신백업/복귀확인·full검증·고정image·공동 전환. 키 공급/서버·로컬 사본과 Native 파일 수령/로컬 stage는 B4에서 완료했다. 최종 배포가능/공동공개 준비완료로 표시할 단계는 아니다. 원격게시/태그·운영반영은 별도 사용자지시 범위다.

[Issue59 전체2 Backend B2 초기화범위확정](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6948402246)에 회신했다.

## 1·2단계 선행 결과 — 운영 점검과 Backend 격리 리허설

운영기준실측: API2.3.0/source05daa42·DB0036·정상, 배포진행journal0·여유공간약55GB. 회원3·세션10·개인키2·분석18·assignment11·application0을집계로만확인했다. 실제자료/환경/키/서비스를변경하지않았다. 초기화직전최신백업이필요하며 지금 최신운영백업을만든것은아니다.

리허설도구 scripts/deployment/rehearse_reset.py는 운영host/DB명 인자를받지않고 고유내부네트워크·lostparty_test/tmpfs·합성키만사용한다. 초기화직전마다 컨테이너namespace/서비스/임시저장소/외부port·bind/volume부재를검사한다. scripts/tests/test_rehearse_reset.py에서외부/영구target거절을검증했다. Docker의db별칭/health역할·tmpfs표시형식을리허설에맞춘초기시도2건은실패로남기고최종PASS에합산하지않았다.

최종 실제실행: 구운영동일digest2.3.0기동→합성0036/회원·세션·개인키·원정대seed→0037가드차단및원행보존→custom pg_dump/목차검증→테스트앱DB초기화/0038전체생성→회원/세션/원정대0·역할/합성키보존·새APIhealthy→테스트DB에dump복원→118개테이블의모든행지문일치·0036/구APIhealthy. 외부provider호출0, 임시container/network/volume정리완료. 기존개발API/DB도재기동없이healthy유지했다. 후보는현재작업트리시험이미지이며최종공개GHCR이미지가아니다.

[비민감 실측/리허설집계](records/release-2.4.0-readiness.json). 도구검증70PASS(기존68+격리안전2), 문서/diff검증. 합성복원을실제운영덤프복원·Native웹원자전환·신규full릴리즈시험으로확대하지않는다.

Native전체6에서사용자가개발DB초기화뒤재로그인/재등록·전체기능정상을이미확인했다고정정했다. 이를인수완료로유지하며새회원UUID증명/같은정상흐름재시험을추가요청하지않는다. Native전체7웹인계 source84565024/version2.4.0+9/artifact14330277676을수신했으나Backend독립다운로드/비활성stage는다음단계다. 후행전체8에서APK/artifact14330278091도최종success·서명/hash검증완료로인계됐다. Backend검증과구분한다.

다음은운영용lostark-api-token파일/별도사본준비, 검토된실제운영apply절차·초기화직전최신백업, full릴리즈검증/고정image·Native산출물수령검증과공동전환이다. 사용자이번승인은1·2단계이며실제운영초기화/서버교체/키쓰기·공개/태그는실행하지않았다.

[Issue59 전체9 Backend B3 선행점검/리허설결과](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6948893337)에 회신했다. 소스/문서는 release/2.4.0 미커밋·미push다. 운영키 부재와 남은절차를 해소하기 전 공동배포가능으로 표시하지 않는다.


## B4 — 승인 키 공급·고정 산출물 독립 수령

사용자 진행 지시와 Native 전체11의 키 용도 결정을 적용했다. 고정 서버용 키만 SSH stdin으로 전달하고 argv/env·로그로 내보내지 않았다. 운영 API/DB/Caddy 컨테이너 ID·시작 시각, current source/image·DB0036, 기존 키/환경 무결성은 유지했다. 운영 API는2.3.0을 계속 실행하며 새 토큰 파일을 읽을 수 있는 것과2.4.0 활성화를 구분한다. 새 키 생성·개발 키 변경/삭제·provider 호출은 없었다.

복구용 새파일은 서버 `/home/ubuntu/lostparty-backend/backups/release-2.4.0-server-token/lostark-api-token`, 로컬 `backups/release-2.4.0-server-token/lostark-api-token`이다. 디렉터리0700/파일0600·원본과 바이트 일치를 확인했다. 서버/WSL 사본이며 사용자의 기존 개인 PC 백업 폴더/외장 매체 보관으로 표시하지 않는다. 사용자는 로컬 사본을 기존 비공개 백업 폴더에 별도로 보관한다. 기존 사본/키는 보존한다.

기존 백업도구는0036에 미리 공급한 token을 거절하고0038도 미지원했다. 로컬 backup.py에0036의 기존 필수키+선택token,0038의 필수token+선택과거암호화키를 명시 허용했다.0035/알수없는revision/필수키누락/예상외파일 거절은 보존한다. 운영 설치 도구는 변경하지 않았으며 최신 DB 백업 전 검토된 호환 도구 설치가 필요하다. 이번 키 사본은 DB/전체 복구구성 백업을 대신하지 않는다.

Native 원장 f2f1b75932f3debfd62787a3d7155d7b3c89ee70에 고정된 source84565024/version2.4.0+9를 독립 수령했다. GitHub 연결 도구로 원장/메타데이터를 조회하고 기존 로컬 gh 수령기로 원본 ZIP을 보관했다. web14330277676/APK14330278091의 run/source/만료·외피 digest, 원장5파일의 크기/해시·checksum을 확인했다. 웹은 원3파일과 내부manifest 동일성·34자산·파일경계·운영origin·clean/release/service_worker disabled를 검증하고 로컬 비활성 stage만 생성했다. AWS 업로드/웹 pointer전환은 없다. APK는 원본/ZIP CRC를 확인했으며 로컬 apksigner/aapt가 없어 서명·패키지/버전 재검증은 하지 않았다. Native의 동일 원본 서명검증 보고를 별도 근거로 유지한다. [수령 원장](records/web-handoff-2.4.0.json).

도구72PASS(기존 선택 도구군과 백업 허용/거절 행렬 포함), 문서/diff 검증. 실제운영 초기화/서비스재시작/태그·Release공개/commit·push는 없으며 새full릴리즈 검증/고정이미지·실제apply/최신백업·공동전환은 남았다.

[Issue59 전체12 Backend B4](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6949412430)로 결과를 회신했고 다음 담당은 Backend다.

## B5 — 게시 경계와 운영 전환·백업 준비

release-deployment.json을 publish-only로 고정했다. 향후 승인된 태그 게시가 산출물을 생성하더라도 워크플로의 standard 전용 deploy 조건은 거짓이며 운영 자동전환은 하지 않는다. 기존0035→0036 maintenance 도구를 재사용하지 않는다. 계획의 revision/version/웹원장 조합이 다르면 거절한다. 로컬 경계/백업도구19시험 PASS.

운영 실행 순서는 다음과 같다. 고정 release source/image/계약0038과 웹 원장을 확보→deploy.lock과 미완료journal 확인→기존 도구/상태를 보존하고 backup.py만 호환 설치→최신 DB/키/환경/current/활성웹 백업·PC사본 검증→공개 maintenance503 확인→구API와 모든 writer 정지·DB연결 확인→정지시점 최신dump/행snapshot 재확보→대상 lostparty 앱DB만 재생성(기존역할/볼륨 보존)→고정 후보로0038 migration/seed·권한/빈회원세션 확인→신API만 기동→loopback 계약/health/인증경계 확인→고정웹 전환/비공개 점검→공동확인 후 공개 순이다. 명령을 실행할 최종 관리자 도구와 고정이미지는 아직 준비 전이며 이 순서 자체를 실행완료로 표시하지 않는다.

초기화 이후 실패하면 maintenance를 유지하고 신API/writer를 정지한다. 정지시점0036 dump를 앱DB에 복원하고 대응키/환경·구current/compose·웹pointer를 함께 회복한 뒤 구2.3.0 API/계약/health·행snapshot을 비교한다. 새자료가 작성된 뒤에는 덮어쓰지 말고 자료유실 범위를 먼저 판단한다. dump목차검증은 실제 복원 성공과 구분한다.

운영 백업/PC복사/backup.py설치를 묶은 실행은 자동 승인 검토에서 거절됐으며 실행되지 않았다. 이유는 운영DB·키·환경의 민감 payload와 별도PC 목적지/운영도구 설치에 대한 명시적 승인 부재다. 재실행하지 않고 승인 대기로 남긴다. 대상은 /home/ubuntu/lostparty-backend/backups/의 새날짜 준비사본, 로컬 ignored backups/ 및 이전 검증된 개인PC 백업폴더의 새하위폴더, 설치파일 /usr/local/lib/lostparty-deploy/backup.py다. 실제DB초기화/서비스교체는 이 승인 대상에 포함하지 않는다.

계약 전체객체191경로 일치 PASS, Docker API교체/복귀·Caddy 합성유지보수 PASS. 전체회귀는 실행 중이며 초기14ERROR가 확인됐다. 최소재현으로 tests/core/test_current_runtime.py가0037을 준비하면서 현행0038 readiness에서 거절됨을 확인해 fixture만0038로 수정했다. 수정후 표적검증과 전체회귀 최종결과는 아직 확인 중이다.


### B5 승인 후 실제 백업·설치 결과

사용자가 자동검토 거절 이후 제시된 서버/로컬/기존PC 백업·backup.py만 설치 범위에 진행을 명시 승인했다. 이전 거절은 이번승인으로 해소됐으며 DB초기화/서비스교체 승인으로 확대하지 않았다. 첫시도는 운영backup.py 부재에서 중단, 재시도는 maintenance 의존모듈 부재에서 중단했다. 당시 설치된 도구는 server.py/common.py/ssh_entrypoint.py뿐이었다. 기존도구를 보존하고 backup.py를 신규 설치했으며 기존 backup.py를 교체했다고 표시하지 않는다.

backup.py는 단독 설치 가능하도록 maintenance.require 의존을 내부검증으로 정리하고 활성웹 원3파일을 읽는 최소 검증을 내장했다. 예상외pointer/누락원본/버전형식 거절과 기존 revision/키목록 검증은 유지한다. 현재 경계/백업20시험 PASS. 운영 설치파일 SHA25647ed4ebab5f61b5b05263eb2d1f821410952c4aff30f358c1d701680c4e86cfd를 확인했다.

서버 사본: /home/ubuntu/lostparty-backend/backups/release-2.4.0-preparation-20261117T135434Z/before-tool-install/backend-production.tar. 로컬: backups/release-2.4.0-preparation-20261117T135434Z/backend-production-before.tar. 기존 PC 비공개 백업폴더에 같은 새날짜하위폴더의 backend-production-before.tar와 lostark-api-token을 보관했다. 정확한 개인PC 경로는 ignored 로컬 receipt.private.json에만 남겼다. 사용자가 별도로 같은토큰을 다시 복사할 대기는 해소됐다. 내장SSD 사본이며 외장매체/암호화/정기백업 완료로 확대하지 않는다.

운영0036 최신dump·목차866항목·키/환경/고정current/복구도구/활성웹 원본을15165440bytes 묶음으로 보관하고 서버/로컬/PC 아카이브 SHA256 및 내부복구원본을 모두 검증했다. 서비스 ID/시작시각·키/환경/current와 운영2.3.0/DB0036 유지. source05daa424f06aa34edd76867bac1c78f9d558b51a/image71e30188…834d9d. 설치 전 기존도구를 포함한 준비백업이며 실제전환 직전에는 정지시점 최신dump/갱신백업이 다시 필요하다. 이번운영덤프 실제복원은 실행하지 않았다. [비민감 영수증](records/release-2.4.0-preparation-backup.json).

수정한 current-runtime fixture14PASS. 최초full 회귀는 계속 진행 중이고 초기14ERROR를 포함하므로 전체통과로 기록하지 않는다. 운영전환 관리자실행도구·최종full/고정이미지·실제전환은 남았다. commit/push/태그·공개 없음.

[Issue59 전체14 Backend B5](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6950099720) 결과 회신. 정적전체92PASS·문서/diff PASS.


## B6 — 회귀 실패 보완·관리자 전환도구 로컬 구현

reset_release.py에 preflight→prepare(공개503/API정지/연결0/정지dump)→PC사본확인→apply→rollback/open 분리 흐름을 구현했다. source/태그/이미지/head/계약/Compose·기존current·키/환경·정지dump/행snapshot·1시간신선도·정확한DB/역할·명시초기화확인을 검사한다. 미완료journal은표준배포를차단하고 DB삭제에는FORCE를사용하지않는다. 초기화이후실패는503유지·구API자동재기동금지, 복구는정지dump/전체행일치뒤구API복원이다. 새회원/공개후덮어쓰기는거절하고 공개는별도공동수용기록이필요하다. [실행안](release-2.4.0-reset-runbook.md)·[검증영수증](records/release-2.4.0-reset-preparation.json). 운영설치/실행은하지않았다.

차단/실패격리·준비/적용/복귀순서19시험과정적도구111PASS. 관리자CLI+Caddy전체경로 통합시험/고정image는아직이며, 동일초기화SQL만기존UUID/tmpfs리허설에매핑한실제0036→0038→0036복원은PASS다. 구/신APIhealthy·118테이블모든행일치·역할/합성키보존·임시자원정리, 외부provider호출0/운영접속0을확인했다.

회귀에서발견한시험설정은앱동작을변경하지않고수정했다. current-runtime fixture0037→0038 14PASS, 구0037실행허용기대와0019 합성일정의5분단위/주간경계불일치 두파일15PASS, 수요일00:05표시시험의실제30분floor충돌은판정시각고정후1PASS, 개인표후보시험의6시간표+2시간출발gap이점검시간과겹치는경우는같은주차play구간으로합성창을이동해1PASS다. 과거migration/동결원문·API/업무코드는수정하지않았다.

최초직렬전체회귀는이미완료한앞83파일구간과실패로그를보존하고중단했다. 남은27파일은4개의서로다른UUID/tmpfs프로젝트로분리실행중이다. 최초2FAIL/14ERROR·추가각1FAIL은수정후재검증결과와별도이며겹치는시험수를합산하지않는다. 전체수집110파일/1927항목에대해누락파일을대조하며, 새커밋의깨끗한full CI성공으로표시하지않는다. 최종종료결과는후행기록을따른다.


### B6 종료 결과 — 로컬 회귀 범위/실패 재검증

전체수집110파일/1927항목의파일집합을앞83파일과후행27파일로대조해누락0을확인했다. 최초직렬로그는14ERROR/2FAIL을포함한중단기록이며성공종료가아니다. 후행4구간의원결과는134PASS/5FAIL,161PASS/2FAIL,150PASS,72PASS/1FAIL이다. 원실패를성공으로덮지않고수정후각표적결과를별도보존했다. [회귀근거](records/release-2.4.0-local-verification.json). 겹치는PASS를합산해1927단일실행PASS라고표시하지않으며고정커밋full CI는남았다.

총8개시험파일의설정을보완했다. 앞선DB0037불일치/5분단위·주간경계/수요일00:05 floor/개인표점검시간 외에, opening floor+6h가주차끝을넘는경우·예약출발이달력다음주인데현재주를조회하는경우·개방미리보기의생성시점30분floor와고정00:05 충돌을고쳤다. 수정후current-runtime14PASS, 이관/실행guard두파일15PASS, resume1PASS, 분단위1PASS, 고정floor1PASS, 예약파일16PASS, 개방표시매개변수6PASS. 알려진실패대기0이며애플리케이션/명세/migration변경없다. 로그는ignored backups/release-2.4.0-verification/에보존했다.

최종전환SQL리허설은 recreate와private_snapshot을모두호출해118테이블행보존/0036복원/구APIhealthy,0038새APIhealthy를확인했다. 임시자원정리·운영접속0·합성자료만사용. 전환도구차단/실패격리/순서19PASS, 정적도구111PASS·문서/diff PASS. 전체관리자CLI+Caddy통합검증과고정release source/image·새커밋full CI·실제전환직전백업/공동공개는남았다. 새도구운영설치/DB초기화/서비스재시작/commit·push/태그·Release공개는없다.

[Issue59 전체16 Backend B6](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6951724684)로 결과 회신/본문상단 최신화 완료. 다음 담당은 Backend이며 Native 새구현/동일시험 대기는 없다.


## B7 — 2026-11-18 전체 CLI/API/DB/Caddy 통합 검증 완료

관리자 도구 main/argparse·고정source/clean Git검사·deploy.lock·journal을 그대로 호출하는 reset_smoke.py를 추가했다. 도구의source확인에는새임시시험Git저장소를사용하고, root UID/후보이미지참조/프로젝트표식/운영health URL은검사된UUID합성환경에만매핑한다. 실제PostgreSQL/API/Caddy·현재고정Native웹34자산과실제운영Dockerfile을사용했다. 게시포트/외부네트워크없는internal network·tmpfs DB·합성5키뿐이며운영접속/프로젝트commit/push/공개이미지생성은없다. 임시시험commit/이미지는운영release source/GHCR digest가아니다.

세흐름을통합확인했다. (1) dirty source/비관리자/정지dump PC확인전apply 거절→migration실패주입뒤503/API정지유지→정지dump0036복원/모든행대조/구웹복원→별도승인구운영재개. (2) 빈0038·신API/고정신웹이준비된후에도공개503유지→rollback으로0036/구웹복원·명시재공개. (3) 다시0038/신웹준비→다른source의공동승인거절→공개probe실패주입시503재차단→일치하는공동승인으로최종공개/health·catalog200/me401·새웹HTML바이트일치. 기대한오류코드까지대조했고실제mount된합성키5개/환경·DB/Caddy동일성과자원정리를확인했다. [통합영수증](records/release-2.4.0-reset-integration.json).

복원후접속재개를명확히하기위해 open-restored를추가했다. 구current/source/image·0036·키/환경·구웹pointer·loopbackhealth와별도구버전승인기록을검사하며실패하면유지보수로돌린다. 이는운영에서복원을실행한것이아니다. private_snapshot은psql의식별자/리터럴quoting과gexec로생성SELECT만실행하고전체테이블을한READ ONLY/REPEATABLE READ트랜잭션으로대조한다. 기존테이블별별도연결의시점차와반복Docker호출을줄였으며실제통합복원에서동일행을확인했다.

초기전체흐름시험과추가경계시험도PASS했고, 최종운영Dockerfile·단일읽기snapshot·엄격오류코드/실제구·신웹바이트검사까지PASS다. 관리자도구22시험+UUID대상거절1시험=23PASS, 정적전체115PASS(포함관계로합산안함). API/업무/migration/계약변경없으며새기능full회귀를재반복하지않았다. 이전B6회귀근거와원실패/재검증구분을유지하고고정커밋full CI를대신하지않는다.

남은게시경계: release/2.4.0 누적변경은미커밋·미push다. 사용자commit/push지시후기준source를고정하고릴리즈full CI/불변GHCR이미지·Release를확보해야한다. release-validation full과release-deployment publish-only를유지하므로태그게시가승인돼도운영자동전환은없다. 실제운영반영은새백업/정지dump·독립PC확인/공동전환승인범위에서수행하며현재운영2.3.0/0036은유지한다. 이번에운영도구설치/키·환경/DB자료/서비스교체를하지않았고새키백업이나같은PC복사를요청하지않는다.

[Issue59 전체18 Backend B7](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6952581457) 회신과본문상단갱신을완료했다. 다음은사용자게시지시후Backend 기준source/고정이미지확보이며Native새작업대기는없다.


## B8 — 승인 source게시·수동full CI

사용자명시승인으로누적34파일을release/2.4.0 source5e0ee12e897e35f01dcf73f40eee351a15649d52에commit/push하고원격일치를확인했다. 로컬정적115PASS/비밀패턴·문서/diff검사와소스커밋직후clean을확인했다. 수동full CI [44117486823](https://github.com/heo0328/lostparty-backend/actions/runs/44117486823) source일치실행중이며최종성공은아니다. 수동분기는public publish/deploy를건너뛰고runner로컬빌드만검증한다. [전체20 Backend B8](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6952946626)·[CI영수증](records/release-2.4.0-ci.json). merge/태그/Release·이미지공개·운영반영은이번승인제외로미실행이다. 후행문서는검증source와구분해기록한다.


## 원full CI 결과와 시험시계 보완

2026-11-18 CI후속: 원full CI44117486823/source5e0ee12는7개회귀성공·6번1FAIL(216PASS/2subtests),verify성공·validation실패/publish·deploy skipped다. 수요일점검과충돌한명시출발시험의시계를조회/명령/reconcile모두일치하도록고정해표적1PASS·파일전체11PASS(46.30s). 앱/API변경없음. 동일승인게시/CI구간에직접필요한시험보완/기록만최소게시후새source수동full CI를실행한다. merge/공개/운영은제외다.

명시출발자동후보시험만현재주차의플레이가능한동일합성시각을사용하도록보완했다. 실제시각은그대로두고늦은화요일now+6h로수요일점검창을만들던설정이원인이었다. cycles.now/admission snapshot의now/함수내import하는database.now와최종evaluate시각을일치시킨다. 모의관측/테스트자료만변경하며30분기한/실제점검거절정책은보존했다. 원full성공증거artifact0이며새고정source의full검증이필요하다.


## B10 — 사용자지시검증수용·전체재시험중단

2026-11-18 B10: 사용자지시로전체재실행44120909602 cancelled확인·기존7회귀/verify성공+보완파일11PASS수용. 2.4.0한정reuse원장/source조상/후행변경허용목록연결을로컬구현해관련도구21시험PASS·실제근거해석PASS/새회귀0. 원failure/cancelled는보존하며전체CI성공으로표시하지않는다. 추가변경미커밋·미push/새CI·merge/공개/운영전환없음.

이절이이전full대기상태를대체한다. 원run은failure/후행run은cancelled, 검증판정은사용자가기존통과+보완파일11PASS를수용했다. release-validation.json은2.4.0한정reuse로전환해고정수용원장SHA/051895a→3836eea→게시source조상·후행변경허용목록을검사하고기존기능회귀를다시실행하지않는다. 새정적/근거검사만수행하며신규회귀파일목록은빈목록이다. version2.4.1등에는적용하지않는다. [고정수용원장](records/release-2.4.0-accepted-validation.json)·[B10회신](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6953722160). 이번추가변경미게시,후속게시/태그/운영은지시범위에따른다.


## B13 — Backend산출물 게시완료·실제운영전환전

2026-11-18 B13: 사용자승인v2.4.0태그/Release/불변이미지게시완료. source970b2f430138b95d837305ffc576eb9cbc605cb0·image3e7dcdc5…74adb07·DB0038. publish-only run44125843614 success/deploy skipped, reuse/new_tests_executed=0 확인. 다운로드원본manifest/validation/Compose·익명GHCRdigest·태그source일치검증PASS. 전체회귀재실행없음/운영2.3.0/0036유지. [게시영수증](records/release-2.4.0-publication.json).

[Release](https://github.com/heo0328/lostparty-backend/releases/tag/v2.4.0)와불변image `ghcr.io/heo0328/lostparty-backend@sha256:3e7dcdc5dd8ad954a1f6ca00b098a1d246144c9d0664a7d5224d467d074adb07`를사용한다. 검증은원failure/cancelled를보존한사용자수용근거reuse이며GitHub전체시험성공으로표시하지않는다. 필요한정적/근거검사후publish성공,deploy skipped다. 실제운영은여전히2.3.0/0036이며사용자반영지시후직전백업/정지dump·PC확인/명시apply·비공개검증/공동open이남았다.
