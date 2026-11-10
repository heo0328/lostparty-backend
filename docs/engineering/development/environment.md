# 개발 환경·실행 구성·검증 안내

## 현재 로컬 기준 — 2026-11-10

현재 코드/실행은 업무44eb4ba·게시624ef00/feat/raid-batch-completion, runtime ae6b3e0a·DB0036_roster_presence다. 앱288파일 일치·healthy 및 기본125/142·two-cycle192/213 계약을 확인했다. [개발 반영 원본](../operations/records/batch-completion-local-rollout.json)·[현재 작업](../../project/NEXT_WORK.md)을 따른다. 이번 문서 작업에서 서버/DB를 재실행하지 않았다.

## 2026-11-07 복구 당시 확인

복구 당시 로컬은 `compose.yaml` + `compose.two-cycle.yaml`·DB `0035_cycle_group_policy`로 기동했으며, 복구한 키4개와 현재 debug Android OAuth 허용값으로 실제 앱 Google 로그인을 확인했다. Git 작성자·GitHub 인증/쓰기·Docker 연결도 확인했고, 의존성은 API 이미지에서 runtime31개/시험 이미지에서 전체43개 잠금 일치를 확인했다. 호스트 Python에 같은 패키지를 전역 설치할 필요는 없다. Python/Pylance/디버거 확장은 설치돼 있지만 로컬 `.venv`와 호스트 프로젝트 패키지는 없어 에디터 직접 분석/디버깅 구성은 선택 후속이다.

빈 로컬DB의 테이블 준비와 기존DB 재기동은 구분한다. 기본0023 실행과 최신 구성의 단일화는 [별도 조사](runtime-consolidation-review.md)만 완료했고 코드는 변경하지 않았다. [백업 파일/보관 상태](../operations/backup-and-recovery.md)·[자동 검증의 결과와 한계](../../project/DEV_LOG.md#development-recovery-20261107)를 따른다. 아래0032 실행 수치·예전환경은 당시 이력이며 현재 복구 상태를 덮어쓰지 않는다.

## 환경 분리 기준

개발·검증은 로컬 dev가 기본이고 운영 반영은 개발자 지시에 따릅니다. [로컬 개발과 운영 반영](workflow.md#local-dev-and-production)을 판단 기준으로 사용합니다. 로컬 실행 중단은 먼저 기동으로 해결하며 원격 CI로 임의 대체하지 않습니다.

| 네이티브 빌드 | 연결 대상 |
|---|---|
| debug | 개발자 로컬 Backend 서버 |
| release | AWS 운영 Backend 서버 (`https://lostparty.duckdns.org`) |

위 표는 2026-11-02 사용자가 네이티브에 전달한 baseURL 분리 지시입니다. 실제 앱 설정 반영·접속 확인 완료를 뜻하지 않습니다. 로컬 주소는 기기에서 접근 가능한 실제 환경을 확인해 인계하며 임의로 확정하지 않습니다. 이 문서 수정으로 URL·서버 설정을 변경하지 않습니다.

<a id="section"></a>

## 기술과 설정

Python3.12·FastAPI/Uvicorn·SQLAlchemy·Alembic·PostgreSQL17/psycopg를 Docker Compose로 실행한다. 직접 의존성은 [requirements](../../../requirements.txt), 검증 의존성은 [requirements-dev](../../../requirements-dev.txt), 이미지 구성은 [Dockerfile](../../../Dockerfile)을 따른다. WSL2/Bash는 현재 개발환경이며 라이브러리 사용자의 설치 요건은 아니다.

[검증된 의존성 고정](dependency-locking.md): 직접 요구는 requirements.in/requirements-dev.in, 실제 설치는 전이 의존성과 SHA256을 포함한 requirements.txt/requirements-dev.txt를 사용한다. Docker 빌드는 해시·pip check·설치 목록 일치를 검사한다.

`.env`와 인증/암호화 키는 로컬 비공개 설정이다. 값·원문 응답·회원 개인정보를 문서나 커밋에 넣지 않는다. 새 환경의 설정 준비와 기존 환경의 재기동을 구분한다. 기존 키가 있는 환경에서 키 생성 명령을 반복하지 않는다.

<a id="section-2"></a>

## 현재 실행 구성

현재 개발 API는 `compose.yaml`에 `compose.two-cycle.yaml`을 덮어써 `app.main:create_two_cycle_app --factory`를 선택한다. 기본 Dockerfile의 `app.main:app`는 기존 앱이며 현재 개발 DB에 기본 Compose 단독으로 혼용하지 않는다. `two-cycle`은 실행 구성 이름, `0036_roster_presence`는 현재 로컬 DB구조 이행 식별자다. 아래0032 수치는 이전 반영 이력이다.

현재 실제 개발 서버는178경로/199 operation·DB0032이며 [명시 출발 정수분 개발 반영](../operations/explicit-minute-rollout.md)의 source420e057/이미지cd581ac0를 사용한다. join후보/활성방한도/조율선택조회와검색정수분범위를지원한다. 베타명시출발은정수분이며기본/자동/개인표/진행시간은5분유지한다. 고정runtime31개·JSON로깅·API/DB10m×5와 기존DB컨테이너/볼륨·설정/키를 유지하고 읽기전용검색·실제HTTP9/두계약/worker를 확인했다. 문자hangul-printable-ascii-1·종료관계목록보완이실행중이다. DB32에 구이미지366e868a만 재적용하지 않는다. 아이템레벨 보완 인수는 수용됐고 전체 모집·실회원/기기 인수는 미완료다. 상세 전환 근거는 [운영 기록](../operations/README.md)을 따른다.

기존 DB가 해당 단계로 검증된 개발환경의 API 재기동 예시는 다음과 같다. 이 명령은 DB migration·초기 설정·복원을 대신하지 않는다.

```bash
docker.exe compose -f compose.yaml -f compose.two-cycle.yaml up -d --no-deps --build --wait --wait-timeout 180 api
python3 scripts/check_openapi.py --docker docker.exe --container lostparty-backend-api-1 --profile two-cycle
```

<a id="section-3"></a>

## 계약과 테스트

현재 실행 계약은 [two-cycle OpenAPI](../../../openapi/two-cycle.openapi.yaml), 기본앱 보존 계약은 [기본 OpenAPI](../../../openapi/openapi.yaml)다. 비교는 생성 객체 전체를 검사하며 차이를 무조건 자동 덮어쓰지 않는다. HTTP Swagger/OpenAPI 공개 경로는 비활성이다.

표준 실행은 [격리 검증 실행 안내](isolated-verification.md)를 따른다. `python3 scripts/verify_isolated.py`의 static/contracts/legacy/two-cycle/all을 목적에 맞게 선택한다. 시험 이미지는 현재 소스로 빌드하며 기존 개발 API의 latest에 의존하지 않는다.

pytest는 `compose.test.yaml`의 별도 테스트 DB를 사용한다. 개발 DB를 fixture/초기화 대상으로 사용하지 않는다. 테스트 이미지가 참조하는 계약 snapshot과 파일 COPY 경로도 함께 관리한다. 실제 개발서버·provider·정상 로그인 사용자 시험과 합성 테스트는 결과를 분리한다.

문서/자료 경로만 변경한 경우 서버·DB를 재기동하지 않고 링크·JSON·Python 문법·자료 참조·기존 설계 검증으로 확인한다. 모델을 쓰는 build 도구와 읽기 검증 도구의 실행 목적을 구분한다.
