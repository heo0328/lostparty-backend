# 검증된 Python 패키지 고정

현재 적용: 2026-10-25 [개발 서버 반영](../operations/backend-improvements-rollout.md)을 완료했다. source87c2a0e/이미지366e868a·177/DB0031이며 고정패키지·API/DB 로그10m×5가 실행 중이다. 아래 미반영/별도 반영 설명은 구현 당시 이력과 후속 변경 절차로 구분한다.

2026-10-25 통합: 이 문서의 개선 결과는 사용자 지시로 `feat/raid-recruitment`에 병합했다. 현재 checkout도 해당 모집 브랜치이며 아래 별도 개선 브랜치는 작업 당시 이력이다. 로컬 병합은 미push이고 실제 개발 서버 반영은 별도다.

2026-10-25 / 작업 구간명: 검증된 직접·전이 의존성 고정.
브랜치: `chore/backend-architecture-review`. 기존 개발 API의 설치 목록을 읽기 확인하고 후보 이미지에서 고정 설치를 검증한다. 실제 개발 API 교체·배포·DB 작업은 포함하지 않는다.

## 기준과 적용

- 실행 중인 아이템레벨 보완 API(sourcef471e31/이미지6d5857b3)의 패키지31개(pip 제외)를 [requirements.txt](../../../requirements.txt)에 정확 버전·wheel SHA256으로 고정했다.
- 첫 개선에서 인증34건을 통과한 시험 이미지 `lostparty-check-95452e4ee27c-tests`의 시험 전용12개를 [requirements-dev.txt](../../../requirements-dev.txt)에 추가했다. runtime lock을 포함하므로 시험 환경도 실행 패키지는 동일하다.
- 비교 당시 시험 이미지의 certifi2026.10.23/pycparser3.12는 개발 API의2026.10.19/3.11과 달랐다. 시험 환경의 두 버전을 실행 기준으로 맞춘다. runtime 패키지의 업그레이드는 없으며 이 차이는 고정 이후의 격리회귀로 확인한다.
- 원래 직접 의존성10개/시험3개는 [requirements.in](../../../requirements.in)과 [requirements-dev.in](../../../requirements-dev.in)에 보존했다. 패키지 관리 도구를 교체하거나 새 runtime 라이브러리를 추가하지 않았다.
- `psycopg[binary]`/`PyJWT[crypto]` extras와 그 의존성도 유지한다. 해시는 같은 버전의 배포 wheel을 별도 컨테이너에서 다운로드해 계산했다. 과거 이미지에 설치한 원본 wheel의 바이트를 회수해 입증한 것은 아니며 기존 설치 **버전**과 일치하는 배포물을 고정한 것이다.

## 빌드·검증

두 Dockerfile 모두 다음 순서를 강제한다.

1. 직접 요구와 lock의 버전/extras 일치·정확 버전/해시 존재·시험 lock의 runtime 덮어쓰기 금지를 검사한다.
2. `pip install --require-hashes --only-binary=:all:`로 전체 의존성을 설치한다. 새로운 미고정 전이 패키지나 해시 불일치는 실패한다.
3. `pip check`와 `check_dependencies.py --installed runtime|test`로 의존성 호환성과 설치 목록 전체 일치를 확인한다.

호스트에서 `python3 scripts/check_dependencies.py`는 파일 정합성만 읽기 검사한다. `verify_isolated.py static`에도 포함됐다. 호스트의 Python 패키지를 설치·변경하지 않는다. `--installed`는 해당 Docker 이미지 안에서 사용하며 호스트 환경과 맞추는 옵션이 아니다. 실제 wheel 해시 검증은 pip 설치 단계의 책임이다.

기존 격리 검증 명령과 iOS API 사용법은 그대로다. 설치 기반을 바꾼 후보의 두 OpenAPI 비교·인증/최신 모집 대표회귀는 DEV_LOG의 실제 결과를 따른다. 버전 고정은 모든 기능 통과나 보안 취약점 감사 완료를 뜻하지 않는다.

## 지원 범위·업데이트

현재 lock의 native wheel 해시는 **CPython3.12 / Linux amd64 / Debian bookworm(glibc)** 기준이다. macOS·Windows·ARM 직접 설치 지원을 주장하지 않는다. 다른 대상에 필요한 wheel은 해당 환경에서 별도로 확보·해시 검토·시험 후 추가한다. 해시 검증을 끄거나 source build로 조용히 우회하지 않는다.

pip는 Python base image의 빌드 도구라 앱 패키지 목록에서 제외했다. Python/OS/base image tag·PostgreSQL 버전은 이 작업에서 추가 고정하지 않았다. 따라서 패키지 고정과 이미지 전체의 바이트 재현은 구분한다. 배포물 자체의 식별은 기존 이미지 digest/반영 기록을 따른다.

보안 수정·지원 종료·필요 기능으로 업데이트할 때는 다음 흐름을 사용한다.

1. 직접 요구 변경은 .in에 기록하고, 전이 패키지만 바꾸는 경우에도 목적과 영향을 남긴다.
2. 별도 CPython3.12/Linux amd64 후보 환경에서 기존 lock을 기준으로 필요한 버전만 선택한다. 현재 실행 컨테이너에서 pip install/freeze로 작업하지 않는다.
3. 선택한 전체 버전의 wheel을 `pip download --only-binary=:all: --no-deps`로 임시 디렉터리에 받아 SHA256을 계산하고 lock을 갱신한다. 패키지명/버전/추가·제거와 runtime/test 공유 관계를 검토한다. 이것은 새 lock 작성 절차이며 기존 해시를 무작정 다시 신뢰하는 자동 갱신이 아니다.
4. 새 이미지의 hash 검증·pip check·설치 목록 검증,두 계약·변경 영향 회귀를 통과한 뒤 커밋한다. 실제 API 교체/운영 배포는 별도 승인 범위를 따른다.

다운로드 파일이 사라지면 동일 버전이라도 빌드는 실패할 수 있다. 배포가 필요한 시점의 이미지/배포물 보관으로 대응하며 이번 작업에서 wheel 저장소를 새로 운영하지 않는다.

방식의 근거는 [pip 재현 설치](https://pip.pypa.io/en/stable/topics/repeatable-installs/)와 [hash 검사](https://pip.pypa.io/en/stable/topics/secure-installs/) 공식 문서다.

## 이번 적용 검증

runtime31/test43 패키지의 해시 검증 설치·pip check·설치 목록 일치 모두 통과했다. runtime 후보의31개 이름/버전은 실행 중인 API에서 읽은 기준과 전부 동일했다. 신규 lock 검사4건을 포함한 호스트12건·인증34건·아이템레벨18건과 두 OpenAPI 전체 객체 비교를 통과했다. 합성 잘못된 SHA256도 실제 pip가 exit1로 거부했다. 전체 회귀 묶음/all·실회원/기기·보안 취약점 감사는 미수행이다. 실제 개발 API는 교체하지 않았다. 상세 근거는 [DEV_LOG](../../project/DEV_LOG.md)를 따른다.
