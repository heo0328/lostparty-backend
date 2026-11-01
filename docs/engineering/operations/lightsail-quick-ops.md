# Lightsail 짧은 운영 안내

대상: 시드니 `lostparty-server` / `54.253.176.103` / **https://lostparty.duckdns.org**. 아래 명령은 서버 SSH에서 실행한다. 실제 컨테이너 라벨로 확인한 배포 경로는 `/home/ubuntu/lostparty-backend`, Compose는 `compose.lightsail.yaml`, 환경은 `.env.lightsail`, 프로젝트명은 `lostparty-lightsail`이다. 로컬 개발 Compose와 합치지 않는다.

## 상태·최근 로그

```bash
cd /home/ubuntu/lostparty-backend
dc() { sudo docker compose --env-file /home/ubuntu/lostparty-backend/.env.lightsail -f /home/ubuntu/lostparty-backend/compose.lightsail.yaml --profile public "$@"; }

dc ps
curl --fail --silent --show-error --max-time 10 https://lostparty.duckdns.org/health
dc logs --since 30m --tail 100 --no-color api
dc logs --since 30m --tail 100 --no-color db caddy
```

기대 상태는 `api`/`db`가 `healthy`, `caddy`가 `running`, health 응답은 `status: ok, database: ok`다. Caddy에는 Docker healthcheck가 없으므로 HTTPS 응답도 함께 확인한다. 로그를 공유할 때 필요한 상태·오류 code·request_id만 남기고 인증정보·개인정보는 제외한다. `.env.lightsail`이나 전체 `docker inspect`/`compose config` 출력을 공유하지 않는다.

## API만 재시작

같은 셸에서 위 `dc` 함수를 정의한 뒤 **필요할 때만** 실행한다. 잠깐 API 요청이 중단될 수 있다.

```bash
dc restart --no-deps api
dc ps api
curl --fail --silent --show-error --max-time 10 https://lostparty.duckdns.org/health
```

health가 즉시 정상화되지 않으면 `dc ps api`와 최근 API 로그를 확인하고 잠시 후 health를 다시 조회한다. `restart`는 현재 환경·이미지를 그대로 사용한다. `.env.lightsail` 변경 반영이 목적이면 다음 명령으로 API만 재생성한다(설정 검토 후 실행).

```bash
dc config --quiet
dc up -d --no-deps --no-build --pull never --force-recreate --wait api
```

DB/Caddy나 Docker 데몬을 함께 재시작할 필요는 없다. 이 안내 작성에서는 두 재시작/재생성 명령을 **실행하지 않았다**. `down -v`/volume prune은 DB·인증서 자료를 잃을 수 있으므로 운영 명령에 사용하지 않는다.

## 자동 시작·로그 제한 확인 결과

2026-11-01 **한국시간21:18** 읽기 확인 기준:

| 항목 | 실제 적용 상태 |
|---|---|
| Docker / containerd | systemd `enabled` + `active` |
| API·DB·Caddy | 모두 실행 중, Docker `restart: unless-stopped`, 재시작 횟수0 |
| API / DB | `healthy` |
| 서비스 로그 | 셋 모두 `json-file`, `max-size=10m`, `max-file=5` |
| DB / 인증서 보존 | PostgreSQL 데이터·Caddy `/data`·`/config`는 Docker volume |

```bash
systemctl is-enabled docker.service containerd.service
systemctl is-active docker.service containerd.service
sudo docker inspect --format '{{.Name}} restart={{.HostConfig.RestartPolicy.Name}} log={{json .HostConfig.LogConfig}}' lostparty-lightsail-api-1 lostparty-lightsail-db-1 lostparty-lightsail-caddy-1
```

현재 실행 컨테이너는 Docker가 부팅할 때 재시작하도록 설정돼 있다. 다만 `unless-stopped`는 **수동으로 중지한 컨테이너를 재부팅 때 자동으로 되살리지 않으며**, `compose down`으로 제거한 컨테이너도 새로 만들지 않는다. Docker 데몬 재기동 시에는 Compose의 `depends_on` 준비 순서를 다시 실행한다고 보장하지 않는다. DB 준비가 늦어 API 프로세스가 종료되면 재시작 정책으로 회복할 수 있지만, `unhealthy` 상태 자체만으로 재시작되지는 않는다. 재부팅 후에는 위 상태/HTTPS를 확인한다. **실제 재부팅·자동 회복 시험은 하지 않았다.** [Docker 재시작 정책](https://docs.docker.com/engine/containers/start-containers-automatically/)

로그는 컨테이너당 약50MB, 세 서비스 합계 약150MB까지 회전하는 설정이다. Docker 메타데이터·호스트 journal·DB 데이터·덤프까지 포함한 전체 디스크 제한은 아니다. 실제 대량 로그 회전 시험은 하지 않았다. [Docker JSON 로그 제한](https://docs.docker.com/engine/logging/drivers/json-file/)

## 서버 외부 DB 백업 상태

**미구성/전송 완료 미확인.** 현재 확인한 것은 서버 내부 `backups/`의 DB 덤프2개(초기배포·수동인증 전, 모두0600)와 설정 변경 전 환경 백업1개다. 초기 덤프의 격리 복원 기록은 있지만, 최신 수동인증 이후 상태를 담은 백업은 이번에 만들지 않았다.

ubuntu/root crontab 없음, `/etc/cron*`·사용자/시스템 custom systemd 설정에서 DB 백업/외부 전송 작업이 확인되지 않았다. `dpkg-db-backup.timer`는 Ubuntu 패키지관리 DB용이며 LostParty PostgreSQL 백업이 아니다. 이전 배포 기록에도 외부 복사·암호화된 키 포함 복구 완료 근거가 없다. 사용자가 별도로 수행한 외부 수동 복사 여부까지 확인한 것은 아니다.

서버 손실에 대비하려면 **DB 덤프 + 현재 `.env.lightsail` + `.secrets/lightsail` 4종 키**를 암호화해 서버 밖에 보존하고 복원을 검증해야 한다. 저장 위치·담당·주기·보관기간·복구 목표를 정하는 작업이 남아 있다. 이번에는 외부 저장소 생성/전송·유료 백업 서비스·자동화 설정을 추가하지 않았다.

설치/복원 상세는 [첫 배포 절차](lightsail-first-deploy.md), 이번 확인 근거는 [DEV_LOG](../../project/DEV_LOG.md#lightsail-quick-ops)를 따른다.
