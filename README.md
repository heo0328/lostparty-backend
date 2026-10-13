# LostParty FastAPI + PostgreSQL 실행 가이드

프로젝트 위치: WSL Ubuntu의 `/home/heowork/projects/lostparty-backend`.

## 1. 상태 확인

PowerShell에서 Ubuntu로 들어간 다음 아래 명령을 실행합니다.

```powershell
wsl -d Ubuntu
```

```bash
cd /home/heowork/projects/lostparty-backend
docker compose ps
curl -i http://127.0.0.1:8000/health
```

정상 응답은 HTTP 200과 `{"status":"ok","database":"ok"}`입니다. 이 요청은 앱 계정으로 PostgreSQL의 `SELECT 1`을 실행합니다. DB가 연결되지 않으면 HTTP 503을 반환하며 비밀번호나 연결 오류의 상세 내용은 응답에 노출하지 않습니다.

## 2. 파일 구성

- `app/main.py`: FastAPI와 DB 연결을 검사하는 `/health`.
- `Dockerfile`, `requirements.txt`: Python 3.12 기반 API 이미지와 직접 의존성 버전 고정.
- `compose.yaml`: linux/amd64 API·PostgreSQL 17 서비스, 상태 검사, 영속 볼륨.
- `docker/init-db.sh`: 최초 DB 생성 시 일반 앱 계정 생성.
- `.env`: 서로 다른 무작위 관리자·앱 비밀번호. 권한 600, Git 및 이미지 빌드에서 제외.
- `.env.example`: 공유 가능한 환경변수 예시.
- `scripts/verify.py`: 실제 컨테이너를 사용하는 검증 절차.

DB 포트는 호스트에 공개하지 않습니다. API의 8000번 포트는 `127.0.0.1`에만 연결합니다. API는 비관리자 사용자로 실행하고 읽기 전용 파일시스템, 권한 제거, 새 권한 획득 차단을 적용했습니다. PostgreSQL 앱 계정은 슈퍼유저가 아니며 해당 DB의 public 스키마에서 테이블을 생성할 수 있습니다. 이후 마이그레이션 계정과 실행 계정을 분리하면 권한을 더 줄일 수 있습니다.

## 3. 시작·중지·수정

```bash
# 최초 실행 및 코드 변경 반영
docker compose up -d --build --wait

# 로그 확인
docker compose logs --tail=100 api db

# 컨테이너 제거, 데이터 유지
docker compose down

# 다시 시작
docker compose up -d --wait
```

DB가 정상 상태가 된 후 API가 시작합니다. 코드 자동 재시작 기능은 켜지 않았으므로 코드를 수정한 뒤에는 `--build`로 다시 실행하세요.

`docker compose down -v`는 DB 볼륨을 삭제합니다. 데이터 보존이 필요하면 사용하지 마세요. 프로젝트 이름 `lostparty-backend`를 변경하면 다른 볼륨을 사용하게 되어 기존 데이터가 보이지 않을 수 있습니다.

## 4. 검증 다시 실행

```bash
python3 scripts/verify.py
```

이 절차는 `/health` 200, 앱 계정의 비슈퍼유저 여부, DB 중지 시 503, DB 복구 후 200을 검사합니다. 임의 토큰을 테이블에 저장하고 `down` → `up`으로 DB 컨테이너를 재생성한 다음 같은 토큰이 남았는지 확인합니다. 성공 시 테스트 행을 삭제하며 테스트용 테이블 `persistence_probe`는 남습니다. 컨테이너 중지·재생성을 포함하므로 운영 중인 서비스에서는 점검 시간에만 실행하세요.

## 5. 환경변수와 비밀번호

`.env.example`의 값은 예시입니다. 현재 로컬 `.env`에는 생성된 실제 무작위 비밀번호가 들어 있습니다. `.env`를 커밋하거나 채팅에 붙여 넣지 마세요. 환경변수가 포함된 `docker compose config` 전체 출력도 공유하지 마세요.

PostgreSQL 초기화 스크립트와 `POSTGRES_PASSWORD`는 **빈 볼륨의 최초 실행에만** 적용됩니다. 기존 DB에서 `.env`만 수정하면 DB 비밀번호는 바뀌지 않습니다. 기존 비밀번호 변경은 DB의 `ALTER ROLE`과 `.env`를 함께 갱신한 뒤 API를 재생성하는 절차가 필요합니다. 비밀번호 변경을 위해 기존 볼륨을 삭제하지 마세요.

## 6. 백업과 복원

```bash
mkdir -p backups
chmod 700 backups
docker compose exec -T db sh -c 'pg_dump -U postgres -d "$POSTGRES_DB" -Fc' > "backups/lostparty-$(date +%Y%m%d-%H%M%S).dump"
chmod 600 backups/*.dump
```

백업은 서버 외부의 안전한 저장소에도 복사하세요. 볼륨은 컨테이너 재생성 시 데이터를 보존하지만 서버·디스크 유실을 막는 백업은 아닙니다.

새 서버에서는 먼저 새 `.env`로 DB를 초기화한 다음, API를 중지하고 백업을 복원합니다. 복원 대상은 빈 DB여야 하며 기존 데이터가 있는 DB에는 덮어쓰지 마세요.

```bash
docker compose stop api
docker compose exec -T db sh -c 'pg_restore --exit-on-error -U postgres -d "$POSTGRES_DB"' < backups/복원할파일.dump
docker compose up -d --wait
curl -f http://127.0.0.1:8000/health
```

백업이 사용하는 `lostparty_app` 역할은 새 DB 초기화 단계에서 생성됩니다. 복원 후 실제 업무 데이터도 확인하세요.

## 7. Lightsail Linux amd64에서 재사용

1. Linux x86_64/amd64 인스턴스를 준비하고 Docker Engine와 Compose 플러그인을 설치합니다. 서버에서 `uname -m`과 `docker info --format '{{.OSType}}/{{.Architecture}}'`로 확인합니다.
2. Git에 포함되는 프로젝트 파일을 서버로 전달합니다. `.env`와 DB 볼륨은 Git으로 전달하지 않습니다. 현재 첫 커밋은 아직 생성하지 않았습니다.
3. 서버에서는 `.env.example`을 `.env`로 복사하고 두 비밀번호를 서로 다른 새 무작위 값으로 지정합니다. `openssl rand -hex 32`를 각각 실행해 만들 수 있습니다. `chmod 600 .env`를 적용합니다.
4. 동일 디렉터리에서 `docker compose up -d --build --wait`를 실행합니다. 로컬과 동일하게 API는 서버의 루프백 주소에만 연결됩니다.
5. 외부 공개 전 호스트의 Nginx/Caddy 등으로 HTTPS 역방향 프록시를 구성해 `127.0.0.1:8000`으로 전달합니다. 현재 스캐폴딩에는 도메인·인증서·프록시 설정이 포함되어 있지 않습니다. 프록시 클라이언트 IP가 필요하면 신뢰하는 프록시 주소를 정한 뒤 Uvicorn 설정을 조정하세요.
6. Lightsail 공개 방화벽은 SSH를 관리자의 IP로 제한하고, 웹 공개 시 80/443만 필요한 범위에 엽니다. 8000/5432는 공개하지 않습니다. IPv6를 사용하는 경우 IPv6 규칙도 확인하세요. Lightsail 공개 방화벽은 사설 IP 트래픽에 적용되지 않으므로 호스트 방화벽도 검토합니다.
7. 데이터를 옮길 때는 위의 논리 백업·복원 절차를 사용합니다. 로컬 Docker Desktop 볼륨이 원격 서버로 자동 이동하지 않습니다.

amd64가 명시되어 있으므로 동일 CPU 계열에서 재사용할 수 있습니다. 이미지 태그는 패치 업데이트에 따라 달라질 수 있고 Python 간접 의존성은 완전한 잠금 파일로 고정되어 있지 않습니다. 운영 배포 전 검증한 이미지 digest와 전체 의존성 잠금, 마이그레이션, 정기 백업 및 복원 검증을 추가하세요. PostgreSQL 주요 버전 변경은 볼륨을 그대로 연결하는 방식으로 진행하지 말고 별도 업그레이드 절차를 따르세요.

공식 참고: [FastAPI Docker 배포](https://fastapi.tiangolo.com/deployment/docker/), [Compose 시작 순서와 healthcheck](https://docs.docker.com/compose/how-tos/startup-order/), [Compose 볼륨](https://docs.docker.com/reference/compose-file/volumes/), [Lightsail 방화벽](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html).
