# 개발 환경·실행 구성·검증 안내

<a id="section"></a>

## 기술과 설정

Python3.12·FastAPI/Uvicorn·SQLAlchemy·Alembic·PostgreSQL17/psycopg를 Docker Compose로 실행한다. 직접 의존성은 [requirements](../../../requirements.txt), 검증 의존성은 [requirements-dev](../../../requirements-dev.txt), 이미지 구성은 [Dockerfile](../../../Dockerfile)을 따른다. WSL2/Bash는 현재 개발환경이며 라이브러리 사용자의 설치 요건은 아니다.

[검증된 의존성 고정](dependency-locking.md): 직접 요구는 requirements.in/requirements-dev.in, 실제 설치는 전이 의존성과 SHA256을 포함한 requirements.txt/requirements-dev.txt를 사용한다. Docker 빌드는 해시·pip check·설치 목록 일치를 검사한다.

`.env`와 인증/암호화 키는 로컬 비공개 설정이다. 값·원문 응답·회원 개인정보를 문서나 커밋에 넣지 않는다. 새 환경의 설정 준비와 기존 환경의 재기동을 구분한다. 기존 키가 있는 환경에서 키 생성 명령을 반복하지 않는다.

<a id="section-2"></a>

## 현재 실행 구성

현재 개발 API는 `compose.yaml`에 `compose.two-cycle.yaml`을 덮어써 `app.main:create_two_cycle_app --factory`를 선택한다. 기본 Dockerfile의 `app.main:app`는 기존 앱이며 현재 개발 DB에 기본 Compose 단독으로 혼용하지 않는다. `two-cycle`은 실행 구성 이름, `0031_membership_actions`는 DB구조 이행 식별자다.

현재 실제 개발 서버는177경로·DB0031이며, #26 아이템레벨 보완 sourcef471e31/이미지6d5857b3를 반영했다. [실제 교체·자료 보존·HTTP 검증](../operations/application-item-level-rollout.md)을 확인했다. 아이템레벨 보완 인수는 수용됐고 전체 모집·실회원/기기 인수는 미완료다. 상세와 복원/이행 전후 근거는 [운영 전환 기록](../operations/README.md)을 따른다.

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
