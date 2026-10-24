# 격리 검증 실행

2026-10-25 도입. 현재 checkout의 소스로 시험 이미지를 빌드하고 실행마다 고유 `lostparty-check-…` 프로젝트를 만든다. 개발 API 이미지를 교체하거나 개발 Compose를 호출하지 않는다. API 계약·iOS 연결 방식은 바뀌지 않는다.

## 명령

프로젝트 루트에서 실행한다. 호스트는 Python3 표준 라이브러리와 Docker Compose가 필요하며, Python 패키지는 시험 이미지 안에 설치한다. WSL에서 필요하면 명령 끝에 `--docker docker.exe`를 붙인다.

```bash
python3 scripts/verify_isolated.py static
python3 -m unittest discover -s scripts/tests -v
python3 scripts/verify_isolated.py contracts
python3 scripts/verify_isolated.py legacy
python3 scripts/verify_isolated.py two-cycle
python3 scripts/verify_isolated.py all
```

- `static`: 기존 문서·동결자료·JSON/Python 경로 검사와 실행기 호스트 unittest. Docker/DB를 시작하지 않는다. 전체 lint/type 검사는 아니다.
- 호스트 unittest: 실행기의 환경 거부·선택 제한·실패 전달·cleanup 제어를 검사한다. DB/서버에 접근하지 않는다.
- `contracts`: 새 시험 이미지에서 기본116경로/133동작과 two-cycle177경로/197동작의 생성 OpenAPI 객체 전체를 비교한다. DB/lifespan/HTTP 서버를 시작하지 않는다.
- `legacy`: 인증·계정·bootstrap·회원설정·개인키·그룹HTTP·기존모집HTTP의 지정7파일 회귀 묶음이다.
- `two-cycle`: 구성·통합자격·표시/참조/아이템레벨·membership actions·atomic members·완료정정의 지정8파일 회귀 묶음이다.

- `all`: `tests/test_*.py` 전체 파일을 선택한다. 시간이 오래 걸릴 수 있으며 전체 선택이 전체 통과를 뜻하지 않는다. 추가 파일을 지정하면 그 파일만 실행한다.

legacy/two-cycle 묶음은 프로젝트 전체 시험이 아니다. 파일 목록은 [실행 정의](../../../scripts/isolated_checks.py)의 `SUITES`가 원본이며 시작 시 실제 선택을 출력한다. 특정 변경에 필요한 다른 시험은 `all tests/test_…py`로 선택할 수 있다. 기존 검증 결과의 수치를 새 실행의 통과 수에 합산하지 않는다.

묶음 안의 파일/정확 node만 선택할 수도 있다. 선택된 항목만 검증한 결과로 보고한다.

```bash
python3 scripts/verify_isolated.py legacy tests/test_auth.py
python3 scripts/verify_isolated.py two-cycle tests/test_application_item_level.py
python3 scripts/verify_isolated.py all tests/test_recruitment_cycle_queries.py
```

## 환경·데이터 경계

- 고유 프로젝트의 `test-db`만 만들고 `lostparty_test`를 tmpfs에 저장한다. host port·host bind mount·영속 volume·실키 연결은 없다. 내부 네트워크만 사용해 시험 중 실제 provider 접근을 막는다. 이미지 최초 build의 패키지 다운로드에는 네트워크가 필요하다.
- `.env` 자동 로딩을 끄고 상속한 `COMPOSE_*` 옵션을 제거한 뒤 `compose.test.yaml`과 고유 프로젝트를 명시한다. `DATABASE_URL`/키 디렉터리는 Compose의 합성 시험 값으로 고정한다. 기존 개발 컨테이너 이름이나 volume을 참조하지 않는다.
- 컨테이너 진입점은 시험 표식·DB 주소/DB명/사용자·키 디렉터리·worker 비활성을 검사하며 다른 환경이면 pytest 전에 거부한다. 이것은 직접 pytest를 임의 환경에서 실행해도 안전하다는 보장이 아니다. 신규 진입점을 사용한다.
- 공통 `tests/conftest.py`의 기본0023 준비를 유지한다. `test_model_migration_consistency`도0023의 명시적 모델 모듈만 복사해 비교하며0031에서만 생기는 index를 제외한다. 전체 collection에서 최신 모델이 import돼도 기본 시험에 섞이지 않도록 했다. 이 시험은0031 전체 metadata 일치 검증이 아니다. 최신 기능 시험은 기존 fixture로 별도 임시 DB/제한된 app role을 만들고 필요한0031 등으로 이행한다. 전체 fixture를0031로 바꾸지 않았다. 인증 cleanup은 기존 TestClient lifespan 동작을 유지하되 시험DB 안에서만 동작한다.
- pytest 종료/빌드 실패/일반 Ctrl-C 모두 finally에서 해당 고유 프로젝트의 컨테이너와 네트워크를 정리한다. 실패·선택 오류를 성공으로 바꾸지 않으며 cleanup 실패도 비정상 종료한다. 강제 종료·Docker 장애 때는 출력한 프로젝트 이름으로 잔존 자원을 확인해야 한다. 생성한 시험 이미지/빌드 캐시는 재사용을 위해 남으며 자동 prune하지 않는다.

## 결과 해석과 기존 도구

시험은 합성회원·격리 PostgreSQL/FastAPI 근거다. 정상 로그인 사용자·기기·실제 provider·개발/운영 배포 인수가 아니다. 내부 네트워크 차단 때문에 실제 외부 API가 필요한 시험을 이 환경에 섞지 않는다.

`scripts/check_openapi.py`는 기존처럼 지정 실행 컨테이너를 읽는 도구로 유지한다. 실제 개발 반영 후 비교와 새 소스 후보의 격리 계약 비교는 별개다.

`scripts/verify.py`는 DB probe 쓰기와 컨테이너 재생성을 포함하는 환경 복구시험으로 유지하며 이 실행기에서 호출하지 않는다. 개발·운영 환경 상태 확인 명령으로 사용하지 않는다. 이번 작업에 CI 자동 게시·배포는 포함하지 않았다.

## 이번 도입의 확인 결과

호스트 안전성8건·기본 인증34건·최신 아이템레벨18건을 실행해 통과했다. 기본/two-cycle 생성 OpenAPI 전체 객체 비교도 통과했다. 의도적 잘못된 node의 exit4 및 실패 후 cleanup을 실제 확인했다. 내부 네트워크·tmpfs·호스트 포트/마운트 부재를 읽기 확인했고 종료 후 시험 컨테이너/네트워크가 남지 않았다. 전체 legacy/two-cycle 묶음 및 all은 이번에 실행하지 않았다. 상세 실패/수정·경고와 미실행 범위는 [DEV_LOG](../../project/DEV_LOG.md)에 보존한다.
