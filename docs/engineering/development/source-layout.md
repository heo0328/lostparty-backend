# 앱과 테스트의 폴더 분류

2026-11-09 사용자 승인: 기능별 모듈을 유지하고 큰 기능 내부의 업무 코드와 테스트를 하위 패키지로 분류한다. 이번 구간은 `feat/character-lifecycle` 브랜치를 유지하며, 이전 폴더 이동 보류는 이 승인 범위에 한해 해제됐다.

## 분류 기준

- **업무 기능을 먼저 선택한다.** 작은 기능은 기존 모듈을 유지한다. 파일 개수만을 기준으로 폴더를 추가하거나 모든 기능에 같은 계층을 강제하지 않는다.
- 레이드룸의 업무 코드는 `admissions`(모집·신청·개설/다음주 참가), `participation`(현재 참가·캐릭터 교체·탈퇴·승계), `schedules`(일정·조율·예약), `outcomes`(완료·정정·재개·주간 기록), `group_links`(그룹 연결 정책), `reads`(일반 목록·검색·상세 조회), `compat`(기존 API 호환), `common`(공통 정책·주차·실행/worker)으로 분류한다. `cycle_` 접두사는 업무 기능 분류를 대신하지 않는다.
- 게임 계정은 `rosters`(등록·원정대 갱신·저장 조회), `verification`(소유/장비 인증), `character_profiles`(활동·대표·개인 설정), `power`(전투력), `provider_io`(공급 API)로 분류한다.
- 이름과 업무 로직은 그대로 유지한다. 다른 기능도 실제 사용하는 코드를 과거 버전 접두사만으로 호환 폴더에 넣거나 삭제하지 않는다. 새 서비스/Repository 계층·무분별한 공통 유틸을 만들지 않는다.

## 2차 정리 — 정의·HTTP·ORM·계약 자원

2026-11-09 사용자 지시로 1차 개발 현황/정리를 `34a2a47`에 로컬 커밋한 뒤 [2차 계획](source-layout-phase2-plan.md)을 실행했다. 대상 두 기능의 루트에는 `__init__.py`만 두고 HTTP 경계는 `api/`, 입출력/검증/동적 DTO 생성은 `schemas/`, ORM 정의는 `models/`, OpenAPI 조립과 JSON 자원은 `contracts/`로 분류한다. 게임 계정의 공유 권한/잠금/멱등 처리만 `common/support.py`에 둔다. 작은 다른 기능·프로젝트 진입점·DB migration 이력은 이동하지 않는다. 전체 회귀는 최종 고유1921PASS/기존2FAIL·신규 미해결0으로 완료했다. 실제 상태는 [다음 실행](../../project/NEXT_WORK.md)을 따른다.

파일명·함수·클래스 이름은 유지한다. `models/models.py`·`schemas/schemas.py`는 의도한 배치이며 이번에 이름을 다시 정리하지 않는다. 혼합 모듈15개는 DTO/ORM/HTTP/업무 책임별로 나누고 요청 ContextVar와 ORM 클래스는 각각 한 정식 모듈에서만 생성한다. DTO validator/타입 생성 함수는 DTO와 함께 두며 worker·트랜잭션 책임은 유지한다. 비어 있는 기존 경로 호환 파일/루트 재수출·새 서비스 계층은 만들지 않는다.

기존 공개 OpenAPI 모델 식별자는 `contracts/schema_ids.py`의 명시적 모듈 대응으로 유지하며 기존 장식 코드보다 먼저 적용한다. component key/참조만 보정하고 예시·업무 문자열·실제 모델 identity는 바꾸지 않는다. 이동 전후 두 전체 객체 일치가 필수다. 모델 import는 실제 정식 모델 모듈로 등록하고 과거 migration을 수정하지 않는다. 연결 JSON은 계약 코드 옆에 둔다. [2차 대응표](folder-layout-phase2-map.json)·[검증 기록](folder-layout-phase2-verification.json)은 1차 원본과 분리하며 새 파일 추가 때는 해당 책임을 먼저 선택한다.

## 현재 파일을 찾는 순서

1. 기능과 책임을 먼저 고른다. HTTP 진입은 `api`, 입력/출력 정의는 `schemas`, DB 정의는 `models`, 계약 보정/자원은 `contracts`, 실제 처리 함수는 위의 기능별 업무 폴더에서 찾는다. 시험은 `tests/<기능>/` 하위에 있다.
2. 예전 경로만 알고 있으면 [1차 이동표](folder-layout-map.json)의 이전/이동 경로를 검색한다. 해당 항목이 없거나 공개 정의/모델 파일이라면 [2차 대응표](folder-layout-phase2-map.json)의 `entries[].source`를 찾고 `targets`를 확인한다. 1차 원본의 경로를 무조건 최종 위치로 간주하지 않는다.
3. 한 파일이 분리된 경우 파일명만으로 import를 바꾸지 않는다. [2차 계획의 파일별 표](source-layout-phase2-plan.md#파일별-대응표)에서 책임별 대상을 보고, 2차 대응표의 `symbol_mapping`에서 기존 모듈+클래스/함수 이름으로 정식 경로를 확인한다. 정의되지 않은 새 심볼은 실제 소스를 확인한다.
4. 문서와 코드가 다르면 실제 정의·참조를 확인하고 현재 안내/대응표를 함께 갱신한다. 과거 커밋·검증 원본은 소급 수정하지 않는다. 새로운 이동이 생기면 별도 이동 기록을 연결하고 현행 안내를 갱신한다.

예를 들어 옛 `app/raid_rooms/cycle_continuation.py`는 현재 [다음 주 참가 업무 코드](../../../app/raid_rooms/admissions/cycle_continuation.py)에 있다. 옛 `completion.py`는 [업무 함수](../../../app/raid_rooms/outcomes/completion.py)와 [DTO 정의](../../../app/raid_rooms/schemas/completion.py)로 나뉘었다. 같은 파일명이 여러 폴더에 있어도 역할이 다르므로 함수/클래스 이름까지 확인한다.

```bash
rg --files app/raid_rooms app/game_accounts tests
rg -n 'def complete_assignment|class ContextRequest' app/raid_rooms
```

[AGENTS](../../../AGENTS.md) → [개발 흐름](workflow.md)에서 이 기준으로 연결한다. 새 채팅은 NEXT_WORK·AI_CONTEXT의 현재 상태를 먼저 보고, 과거 이력의 경로나 미착수 문구를 현행 지침으로 적용하지 않는다. 옛 Python import용 호환 파일은 없으므로 새 코드는 정식 하위 모듈을 직접 import한다.

## 테스트와 참조

- 테스트는 앱 기능과 대응하는 하위 패키지에 배치한다. 레이드룸은 그 안에서도 업무 기능별로 분류한다. 같은 파일의 함수/fixture는 그대로 두며, 이번에는 시험 코드와 fixture를 별도 도우미 계층으로 추출하지 않는다.
- 기존 파일명과 test node suffix는 유지한다. import, monkeypatch의 문자열 대상, 실행 도구와 현재 문서의 참조는 이동 경로에 맞춘다.
- 전체 시험 발견은 `tests` 아래 재귀 검색을 사용한다. `legacy`·`two-cycle` 묶음의 시험 구성은 유지하며 정확한 파일/허용된 묶음 검사와 경로 탈출 방지를 완화하지 않는다.
- 과거 실행 기록·고정 SHA 링크·동결 JSON은 당시 기준으로 보존한다. 보관 문서의 깨지는 로컬 링크는 링크 목적지만 수정하며 본문과 수치를 재작성하지 않는다. 현재 문서 색인의 dependency 경로는 새 위치를 가리킨다.

## 1차 이동의 원본과 검증

[파일 이동 대응표](folder-layout-map.json)는 이동 전 커밋/브랜치·고정 모듈·198개 파일의 이전/현재 경로를 기록한다. 업무 모듈95개와 시험 파일103개를 이동했으며 공개 정의/진입점79개는 기존 위치를 유지한다. 새로운 하위 패키지의 `__init__.py`는 빈 파일로 둔다.

검증 결과 원본은 [폴더 정리 집계](folder-layout-verification.json)에 기록한다. 이동 전/후 수집1916개를 경로 역대응으로 비교하고, 기존 UUID1 생성 파라미터1개만 값 대신 같은 사례로 비교한다. 업무/테스트349 Python 파일의 import와 경로 참조를 제외한 AST를 비교하며, session-display 도구의 파일 깊이 참조1곳은 별도로 기록한다. 두 OpenAPI 전체 객체와 DB 모델 등록을 검증하고 격리 PostgreSQL 전체 업무 회귀·도구 시험 결과를 구분한다.

구조 정리의 완료와 commit/push·실제 개발서버 반영·Native 기기 인수·운영 반영은 별도다. 기존 개발 이미지의 파일 경로/hash를 정리 후 로컬 소스와 같다고 표시하지 않는다.

## 1차 완료 결과와 기존 실패

전체1916사례를 초기 실행과 독립 PostgreSQL4묶음의 합집합으로 확인했다. 최종 고유1914PASS·기존 기대값 불일치2FAIL이며 모두 통과했다고 표시하지 않는다. 초기1010PASS/2FAIL·1371.44초에서 나머지를 분할했고,4묶음은230PASS/230PASS/229PASS/228PASS+1FAIL이다. 파일 경계14중복과 수정 후 단일 재실행을 합산하지 않는다. 분할 실행시간은 각각1715.69/1527.29/1672.93/2484.42초다. 시험용 DB와 network는 모두 정리됐다.

- 이동으로 누락된 subprocess 문자열 import는 참조를 고쳐 강제 종료/부분 저장 복구1PASS로 확인했다. 업무 동작과 시험 기대는 유지했다.
- 그룹 탈퇴 뒤 활동 해제가 기존 참가를 거절해야 한다는 기대, stopped 상태 뒤 캐릭터 미선택 개설을 허용해야 한다는 기대의2사례는 이동 전 이미지에서도 각각 동일 실패했다. 이 정리에서 제품 정책이나 기존 기대값을 임의 수정하지 않았고 후속으로 남긴다.
- 도구63PASS·앱256모듈 import·349파일 업무/시험 AST 보존·ORM116개 등록/DDL·두 전체 계약 일치·문서/동결 기록 검증을 확인했다. 최종 시험 이미지의 앱/테스트/도구413파일은 현재 소스와 같다.

위 문단은 1차 정리 당시 결과다. 후속 사용자 지시로 1차34a2a47과 2차 구현/문서6a87e14를 같은 작업 브랜치에 커밋·push했다. 게시 상태 기록은 후행 문서 커밋으로 남기며 현재 실행/반영 상태는 NEXT_WORK를 따른다. 실제 개발서버/DB·운영/Native 기기에 자동 반영하지 않는다.
