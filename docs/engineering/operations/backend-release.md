# Backend 태그 기반 Lightsail 배포

작업 목적은 승인된 고정 릴리즈와 실제 운영 반영을 연결하는 것이다. [Issue34](https://github.com/heo0328/lostparty-backend/issues/34)에서 Native와 합의한 독립 버전·4단계 추적을 따른다. 구현 브랜치는 `chore/release-management`이며 첫 버전은 `VERSION`의 `0.1.0`이다. OpenAPI의 버전과 별도다. 기존 APK release Google 로그인 사용자 인수는 보존하며 다시 요구하지 않는다.

## 실행 경계

목적 브랜치→dev→main 통합과 완료 브랜치 정리를 유지하고 release 브랜치는 추가하지 않는다. 사용자가 승인한 `vMAJOR.MINOR.PATCH` 태그 push가 운영 배포 승인이다. 태그와 VERSION 일치·main/dev 동일 SHA·태그 소스의 main 포함을 **최초 산출물 게시 전** 검사한다. 뒤에 main/dev가 전진해도 게시된 Release 재실행은 원래 태그/source/digest를 재사용한다. GitHub의 태그 update/deletion 규칙이 공개 태그 이동/삭제를 막는다.

`.github/workflows/backend-release.yml`의 실행은 다음과 같다.

1. 정적·스크립트 테스트, 격리 Docker 교체/복귀, 두 계약 전체 비교, 전체 격리 pytest gate를 8개 비중복 파일 그룹으로 병렬 실행한다. 운영 DB나 비밀을 사용하지 않는다.
2. Linux amd64 이미지를 GitHub 표준 runner에서 빌드하고 `ghcr.io/heo0328/lostparty-backend:sha-<source>`와 `:<tag>`로 게시한다. 소스·버전 태그는 기존 digest와 다르면 덮어쓰지 않는다. 조회 실패를 이미지 없음으로 취급하지 않는다. 중간 실패 후 같은 SHA 이미지는 재빌드하지 않는다.
3. GitHub Release의 `release.json`과 `compose.lightsail.yaml`을 고정한다. draft로 생성/첨부 후 게시한다. 불완전 draft는 자동 덮어쓰기하지 않으며 운영자가 원인/게시 복구를 검토한다. 코드 수정은 새 버전이다.
4. production 환경 작업에서 배포 전용 SSH 계정/키와 API로 확인해 고정한 호스트키로 접속한다. 서버의 AWS CLI·GitHub runner나 AWS access key는 필요하지 않다. 개인키는 GitHub production Secret에 보관한다. GitHub 환경 Deployment 상태와 Actions summary에 실제 결과를 남긴다.
5. 서버는 digest 이미지를 pull한 뒤 API만 교체한다. DB/Caddy/네트워크/볼륨·API 환경/명령/mount 등 image/build 외 Compose 변경은 사전 거절한다. DB revision 불일치도 교체 전에 거절하며 `alembic upgrade/downgrade`는 호출하지 않는다.

수동 workflow_dispatch는 검증과 이미지 **로컬 빌드까지만** 실행한다. GHCR/Release 게시·운영 SSH 접속/반영은 하지 않는다. 추가 merge·태그·Release 발행은 사전 준비만으로 승인됐다고 해석하지 않는다.

## 일회 준비와 현재 활성화 상태

GitHub production 환경은 reviewer/wait 없이 `v*` **태그만** 허용한다. 환경 Secret은 `LIGHTSAIL_DEPLOY_SSH_KEY`, 변수는 `LIGHTSAIL_SSH_KNOWN_HOSTS`다. 서버 주소/계정은 `54.253.176.103` / `lostparty-deploy`로 고정한다. GitHub 환경/태그 정책 입력 JSON은 `scripts/deployment/`에 보관한다. 미사용 AWS_DEPLOY_ROLE_ARN 변수와 workflow의 id-token 권한은 제거했다. 기존 SSH 방화벽은 변경하지 않는다.

**인증 방식 변경 근거:** 초기 확정안은 OIDC였지만 실제 IAM 호출은 조직 SCP explicit deny로 거절됐다. 공식 [새 AWS 가입 방식의 관리 정책](https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html)은 iam:*Provider*를 제한한다. [고급 기능 활성화](https://docs.aws.amazon.com/accounts/latest/reference/activate-advanced-features.html)는 계정 업그레이드가 필요하므로 현재 Free plan 유지와 맞지 않는다. 사용자에게 원인을 설명하고 **전용 SSH 키 방식으로 변경하는 명시 승인을 받았다.** 별도 관리자를 찾는 방식으로 해결된다고 안내한 초기 추정은 정정했다. OIDC 역할/provider는 생성하지 않았고 계정 업그레이드·정책 우회도 하지 않았다.

배포 전용 계정은 암호가 잠겨 있고, root 소유 authorized_keys의 `restrict`·강제 명령으로 셸/PTY/에이전트·TCP 포워딩을 허용하지 않는다. 강제 명령은 `submit`, `preflight`, `status <run>-<attempt>`만 받고 제한된 sudo 명령으로 root 소유 배포 도구를 호출한다. 사용자 홈/키 파일을 root 소유로 두어 배포 키로 허용 명령을 바꿀 수 없다. 개인키는 Git에 넣지 않으며 production Secret에 암호화 저장했다. key rotation은 새 키 준비→전용 명령 검증→Secret 교체→이전 키 폐기의 별도 승인된 운영 작업으로 진행한다. 운영 env/인증 키/DB는 이 SSH 키와 다르다.

`bootstrap_server.py`는 관리자 SSH에서 검토한 코드·public key·기존 설치본 expected hash를 stdin JSON으로 받아 root 도구와 전용 계정/최소 sudoers를 준비한다. 개인키를 서버에 보내지 않는다. 기존 계정/authorized_keys/sudo 정책이 다르면 덮어쓰지 않는다. 실제 키로 preflight 성공·일반 명령/포워딩 거절을 확인했고, 키와 임시 관리자 인증의 로컬 복사본은 작업 종료 시 제거한다.

GHCR 신규 package는 기본 private일 수 있다. 최초 게시 후 소유자가 package 설정에서 이 package를 public으로 전환해야 한다. workflow는 **익명 digest 조회가 성공하기 전에는 Release 완료/운영 배포로 넘어가지 않는다.** 첫 게시가 이 지점에서 멈추면 public 전환 후 같은 run을 재실행해 기존 소스 이미지를 재사용한다. package public 전환은 현재 도구로 미확인이고 첫 태그는 아직 발행하지 않았다. 이미지는 공개 소스/런타임만 포함하며 `.env`·인증 키·백업/개인정보를 넣지 않는다. GHCR/Actions 요금과 공개 여부가 바뀌면 운영자가 다시 검토하며 유료 runner·AWS ECR/S3 등은 추가하지 않는다.

서버에는 root 소유 `/usr/local/lib/lostparty-deploy/{server.py,common.py}`와 비공개 `/var/lib/lostparty-deploy`를 준비했다. bootstrap은 현재 API image ID·실행 source·DB revision과 root만 읽는 해석된 Compose를 동결해 초기 복귀 기준으로 보존한다. 운영 checkout과 `.env.lightsail`·4종 키·DB/Caddy·서비스 시작 시각을 바꾸지 않았다. 설치 스크립트 자체의 변경은 별도 검증/승인된 준비 작업으로 반영하며 일반 릴리즈가 임의로 교체하지 않는다.

## 서버 결과·복귀·재실행

서버 단일 flock과 GitHub `concurrency`의 `cancel-in-progress: false, queue: max`로 배포를 직렬화한다. queue 한도는 GitHub 정책을 따르며 한도 초과는 무조건 배포 성공으로 취급하지 않는다. 서버 systemd transient unit은 SSH/runner 연결과 독립 실행한다. 현재·직전 정상 이미지와 릴리즈 파일은 보존하고 전체 Docker prune/volume 삭제를 실행하지 않는다. 더 오래된 로컬 이미지도 자동 삭제하지 않으며 디스크 3GiB 미만이면 중단해 운영자가 배포 전용 자료 정리를 검토한다.

각 요청은 GitHub run ID/attempt로 구분한다. 같은 attempt에 다른 입력은 거절하고 완료 결과는 다시 실행하지 않는다. 이전 in-progress journal이 프로세스/호스트 중단으로 남았으면 기존 정상 API를 복구하고 이전 시도를 실패로 종료한 뒤 새 시도를 검증한다. 이전보다 낮은 version의 신규 배포는 거절한다. 자동 복귀는 journal에 보존한 이전 image/Compose로만 수행한다.

교체 시작 전 이전 정상 정보를 기록하고 API만 `up --no-deps --no-build --pull never --force-recreate --wait`한다. 120초 내 healthy와 공개 HTTPS `/health` 200/database ok, 공개 raid-catalog 200, 미인증 `/v1/me` 401을 확인한다. API 환경/mount·비밀 파일 bytes/소유/권한과 DB/Caddy container ID/start/mount도 비교한다. 실패하면 이전 API로 복귀하고 같은 health를 확인한다. 복귀 성공도 릴리즈 실패다. DB downgrade/자료 복구는 수행하지 않는다.

서버 확인 명령:

```bash
sudo python3 /usr/local/lib/lostparty-deploy/server.py status RUN_ID-ATTEMPT
sudo systemctl status lostparty-deploy-RUN_ID-ATTEMPT
```

status는 비밀 없는 결과만 출력한다. `current.json`·동결 Compose·전체 inspect/env는 출력/게시하지 않는다. 설정·키 변경은 기존 별도 승인 절차로 진행하고, 운영 기준과 configuration revision을 함께 갱신한 후 배포 baseline 재정렬이 필요하다. 일반 코드 배포가 환경파일/Google 허용 목록을 덮어쓰지 않는다.

배포 manifest는 tag/source/image digest·DB revision·두 고정 OpenAPI SHA256·Compose SHA256·빌드 UTC를 포함한다. 서버 journal은 configuration revision, 실제 API 시작/완료 UTC, 검증 결과·복귀·previous good·run 링크를 추가한다. `.env` hash나 비밀 원문은 공개하지 않는다. 사용자 인수는 자동 health와 분리한다. API 동작·공개 버전 endpoint는 추가하지 않는다.

## 검증과 다음 실행

구현/실제 준비·검증 진행 상태는 [준비 집계](records/backend-release-preparation.json)를 따른다.

- 제어 단위 시험: 태그/버전, DB·구성 불일치, 이미지 실패, unhealthy/복귀 실패, 낮은 버전, 중단 journal 복구, 중복·다른 attempt, OS flock 배제, 비밀 값 제외.
- `python3 scripts/deployment/docker_smoke.py`: UUID 로컬 Docker 환경에서 실제 API 교체·unhealthy 복귀·DB/Caddy 보존. 애플리케이션 DB/공개 HTTPS·실 Google 인수는 이 시험에 포함하지 않는다.
- `python3 scripts/verify_isolated.py static`, `contracts`, `all`: 별도 프로젝트/tmpfs PostgreSQL만 사용한다. 기존 0023 메타데이터 비교 테스트가 0031에서 대체된 unique constraint를 누락한 문제는 복사한 테스트 metadata에만 원래 제약을 복원했다. 운영 모델/migration은 변경하지 않았다.
- actionlint1.7.12는 새 queue 필드를 아직 인식하지 못하므로 해당 진단 하나만 제외하고 나머지 검사를 실행했다. queue:max는 [공식 workflow 문법](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)에 대조했다.

다음 순서: 검증된 작업 구간 dev/main 통합 승인 → 수동 workflow 검증 → 사용자 승인 첫 v0.1.0 태그 → 최초 GHCR public 접근 확인/필요시 같은 run 재실행 → 실제 GitHub Secret/자동 배포 결과 확인. 현재 실제 운영은 source6154e45/image dfad04e8·DB0035이며 후행 구현/문서 commit과 다르다. 외부 백업 미구성은 별도 미완료이고 migration 자동화의 선행 해결이 필요하다.
