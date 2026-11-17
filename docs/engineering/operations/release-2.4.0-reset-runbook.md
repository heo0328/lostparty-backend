# 2.4.0 운영 앱DB 초기화 전환·복귀 실행안

Issue59 / release/2.4.0 / 준비 코드. **이 문서는 실행 기록이나 운영 반영 승인이 아니다.** 운영은2.3.0/0036을 유지한다. 관리자 전환도구의 합성 CLI/API/DB/Caddy 전체 격리 검증은 [B7 영수증](records/release-2.4.0-reset-integration.json)에서 완료했다. 실제사용 전 최종 게시 커밋·GHCR digest/full CI·운영반영/공동 공개 승인을 확보한다. 기존0035→0036 maintenance.py를 실행하지 않는다.

## 대상과 필수 전제

- 정확한 대상은 lostparty-lightsail 프로젝트의 PostgreSQL 앱DB `lostparty` 하나다. 회원/세션 포함 전체 앱자료를 초기화하며 재로그인·원정대 재등록이 필요하다. PostgreSQL역할/볼륨·키/환경·인증서·기존웹은 보존한다. 외부Firebase/개발DB/기기자료는 대상이 아니다.
- 전환은 관리자 SSH 전용이다. 제한 배포계정/일반HTTP/CI에서는 reset_release.py를 호출하지 않는다. `release-deployment.json`은 publish-only이고 자동deploy를 차단한다.
- 실제실행 시에는 고정release.json의 source와 HEAD가 일치하는 깨끗한 소스 checkout, 고정이미지/계약·Compose hash, Native 고정 원본이 필요하다. 미커밋 현재 작업트리는 실행 대상이 아니다. 환경/키를 새로 만들지 않는다.
- 기존3도구 보존 및 backup.py 단독설치·준비백업/PC사본은 완료했다. 준비백업은 [영수증](records/release-2.4.0-preparation-backup.json)을 따르며 전환직전 최신백업을 대체하지 않는다.
- 공개503을 확인한 뒤 API를 정지한다. API외 PostgreSQL 연결이 하나라도 남으면 초기화하지 않는다. DROP에 FORCE를 사용하지 않으며 예상외 연결은 원인을 확인한다.

## 명령의 경계와 순서

아래 경로 변수는 고정된 실제 release checkout/다운로드 manifest/웹 원본으로 관리자가 설정한다. 비밀값을 변수/명령행에 넣지 않는다. `LP_RELEASE_ROOT`는 소스 root, `LP_MANIFEST`는 GitHub 고정 release.json, `LP_HANDOFF`는 검증된 웹 원3파일 디렉터리, `LP_BACKUP_RECEIPT`는 전환직전 백업의 비공개 영수증 경로다. 이 변수 설정은 서버 .env를 변경하지 않는다.

1. 읽기전용 preflight(고정이미지 pull은 수행)로 운영source05daa424·tag2.3.0/0036·구성 lightsail-web-2.1.0·API DB대상/역할/이미지/환경/키mount/웹root·health를 확인한다. 후보는 schema2/v2.4.0/head0038만 허용한다.

   ```bash
   sudo python3 "$LP_RELEASE_ROOT/scripts/deployment/reset_release.py" preflight \
     --release-root "$LP_RELEASE_ROOT" --manifest "$LP_MANIFEST"
   ```

2. 새날짜의 DB+키/환경+current/compose/기존도구/활성웹 백업과 기존PC사본을 검증한다. dump목차·원본무결성과 실제복원은 구분한다. 백업은1시간 이내이고 현재키/구성/이미지와 같아야 한다. 기존 source/키/서명자료를 덮어쓰지 않는다.
3. `prepare`는 고정웹을 비활성stage하고 후보Compose를 생성한다. deploy.lock 아래 비공개journal을 만든 뒤 maintenance파일→공개503확인→구API정지→연결0확인→정지시점dump/모든테이블행snapshot 순으로 수행한다. 이 명령은 서비스를 중단하므로 실제 운영반영 승인과 유지보수 구간이 필요하다. DB삭제는 아직 없다.

   ```bash
   sudo python3 "$LP_RELEASE_ROOT/scripts/deployment/reset_release.py" prepare \
     --release-root "$LP_RELEASE_ROOT" --manifest "$LP_MANIFEST" \
     --handoff "$LP_HANDOFF" --backup-receipt "$LP_BACKUP_RECEIPT"
   ```

4. `/var/lib/lostparty-deploy/reset-2.4.0/stopped.database.dump`를 로컬/기존개인PC의 새날짜 비공개 폴더에 보관하고 PC에서 독립 계산한 SHA256을 비교한다. journal/키지문·dump·개인PC경로를 Git/Issue/로그에 올리지 않는다. 실제사본 확인 전 `confirm-stopped-backup`을 실행하지 않는다. `LP_PC_DUMP_SHA256`은 토큰해시가 아닌 dump아카이브의 비민감 무결성값이다.

   ```bash
   sudo python3 "$LP_RELEASE_ROOT/scripts/deployment/reset_release.py" confirm-stopped-backup \
     --release-root "$LP_RELEASE_ROOT" --manifest "$LP_MANIFEST" \
     --pc-dump-sha256 "$LP_PC_DUMP_SHA256"
   ```

5. `apply`는 명시적인 전체자료 초기화 확인문구·1시간 이내 정지dump/PC확인·키/구성/current/DB행불변·API정지/연결0을 다시 검사한다. 앱DB만 DROP/CREATE하고 기존역할에 schema권한을 부여한다.0038 migration→빈회원/세션/원정대→새API/계약전체·401/loopbackhealth→고정웹 바이트검증을 거친 뒤 current를 확정한다. **공개503은 유지한다.**

   ```bash
   sudo python3 "$LP_RELEASE_ROOT/scripts/deployment/reset_release.py" apply \
     --release-root "$LP_RELEASE_ROOT" --manifest "$LP_MANIFEST" \
     --acknowledge reset-production-lostparty-all-users-and-sessions
   ```

6. 실패 시 추가전환을 중단한다. journal의 reset_started 이후 구API만 재시작하지 않는다. `rollback`은 공개이전/maintenance상태에서만 사용하며 새회원이 있으면 자동복원을 거절한다. 새쓰기 발생 후 자료유실 판단은 별도다. 구0036 dump복원/전체행snapshot일치→구웹pointer/구API/DBrevision/health→구current 복귀 순이고 유지보수503을 유지한다. 초기화시도 전에 실제DB가 불변이면 불필요한 재삭제/복원을 생략한다.

   ```bash
   sudo python3 "$LP_RELEASE_ROOT/scripts/deployment/reset_release.py" rollback \
     --release-root "$LP_RELEASE_ROOT" --manifest "$LP_MANIFEST" \
     --acknowledge reset-production-lostparty-all-users-and-sessions
   ```

   이전 버전 복원 후 접속 재개도 별도 결정이다. 구 API/DB0036·키/환경·구웹pointer/loopbackhealth·current가 복원 기준과 일치하는지 다시 검사하고, 구 backend_source·구 web_sha256을 담은 공동확인 기록으로 `open-restored`를 사용한다. probe실패면503을복구한다. 기존구버전 정상인수 근거는 재사용할 수 있으며 같은Native시험을새로요청하는절차가아니다.

   ```bash
   sudo python3 "$LP_RELEASE_ROOT/scripts/deployment/reset_release.py" open-restored \
     --release-root "$LP_RELEASE_ROOT" --manifest "$LP_MANIFEST" \
     --joint-acceptance "$LP_RESTORED_ACCEPTANCE"
   ```

7. 공동확인·최종공개 지시 이후에만 `open`을 호출한다. 비공개joint-acceptance.json은 정확히 backend_source·web_sha256·backend_checks=true·native_checks=true·joint_publication_authorized=true를 포함한다. 기존 개발인수를 운영실기기 시험으로 바꾸지 않고 각확인의 근거를 구분한다. 공개전 candidate/계약/웹을 다시검사하고 공개후probe실패면 maintenance파일을 복구한다.

   ```bash
   sudo python3 "$LP_RELEASE_ROOT/scripts/deployment/reset_release.py" open \
     --release-root "$LP_RELEASE_ROOT" --manifest "$LP_MANIFEST" \
     --joint-acceptance "$LP_JOINT_ACCEPTANCE"
   ```

## 구현·검증의 한계

현재 reset_release.py는 로컬 구현이며 운영에 설치/실행하지 않았다. 오류 차단/순서/실패격리/복구/재공개 및 일관된읽기snapshot22시험과, 동일 초기화SQL을 UUID/tmpfs 합성DB에만 매핑한0036→0038→dump복원 리허설을 수행했다.118테이블 모든행일치·신/구APIhealthy·역할/합성키보존·임시자원정리를 확인했다. 이후 B7에서 실제운영Dockerfile 기반 합성이미지와 CLI/API/DB/Caddy의 세가지 전체흐름도 검증했다. 실패주입복구/0038후보복구/최종공개 및 공개probe실패 재차단을확인했다. 비관리자/dirty source·PC미확인·공동승인불일치의정확한오류코드와실제구/신웹HTML바이트·mount된합성5키도검증했다. source/UID/이미지참조·운영URL은UUID합성환경어댑터이며 운영에접속하지않는다. 이는 실제운영dump복원/고정커밋full CI/GHCR불변이미지/운영반영완료는 아니다. 최종출시 전 고정 source/image와 승인 범위를 확인한다. [준비 원본](release-2.4.0.md).
