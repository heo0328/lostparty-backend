> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [operations](../../../../engineering/operations/README.md). [문서 대응표](../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# Issue #8 — 기존 자료 보존 전환 계획 폐기

> **2026-10-16 실행 기준 정정:** [최신 지시](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207542428)에 따라 현재 사용하던 환경과 개발자료로 개발을 계속한다. 아래 별도8001 구성·채택/기본 재인수 안내는 작업 이력이며 현재 실행 순서가 아니다. 별도환경 삭제/재설정도 실행하지 않는다. 현재 필요한 기능별 schema/API 작업과 개발자료 초기화를 구분한다. Flutter 별도DB/키 연결은 원래 연결로 복구됐고 최종1524PASS다.

2026-10-16 사용자 지시에 따라 **현재 테스트 자료와 기존 Firebase 시스템은 폐기 대상으로, 새 시스템에 승계하지 않는다.** 기존 테스트 DB 백업→격리 복원→기존 행 보존 migration 리허설을 필수 선행으로 삼은 이 문서의 실행 계획은 폐기했다. 실행 명령과 완료 조건도 제거했다.

원인은 Backend가 자료 폐기 전제를 적용하지 않고 일반적인 기존 데이터 보존 절차를 이번 전환에 확대 적용한 판단 오류다. Flutter의 P1/P2 요청에는 신규 DB 구조를 정의하는 additive migration 코드와 격리 테스트가 포함됐으나, 이 백업/복원 리허설을 요청한 것은 아니다.

Firebase 자료 이관 코드는 구현하지 않았다. 0007~0009는 신규 PostgreSQL API의 테이블/제약을 만드는 Alembic schema 변경 파일이며 Firebase 이전과 다르다. 해당 파일의 향후 정리 여부와 새 DB 초기 구성 방식은 기존 테스트 자료를 승계하지 않는 기준으로 다시 검토한다. 이 폐기 지시를 기능/API 전체 취소나 실제 데이터 즉시 삭제로 확대하지 않는다.

확인한 현재 상태는 API/DB healthy, DB0006_provider_limits, 실행 API cd3e003 계약 일치·V2 경로0개다. 실제 테스트 DB dump/격리 복원/0007~0009 실제 적용·Firebase 접근/자료 이관·서버 재시작·데이터 삭제는 수행하지 않았다.

다음 작업의 기준은 기존 테스트 자료를 보존·복원하는 업그레이드가 아니라 **새 DB 구성과 최신 API를 이용한 새 사용자 테스트 환경 준비**다. 현재 발언에서는 설계 폐기/경위 설명만 수행하고 원본 DB/볼륨/Firebase/기기 데이터는 조작하지 않는다.

[사용자 방침 Issue 전달/Flutter 영향검토 요청](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6206662757) 게시 완료. Flutter의 구자료보존/legacy 의존 영향 회신 후 새 환경 작업 구간을 정리한다.

## 단계 정책 재확인

[Flutter 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6206739088) 기준으로 개발중자료생성/삭제·베타직전개발기록전체초기화·베타자료운영승계다. 지금즉시전체삭제로확대하지않는다. D 구의존정리는계획단계/새P2계약변경요청없음. [Backend 추가 확인](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6206816156)으로새회원실소유/canonical선행인수와현재가능한기본흐름을구분요청했다. liveproof보류는새DB/플래그ON만으로해소되지않으며독립구성준비는진행가능하다.

## 제품/UX 검토 수용

[Backend 검토 회신](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207049997)으로Flutter6206873992/6206946439를수용했다. 기능/비로그인UX유지·Firebase전용구현제거이며로컬DB/정수ID/순수mapper자체폐기가아니다. canonical인수확인은해소됐고현재추가질문/P2계약변경없음. D/새DB준비는독립진행가능, 실제소유proof보류는별도후속이다.

## 새 빈 개발 환경 구성 완료 — 기존 환경과 분리

사용자 두 구간 진행 지시/[우선순위 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6207154064)에 따라 `compose.yaml` + `compose.fresh.yaml`로 새 프로젝트 `lostparty-fresh-dev`를 구성했다. 위의 폐기 이력과 달리 이번 구간은 실제 새 환경을 생성·시작했다.

- 새 volume `lostparty-fresh-dev_postgres_data`, 별도 network, API `http://127.0.0.1:8001`. 원본 DB/volume/8000 API는 유지했다.
- 신규 DB에 Alembic `upgrade head`를 적용하여 `0009_personal_presentation` 확인. Firebase/구 DB import·dump/복원은 없다. 0001~0009는 새 PostgreSQL 구조를 만드는 데 사용했다.
- 새 API/DB healthy, 호스트 8001 `/health`는 status/database 모두 ok. 실행 OpenAPI는 P2 `7027f0b` 원본과 전체 일치한다.
- 사용자·등록·캐릭터·역할요약·개인설정·원정대 표시 테이블 각 0건 확인. 신규 환경은 기존 로컬 `.env`/`.secrets`의 인프라 설정을 사용하지만 기존 사용자/게임 자료를 복사하지 않는다.
- 원본 API/DB도 healthy, DB는 기존 `0006_provider_limits` 유지. 원본 서버를 P2로 교체하지 않았다. 새 포트는 loopback이며 모바일/에뮬레이터 경로는 별도 확인해야 한다.

동일 환경 재시작(자료 유지):

```bash
docker compose -f compose.yaml -f compose.fresh.yaml up -d --wait db api
```

새 머신의 최초 구성은 API 이미지 빌드 후 DB 시작 → 아래 구조 생성 → API 시작 순서다. 이미 생성된 환경을 빈 DB로 되돌리는 명령이 아니다.

```bash
docker compose -f compose.yaml -f compose.fresh.yaml build api
docker compose -f compose.yaml -f compose.fresh.yaml up -d --wait db
docker compose -f compose.yaml -f compose.fresh.yaml run --rm --no-deps -T api alembic upgrade head
docker compose -f compose.yaml -f compose.fresh.yaml up -d --no-deps --wait api
```

새 환경만 중지할 때는 같은 파일 순서로 `stop`을 사용한다. volume 삭제·베타 직전 초기화는 이번 실행에 포함하지 않았다. 새 환경 준비는 실제 소유 증거 보류를 해제하지 않는다. [소유 관찰 도구](ISSUE_8_OWNERSHIP_READINESS.md)는 준비했고 사용자 결정에 따라 실제 검증은 나중에 진행한다. Flutter 기본 로그인/키/설정/preview와 보류 안내 인수, D 실기기 확인 및 게시 SHA는 다음 구간이며 아직 통과로 기록하지 않는다.

## 기존 개발 서버 반영 완료

2026-10-16 사용자 진행 지시에 따라 기존8000/기존DB를 유지해 0006→0009 구조와 최신P2 API를 반영했다. 기존자료 동일·모델/DB정합·health/계약을 확인했다. 별도8001을 채택하거나 원본자료 초기화·백업/복원·import를 하지 않았다. 이 문서의 별도환경 구성 명령은 과거 작업이력으로만 유지한다. 다음은 현재 서버에서 남은 기능 개발이며 기존 정상 기능 전체 재인수가 아니다.
