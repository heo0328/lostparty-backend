# Lightsail 첫 배포 준비

2026-11-01 사용자 요청 기준. 작업 구간은 **Lightsail 신규 서버 설치·HTTPS 준비**, 브랜치는 `chore/lightsail-deployment`다. 최신 main `6151fa0`은 dev `ac0526f`를 포함하며 프로젝트 소개 수정까지 보존해 분기했다. 이 문서는 실행 절차이며 AWS 설치·공개·운영 인수 완료 기록이 아니다. 로컬 개발 DB·키·Firebase·기기 자료는 이관하거나 삭제하지 않는다.

## 대상과 비용 경계

사용자 보고: 프로젝트 `lostparty`, 인스턴스 `lostparty-server`, `ap-southeast-2`(시드니), Ubuntu 24.04 LTS amd64, 2GB RAM/2vCPU/60GB SSD, 월 $12, 브라우저 SSH 성공, Backend/DB 미설치, AWS Free plan·크레딧 $120. 콘솔 계정 상태·만료일·실제 청구는 Backend가 조회하지 않았다.

2026-11-01 후속 배포 입력: 사용자 고정IP 연결/Duck DNS 등록 완료, 주소 `lostparty.duckdns.org`, IPv4 `54.253.176.103`. DNS A 일치/AAAA없음·AWS 인스턴스 running/staticIP/Ubuntu24.04/2GB/2vCPU를 직접 확인했다. FreeTier API는 FREE/ACTIVE·$120·종료2027-05-01T09:26:57.701Z(한국시간18:26:57)를 반환했다. 기존 로그인 프로필의 임시 SSH 접속으로 신규 서버/미설치를 확인하고 첫 설치를 진행한다. 위 미조회 문장은 최초 준비 당시 상태이며 최종 실행 결과는 [배포 기록](../../project/DEV_LOG.md#lightsail-rollout)을 따른다.

- [AWS Free plan](https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/free-tier-plans.html)은 가입 후 6개월 또는 크레딧 소진 중 이른 시점에 종료되어 접근이 중단된다. `$120 / $12 = 10개월`을 이용 가능 기간으로 해석하지 않는다. **Paid plan으로 전환하지 않고**, Billing 홈의 현재 plan/잔액/종료일과 Credits 적용 대상을 먼저 확인한다. 다른 서비스 사용도 같은 잔액을 소비한다.
- [Lightsail 가격](https://aws.amazon.com/lightsail/pricing/)의 번들 외 전송량·스냅샷·디스크 등은 별도 비용이다. 시드니 전송량은 일반 표의 절반이므로 해당 인스턴스 콘솔의 포함량을 기준으로 확인한다. 서버 정지만으로 인스턴스 비용이 없어지지 않는다. 이번 준비에는 RDS/LB/Route53/추가 디스크/스냅샷/유료 모니터링을 추가하지 않는다.
- [고정 IP](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-static-ip-addresses-in-amazon-lightsail.html)는 인스턴스에 연결된 동안 별도 요금이 없고 미연결 상태는 과금된다. 생성하면 즉시 **같은 시드니 리전의 lostparty-server에 연결**한다. 계정에서 이 기능이 Paid plan 전환을 요구하면 중단하고 대안을 검토한다. 이 문서 작성 중 리소스를 생성하지 않았다.
- 정기적으로 Billing 잔액·종료일·전송량을 확인한다. 만료 전 서버 밖으로 백업을 확보한다. 금액 알림은 서비스의 강제 중지 장치가 아니다.

## 현재 코드와 선택 이유

기존 `compose.yaml`은 API/DB를 localhost에 게시하고 HTTPS가 없으며 기본 앱은 DB0023 전용이다. 최신 기능은 `app.main:create_two_cycle_app`와 DB `0035_cycle_group_policy`가 필요하다. 따라서 **독립 파일 `compose.lightsail.yaml`만** 사용한다. 기존 Compose/개발 볼륨을 변경하지 않는다.

구조: 인터넷 → Caddy(80/443) → API(8000, 호스트 게시 없음) → PostgreSQL17(5432, 호스트 게시 없음). API 1 worker로 시작해 내장 정리/모집 worker 다중 실행을 피한다. 2GB에서의 부하 수용량은 미측정이며 테스터20~50명을 동시 처리 보장으로 해석하지 않는다. JSON 로그는 서비스별10MB×5개로 제한하며 Caddy access log는 켜지 않는다.

Caddy는 직접 접속 IP로 XFF를 덮어쓰고 Uvicorn은 Caddy의 고정 내부 IP `172.30.85.2`만 신뢰한다. 임의 클라이언트 XFF/Forwarded를 신뢰하지 않는다. `172.30.85.0/24`가 서버/VPN/다른 Docker망과 겹치면 공개 전에 subnet·Caddy IP·Uvicorn allow IP를 함께 수정/검증한다. CDN/LB를 앞에 추가하면 이 신뢰 경계를 다시 검토한다. API 명령/DTO/DB 스키마 계약은 변경하지 않는다.

동적 DB/API 주소는 `172.30.85.128/25`에서 할당한다. DB/API를 public profile보다 먼저 시작해도 Caddy 고정`.2`를 선점하지 않도록 분리했다. subnet을 바꿀 때 이 범위도 함께 맞춘다.

## 1. 무료 주소와 네트워크 준비

사용자는 도메인을 구매하지 않고 무료 서브도메인을 사용하기로 했다. [Duck DNS](https://www.duckdns.org/)에서 사용 가능한 이름을 등록한다. 예시 `lostparty-선택한이름.duckdns.org`의 실제 등록 이름은 영문/숫자 등 서비스가 허용하는 형식으로 정한다.

1. Lightsail Networking에서 고정 IPv4를 생성해 대상 인스턴스에 연결한다.
2. Duck DNS 로그인 후 서브도메인을 등록하고 **current IP에 Lightsail 고정 IPv4를 명시적으로 입력**해 갱신한다. PC IP 자동 감지를 그대로 저장하지 않는다. AAAA가 있으면 잘못된 IPv6를 남기지 않는다.
3. 고정 IP를 유지하므로 주기적 DDNS cron이나 서버의 Duck DNS 토큰은 필요하지 않다. Caddy는 일반 HTTP/TLS 인증으로 발급하므로 DNS 플러그인/TXT 토큰도 필요하지 않다. 토큰·로그인 화면을 채팅/Issue에 공유하지 않는다. 주소는 무료 DNS 서비스 가용성에 의존한다.
4. Lightsail IPv4 방화벽은 TCP80/443을 공개하고 SSH22는 관리자 접속 범위와 브라우저 SSH 허용 옵션을 보존한다. 8000/5432는 열지 않는다. IPv6를 제공하지 않을 때 해당 규칙도 닫아 둔다. UFW만으로 Docker 게시 포트가 차단된다고 가정하지 않는다([Docker 안내](https://docs.docker.com/engine/install/ubuntu/)).
5. 설치 후 `dig +short A 실제주소`가 고정 IP와 일치하고 `dig +short AAAA 실제주소`에 잘못된 값이 없는지 확인한다. Caddy 시작 전 80/443을 사용하는 기존 서비스도 확인한다.

[Caddy 자동 HTTPS](https://caddyserver.com/docs/automatic-https)는 공개 DNS 이름·외부80/443 접근·인증서 저장 볼륨이 필요하다. 주소가 준비되면 자동 발급/갱신하고 HTTP를 HTTPS로 전환한다. 앱 인증서 검증을 끄거나 자체 서명 인증서를 앱에 허용하지 않는다.

## 2. Ubuntu 설치 준비

이후 명령은 **대상 서버의 브라우저 SSH**에서 실행할 절차다. 설치·신규 DB 생성·공개 실행은 아직 수행하지 않았다. 먼저 `uname -m`, `free -h`, `df -h /`, `ip route`, `sudo ss -lntp`로 아키텍처·여유 자원·망 충돌·포트 점유를 확인한다.

[Docker 공식 Ubuntu 설치](https://docs.docker.com/engine/install/ubuntu/)의 apt 저장소 방식을 사용한다. Ubuntu24.04는 `noble`, 아키텍처는 `amd64`다. 기존 Docker 관련 패키지가 발견되면 무조건 삭제하지 않고 상태를 확인한다. 신규 서버 기준:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git dnsutils
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker compose version
sudo docker run --rm hello-world
```

Docker 그룹 추가 대신 `sudo docker`를 사용한다. Docker/Compose를 설치한 사실만으로 Backend가 설치된 것은 아니다.

## 3. 고정 소스와 환경변수

공개 저장소면 아래 clone을 사용하고, private이면 읽기 전용 deploy key 등으로 접근한다. PAT를 URL/명령행에 넣지 않는다. 원격 게시가 확인된 작업 브랜치에서 고정 SHA를 정하고 서버 checkout을 확인한다. 아직 dev/main 병합 승인은 포함하지 않는다.

```bash
git clone --branch chore/lightsail-deployment https://github.com/heo0328/lostparty-backend.git
cd lostparty-backend
git status --short --branch
git rev-parse HEAD
```

인계한 고정 SHA와 서버 HEAD가 일치하는지 대조한 뒤 아래를 **1회만** 실행한다. 비밀값을 화면에 출력하지 않고 서로 다른 랜덤 DB 암호를 생성한다.

```bash
python3 - <<'PY'
import os, secrets, subprocess
from pathlib import Path
template = Path('docker/lightsail.env.example').read_text()
template = template.replace('REPLACE_ADMIN_PASSWORD', secrets.token_hex(32))
template = template.replace('REPLACE_APP_PASSWORD', secrets.token_hex(32))
template = template.replace('REPLACE_SOURCE_COMMIT', subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], text=True).strip())
fd = os.open('.env.lightsail', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as stream:
    stream.write(template)
PY
nano .env.lightsail
```

`API_DOMAIN`을 등록한 `이름.duckdns.org`로 변경한다(프로토콜·경로 없음). `GOOGLE_CLIENT_ID`는 현재 프로젝트의 기존 기본값이며 Flutter 로그인에서 서버 검증 대상으로 쓰는 audience와 대조한다. `GOOGLE_AZP_ALLOWLIST`는 기존 네이티브 클라이언트 요구에 맞게 검토하며 임의 값을 추가하지 않는다. 새 서버 키 ID는 `lightsail-1`로 고정한다. `.env.lightsail`을 `cat`/게시하거나 `docker compose config`의 전체 결과를 공유하지 않는다. 기존 DB의 암호는 env 파일 변경만으로 바뀌지 않는다.

동일 셸에서 이후 명령용 함수를 정의한다:

```bash
dc() { sudo docker compose --env-file .env.lightsail -f compose.lightsail.yaml "$@"; }
dc config --quiet
dc build api
mkdir -p .secrets
sudo install -d -o 10001 -g 10001 -m 0700 .secrets/lightsail
sudo docker run --rm --user 10001:10001 --read-only --cap-drop ALL \
  --security-opt no-new-privileges:true --network none \
  -v "$PWD/.secrets/lightsail:/run/secrets:rw" \
  "lostparty-backend-api:$(git rev-parse HEAD)" python scripts/create_lightsail_secrets.py
```

기존 `create_auth_keys.py`는 JWT/복구 키만 만들지만 신규 전용 스크립트는 JWT·복구·Lost Ark 암호화·fingerprint 4개를 만든다. UID10001/권한0600, 디렉터리0700이며 기존 파일이 하나라도 있으면 덮어쓰지 않는다. 실패 후 부분 생성도 자동 재생성하지 않고 확인한다. `.secrets/lightsail`은 개발 키와 분리한다. 개인 Lost Ark API 토큰 원문은 서버 공통 env에 넣지 않는다.

위 디렉터리 생성·소유자 설정은 **새 빈 경로 전용**이다. 기존 키 경로에 재실행하지 않는다. Compose v5의 `run -v ...:rw`는 서비스의 read-only 마운트를 그대로 유지하는 동작이 확인되어, bootstrap에만 직접 `docker run`을 사용한다. 네트워크 없이 UID10001로 생성하고 서비스는 계속 read-only로 읽는다.

## 4. 신규 DB 초기 구성 — 공개 전에 별도 실행

이 단계는 **아직 DB가 없는 신규 인스턴스 전용**이다. 먼저 `dc ps -a`와 `sudo docker volume ls --filter name=lostparty-lightsail`로 기존 컨테이너/볼륨 유무를 확인한다. 기존 자료가 발견되면 fresh로 간주하지 말고 확인한다. `down -v`, volume prune, DB restore/초기화는 실행하지 않는다.

```bash
dc up -d --wait db
dc run --rm --no-deps api alembic heads
dc run --rm --no-deps api alembic current
```

예상: heads는 단일 `0035_cycle_group_policy`; current는 신규 DB이므로 revision 없음이다. DB init은 빈 볼륨에서만 `lostparty_app`을 생성하며 superuser/createdb/createrole 권한을 주지 않는다. 앱 역할은 현행 migration을 위해 public schema CREATE 권한을 가진다. 별도 최소권한 런타임 역할 도입은 이번에 하지 않는다. 관리자 암호는 API 컨테이너에 전달하지 않는다.

두 상태와 신규 DB 대상을 확인한 뒤 migration을 명시 실행한다. API 시작 시 자동 migration은 없다.

```bash
dc run --rm --no-deps api alembic upgrade 0035_cycle_group_policy
dc run --rm --no-deps api alembic current
dc up -d --wait api
dc exec -T api python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5); print(r.status)"
dc ps
```

레이드 카탈로그는 코드/정적 자료, 기본 head/정책은 migration에서 준비한다. 실회원·방·기존 Firebase/개발 DB 덤프를 seed로 넣지 않는다. API lifespan이0035 스키마/권한/head를 검사하고 내장 worker를 시작한다. 실패하면 오류의 민감정보를 제거해 조사하고 DB를 지워 재시도하지 않는다.

## 5. HTTPS 공개와 검증

실제 주소·DNS·방화벽을 확인한 뒤 실행한다. `api.example.invalid` 상태로 public을 시작하지 않는다.

```bash
dc --profile public run --rm --no-deps caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
dc --profile public up -d caddy
curl --fail --silent --show-error https://실제주소/health
curl --silent --show-error --head http://실제주소/health
```

HTTPS는 인증서 검증을 켠 채200, HTTP는 HTTPS redirect가 기대값이다. Caddy 인증서/계정은 `caddy_data`에 보존하며 재시작 시 삭제하지 않는다. 요청 원문/인증정보가 들어갈 수 있는 debug/access log를 켜지 않는다. 실패 시 DNS A/AAAA·80/443·포트 점유·시각과 CA 제한부터 확인하며 인증서 발급을 반복하지 않는다.

공개 완료 판정 전에 확인할 경계:

- 외부에서80/443만 서비스 접근 가능하고8000/5432 직접 접속이 차단된다. localhost로도 API/DB를 게시하지 않는 구성이므로 호스트 확인은 `dc exec`를 사용한다.
- 서로 다른 실제 공인 IP의 인증 제한 분리, 같은 IP 제한, 위조 XFF/Forwarded·다중 hop의 우회 불가, 그룹 가입 코드 제한을 확인한다. 같은 NAT의 기기들은 IP를 공유한다. 임시 개발 프록시/worker 추가로 결과를 왜곡하지 않는다.
- HTTPS Google 로그인→세션 발급→refresh·기존 앱 핵심 조회를 확인한다. 네이티브에는 검증된 서버 주소와 고정 소스/변경 범위만 인계하고 전체 기존 인수를 반복 요청하지 않는다. 새 서버는 별도 회원/세션이므로 로컬 세션을 성공 근거로 삼지 않는다.
- `dc ps`의 db/api healthy와 worker의 예외/재시작·메모리/디스크 추이를 확인한다. 기동·TLS만으로 부하/공개 베타 인수 완료를 선언하지 않는다.

F02는 프록시 구성 준비 재개 상태다. 위 실제 IP/그룹 코드/HTTPS 인증 검증이 남아 있으므로 완료가 아니다.

## 백업·복구와 반영 기록

첫 공개 전 DB·환경·4개 키를 함께 보존할 경로와 담당을 정한다. 로컬 볼륨은 백업이 아니다. 서버 내부 DB 덤프 예시(서비스 중 가능):

```bash
umask 077
mkdir -p backups
dc exec -T db pg_dump -U postgres -d lostparty -Fc > "backups/lightsail-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

명령 실패/빈 파일은 성공 백업으로 기록하지 않는다. `.env.lightsail`과 `.secrets/lightsail`도 암호화된 서버 밖 저장소로 보존한다. Duck DNS 토큰은 이 서버에 저장하지 않는다. 복구에는 DB뿐 아니라 당시 암호화/서명 키·소스 이미지·설정이 필요하다. 덤프 존재/목록 확인과 격리 PostgreSQL17 복원·역할/0035/키 연결 검증을 구분한다. 기존 `compose.preflight.yaml` 등 별도 환경에서 복원을 검증하고 서비스 DB로 시험 복원하지 않는다. 자동 백업/알림은 현재 미구현이다.

실제 배포 기록에는 source SHA·이미지 ID/RepoDigest(API/Postgres/Caddy)·Compose 버전·migration current·키 ID(값 제외)·HTTPS 주소·확인 시각/항목·미확인을 남긴다. upstream 이미지 태그는 가변이므로 첫 검증한 digest/이미지를 기록·보존하고 운영 중 무조건 pull하지 않는다. 최초 설치 실패 시 caddy/api를 중지해 공개를 닫고 DB/키는 보존한다. 후속 업데이트는 고정 이미지·사전 백업·migration 호환성 검토 후 시행하며 구 이미지로 교체만 하면 DB가 롤백된다고 가정하지 않는다.

## 최초 준비(ce25368)에서의 검증 범위

정적 YAML/키 생성·덮어쓰기 거절/문서 검증 결과는 [DEV_LOG](../../project/DEV_LOG.md#lightsail-preparation)에 기록한다. 현재 작업 환경에 Docker 실행기가 없어 Compose 실제 렌더링·이미지 build·빈 PostgreSQL migration·Caddy validate·실제 DNS/TLS/IP 제한·provider/기기·복원/부하 검증은 실행하지 않았다. 위 명령은 실행 완료 근거가 아니다.

## 2026-11-01 실제 첫 배포 결과

위 최초 준비 이후 사용자 배포 지시로 source`6154e45`·API이미지`dfad04e8`·신규DB0035를 `lostparty-server`에 실제 반영했다. **https://lostparty.duckdns.org/health**는 인증서검증을 켠 외부요청에서200/DB정상이다. HTTP는308, DB/API는healthy, Caddy는running/실제HTTPS확인이다. 최초 발급 중 약6초의 TLS준비 오류 후 자동발급이 완료됐다. 인증서 SAN/Let's Encrypt YE2·만료2027-01-30을 확인했으며 갱신데이터는 Caddy볼륨에 보존한다.

현재 사용자 계정/세션/인증거래/그룹은0개인 신규환경이다. 실제이미지의 두전체OpenAPI일치·공개조회/인증거절/no-store·직접포트차단·위조전달헤더 제한우회불가·두실제출발지 제한분리·worker3종실행/관찰시ERROR0을 확인했다. 초기덤프는 별도내부망/tmpfs PostgreSQL17에 소유자/ACL제외로 복원해0035/115표를 확인했고 임시시험컨테이너만 제거했다. 서비스DB/키 초기화·개발자료이관은 하지 않았다.

자세한 고정소스/이미지/검증/백업/미확인은 [집계](records/lightsail-first-deploy.json)와 [DEV_LOG](../../project/DEV_LOG.md#lightsail-rollout)를 따른다. 실제 Google성공/refresh·로그인후그룹코드·서버밖키포함암호화백업·자동화/전체복구·부하/장기운영인수는 남아 있다. 후행 문서게시로 서비스 소스를 교체하지 않는다.
