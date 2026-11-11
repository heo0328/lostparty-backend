# Backend 태그 기반 Lightsail 배포

이 문서는 자동 배포의 현재 운영 기준 원본이다. Backend 버전은 `VERSION`, 태그는 `vMAJOR.MINOR.PATCH`이며 Native·OpenAPI 버전과 독립적이다. 목적 브랜치 → dev → main 통합을 유지한다. 사용자가 승인한 태그 push가 운영 배포 승인이다. 별도 간소 배포 시스템은 두지 않고 동일 배포에서 검증 범위만 바꾼다.

**개발·검증은 로컬 dev가 기본이며 운영 반영 여부·시점은 개발자가 지시한다.** 아래 절차는 운영 반영을 준비하거나 승인된 배포를 수행할 때 적용하며, 기능 수정 요청마다 실행하지 않는다. 로컬 실행 중단을 이유로 수동 배포 워크플로의 검증 경로로 임의 대체하지 않는다. Backend의 반영 시점 제안·대안 판단은 [로컬 개발과 운영 반영](../development/workflow.md#local-dev-and-production)을 따른다. 네이티브 debug는 로컬, release는 AWS를 대상으로 하며 앱 연결과 서버 반영 완료를 구분한다.

## 현재 적용 상태와 변경 이력

- **운영 최신 v2.0.0**: 사용자 승인 PR45·source51b1cb3·imagef33f4c6c·DB0035, Actions41674801953/production Deployment7524537038 success로 한국2026-11-04 01:31:59 반영 완료. 이슈41 일괄 API·이슈42 참가 유지 예방 수정을 지원한다. [최신 배포 집계](records/backend-v2.0.0-deployment.json)·[Issue34 전체13번째 Backend 운영 결과](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6609667274)를 따른다. 아래 v0.1.x는 과거 기록이다.

- 이전 운영은 v0.1.2/source2c6070c/image7c8b8db9·DB0035다. 사용자 승인 이번 한정 재사용·Actions41608259484 success로 한국2026-11-03 18:07:53 반영 완료, [최신 배포 집계](records/backend-v0.1.2-deployment.json)를 따른다. v0.1.1/source77c9de2/image259e8234는 UTC2026-11-01T16:30:33Z 첫 자동 반영 당시 이력이다. [배포 집계](records/backend-v0.1.1-deployment.json)·[전체9번째 Backend 결과](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6560737194)를 따른다.
- 이번 개선은 작업 브랜치의 selected/full 검증·validation.json 기록이다. scripts52PASS·수동 전체1811PASS/검증artifact 대조를 완료했다([검증 집계](records/backend-validation-scope-verification.json)). 로컬 selected 실DB 실행은 엔진 불가로 미완료이며 선택분기/실패 차단은 단위 검증했다. 통합/수동 검증 상태는 [NEXT_WORK](../../project/NEXT_WORK.md)를 따른다. 원격 코드 게시·dev/main 통합·새 태그 배포는 구분한다. 이 문서 수정만으로 운영에 반영되지 않는다.
- 과거 OIDC 제한/전용SSH 전환·초기 시험은 [준비 집계](records/backend-release-preparation.json), v0.1.0 실패/태그 충돌은 [첫 태그 시험](records/backend-first-tag-trial.json)에 보존한다. 예전 준비/미실행 상태를 현재 상태로 해석하지 않는다.

## 사용자가 할 일

| 변경 | 요청 예시 | Backend 담당의 대응 |
|---|---|---|
| 문서·주석만 수정 | “문서 수정까지 정리해주세요.” | 문서 검사·통합. 서버 배포 태그 불필요 |
| 특정 API의 작은 수정·독립 기능 추가 | “관련 검증으로 배포 준비해주세요.” | 누적 변경 영향 검토·관련 테스트 선택·버전/검증 계획 준비 |
| 인증·권한·공통 구조 변경 | “전체 검증으로 배포 준비해주세요.” | 전체 회귀·호환성 검토·버전/검증 계획 준비 |
| DB·운영 구성 변경 | “운영 반영 계획부터 검토해주세요.” | 백업·복구/수동 적용 계획과 영향 제시. 별도 승인 전 변경 금지 |

1. 기능 수정을 요청하면 Backend 담당이 목적 브랜치에서 구현하고 로컬 dev 환경에서 변경에 필요한 개발 검증을 수행한다. 새 테스트는 재발 방지·복잡한 동작 확인이 필요한 경우에 추가하며 단순 수정마다 의무적으로 만들지 않는다. 이 단계만으로 버전·태그·배포 워크플로 실행을 시작하지 않는다.
2. 배포 준비 시 담당이 **변경 내용 / 검증 모드·실행 검사 / 버전 / DB·설정 변경 여부**를 짧게 보고한다. 사용자가 테스트 파일이나 설정을 직접 작성할 필요는 없다.
3. 사용자가 통합·해당 버전 배포를 승인하면 목적 브랜치→dev→main으로 통합하고 같은 main/dev 기준에서 승인 태그를 게시한다. commit/push의 상시 승인은 merge·태그·배포의 상시 승인이 아니다.
4. 자동화가 선택된 검증·이미지 게시·서버 반영·결과 기록을 수행한다. 담당은 실행 결과와 실제 서버 결과를 구분해 보고한다.

일반 selected/full 배포는 태그에서 선택 검증을 한 번 수행한다. 아래 v0.1.2 및 v2.0.0 사용자 승인 예외 외에는 과거 CI 결과를 재사용하지 않으며 파일별 테스트 자동 선택은 포함하지 않는다. patch 버전·변경 줄 수·API 추가라는 이유만으로 관련 검증을 선택하지 않는다. 권한이나 공통 영향이 있으면 전체 검증이다.

## 이번 v2.0.0 한정 로컬 검증 재사용

2026-11-04 개발자가 현재 main의 운영 반영과 Native와 같은 `v2.0.0` 버전, 기존 로컬 검증 기록·소스 일치를 확인한 이번 한정 재사용을 명시 승인했다. 승인 main은 `aa23939c9e66332dd40ff39a025f2480178191a3`, 최종 검증 소스는 `0207d0f6b9ef8734e67bbbdc0701ce75fbdc9c8c`다. 둘 사이 비문서 변경이 없어야 하고, 릴리즈 준비에서는 문서·VERSION·계획·검증 제어 파일만 허용한다. 원본 [Issue41 검증](../../features/rosters/bootstrap/startup-batches-verification.json) 고유144PASS와 [Issue42 검증](../../features/recruitment/membership-actions/activity-continuity-verification.json) 고유57PASS를 고정 SHA256으로 확인해 validation.json에 원문과 출처를 보존한다. 기존 검증·후속 Flutter 기기 인수와 이번 신규 실행을 구분한다.

mode=`reuse`·schema2·executed_tests=[]이며 회귀/계약은 reused, 이번 배포 제어 Docker 교체/복귀 시험은 skipped다. 새 전체 CI 통과 또는 기존 v0.1.1 전체 검증이 새 기능까지 검증했다고 주장하지 않는다. 재사용 확인 코드의 단위 검사, 소스/버전·빌드·불변 게시·DB0035 호환·API만 교체·health/실패 복귀는 유지한다. DB migration·키/환경 변경·기존 review 복구 없음. 다음 버전은 별도 승인 없으면 selected/full이다. 아래 v0.1.2는 과거 승인 기록이다.

## 이번 v0.1.2 한정 검증 재사용

2026-11-03 사용자가 main b649ccf의 그룹 초대 수정 운영 반영과 중복 전체 테스트 생략을 지시하고, 이번 배포에 필요한 범위의 재사용만 승인했다. mode=`reuse`는 **v0.1.2만 허용**한다. 기존 성공 run41417066498/attempt1/sourcefdd51c8·artifact13130595536/validation.json SHA256을 코드에 고정했다. 검증 소스→승인 main 사이에는 문서 변경만, 승인 main→릴리즈 소스 사이에는 문서와 명시한 VERSION/계획·재사용 제어 파일만 허용하고 앱·DB·의존성·테스트·서버 제어 변경은 거절한다.

공식 GitHub run 성공·repo/source·artifact 귀속/만료 여부와 원본 바이트 hash·전체 테스트 목록을 대조한다. 새 스크립트 단위 검사는 실행하되 앱 회귀·계약·Docker 교체 시험은 다시 실행하지 않는다. 이번 validation.json은 schema2/신규 executed_tests=[]·관련 checks=`reused`로 기록하며 원본 검증 JSON과 출처를 함께 저장한다. 과거 통과를 이번 실행으로 합산하지 않는다. 일반 모드의 기존 schema1 기록은 유지한다.

이 기능은 상시 검증 생략 옵션이 아니다. 다음 버전은 selected/full을 사용하고 별도 재사용 정책 확장 승인이 없으면 reuse를 거절한다. 이미지 빌드/불변 게시, 소스/버전 확인, DB·구성 보호, API만 교체·health 확인·실패 복귀는 기존 경로 그대로다. 운영 DB migration·환경/키 변경은 포함하지 않는다.

## 검증 계획 작성

루트 `release-validation.json`을 태그 소스와 함께 고정한다. 파일이 **없으면 full**, 있지만 잘못됐으면 게시 전에 중단한다. 담당은 VERSION을 바꿀 때 계획의 version도 함께 바꾼다. 현재 파일은 사용자 승인 v2.0.0 한정 로컬 reuse 계획이다. 기존v0.1.1 태그는 보존하며 재사용하지 않는다. 후속 승인 릴리즈는 새 버전과 selected/full 계획을 정한다.

관련 검증 작성 예시(예시 값이며 실제 선택은 변경 영향에 따라 결정):

```json
{
  "version": "0.1.2",
  "mode": "selected",
  "baseline_tag": "v0.1.1",
  "change": "특정 레이드 공개 조회의 제한된 오류 수정",
  "impact": "공개 조회 한 기능. 인증·모델·DB·공통 코드 변경 없음",
  "reason": "해당 기능과 직접 연결된 기존 테스트로 검증 가능",
  "tests": ["tests/test_raid_catalog.py"]
}
```

예시의 테스트 파일은 실제 존재 여부와 해당 작업의 연관성을 확인해 선택한다. full은 같은 필드에서 mode를 `full`, tests를 `[]`로 지정한다. change/impact/reason은 비밀·회원정보 없는 설명만 넣는다.

- tests는 저장소 tests 아래 실제 `test_*.py` 파일 경로만 허용한다. selected는 최소 하나, full은 빈 배열이다. pytest 옵션·노드·명령·와일드카드·중복·심볼릭 링크는 거절한다.
- baseline_tag는 **이전 운영 릴리즈**다. 게시된 정식 GitHub Release이며 현재 소스의 조상인지 자동 확인한다. 담당은 최신 성공 production Deployment/source와 직접 대조해 현재 운영 이후 누적 변경 전체를 검토한다. 단지 직전 Git 태그나 직전 작업 커밋을 기준으로 좁히지 않는다. 자동화가 최신 운영 태그를 자동 추론하는 기능은 이번 범위에 없다.
- 알 수 없는 영향·다수 기능에 걸친 리팩토링이면 full이다. 파일이 없는 기본 full은 baseline이 없는 보수적 실행으로 기록한다.

### 전체 검증 필수 범위

자동 방어 경로: `app/auth/`, `app/core/`, `app/main.py`, `alembic/`, `.github/`, `scripts/`, ORM의 `*models.py`, 이름에 permission/authorization/transaction/policy가 있는 app 파일, Dockerfile/Compose/requirements 계열, Python 빌드·pytest 설정과 conftest, `.dockerignore`다. 비교 기준 이후 이 파일이 추가·수정·삭제·이름 변경되면 selected를 거절한다.

이는 영향 자동 판정의 완성이 아니다. 다른 경로에 구현된 권한·공통 트랜잭션·여러 기능 리팩토링도 담당이 full로 분류해야 한다. 차단을 피하려고 비교 기준이나 파일 위치를 바꾸지 않는다.

## 자동 실행과 기록

| 과정 | selected | full |
|---|---|---|
| 태그·VERSION·main/dev·소스 확인 | 실행 | 실행 |
| 의존성/문서/배포 스크립트 단위 검사 | 실행 | 실행 |
| 두 OpenAPI 전체 계약 비교 | 실행 | 실행 |
| 애플리케이션 회귀 | 지정한 파일, 1개 격리 작업 | 전체 파일, 8개 비중복 그룹 |
| 배포 제어 Docker 교체·복귀 시험 | 생략 | 실행 |
| 이미지 빌드·게시 | 실행 | 실행 |
| 서버 사전 확인·API 교체·health·복귀 | 실행 | 실행 |

`.github/workflows/backend-release.yml`은 선택한 검증 작업이 실제 success인지 별도 gate에서 확인한다. 실패·취소·예상 밖 skip을 성공으로 취급하지 않는다. 수동 workflow_dispatch는 동일 계획으로 검증·로컬 이미지 빌드·검증 artifact까지만 수행하며 GHCR/Release 게시·운영 SSH에 접근하지 않는다.

성공 검증은 `validation-<run>-<attempt>` artifact의 validation.json으로 30일 보관한다. 게시 작업이 해당 artifact를 받아 소스 SHA·계획 해시·모드·테스트 목록·결과·동일 run 여부를 확인하고 GitHub Release에 **validation.json**을 추가한다. 기본 release.json·Compose·서버 입력 계약은 유지한다.

validation.json에는 대상 버전/소스 SHA, 계획 파일 SHA256(없으면 null), 모드, 비교 기준, 선택 이유, 실행 테스트 파일 전체, 검사별 성공/생략, UTC·Actions 링크를 남긴다. 실제 테스트 개수는 로그에서 확인하며 단순 파일 목록을 테스트 개수로 부르지 않는다. 소스 통합 / 산출물 게시 / 실제 서버 반영 / 사용자 인수는 계속 구분한다.

## 불변 산출물과 실패 대응

- 태그·VERSION 일치, 최초 게시 시 main/dev 동일 SHA·태그 소스의 main 포함을 확인한다. checkout의 로컬 태그 변형과 충돌하지 않도록 브랜치 갱신은 --no-tags/명시 refspec을 사용한다.
- GitHub 표준 Linux runner에서 linux/amd64 이미지를 빌드한다. GHCR 버전·소스 태그를 덮어쓰지 않고 실제 배포는 digest로 고정한다. 최초 private package는 public/익명 digest 조회를 확인하기 전 배포하지 않는다. 현재 v0.1.1은 익명 조회 확인 완료다.
- 기존 Release 재실행은 원래 이미지·release.json·Compose·validation.json을 재사용한다. 검증 기록을 덮어쓰거나 소급 추가하지 않는다. 이전 검증 기록이 없는 옛 소스의 Release는 읽을 수 있지만 계획 파일이 있는 새 소스의 Release에서 증거가 누락되면 중단한다.
- 코드 수정은 새 VERSION/태그다. 전송·인증/설정 문제는 원인 확인과 수정 후 승인된 같은 태그/이미지를 재실행할 수 있다. 무작정 전체 workflow를 반복하지 않고 실패 작업만 재실행한다. artifact가 만료돼 게시 증거를 읽을 수 없으면 동일 run에서 검증 gate를 다시 수행해야 하며 증거 없이 우회하지 않는다.
- draft 생성·첨부 후 게시한다. 불완전 draft는 자동 덮어쓰기하지 않고 수동 조사한다. 태그 수정/삭제 방지와 production의 v*태그 제한을 유지한다.

## 서버 보호와 별도 운영 작업

전용 SSH·고정 호스트키 검증·강제 명령 계정을 유지한다. Free plan 계정의 OIDC provider 제한으로 사용자 승인 후 전용키를 채택했으며 AWS CLI·GitHub runner를 서버에 설치하지 않는다. production Secret `LIGHTSAIL_DEPLOY_SSH_KEY`, 변수 `LIGHTSAIL_SSH_KNOWN_HOSTS`, 계정 lostparty-deploy/54.253.176.103을 사용한다. 포트 추가 개방·유료 리소스는 추가하지 않는다.

배포 키는 root 소유 authorized_keys의 restrict/강제 명령과 최소 sudo로 submit/preflight/status만 허용한다. 셸·PTY·포워딩은 차단한다. 개인키 등록 시 마지막 LF를 보존한다. 일반 `gh secret set < key`는 끝 CR/LF를 제거하므로 사용하지 않는다. Python에서 개인키 문자열을 JSON 인용한 dotenv 항목으로 만들어 `gh secret set --env production --env-file -`의 stdin으로 전달하고, 제한 preflight를 확인한다. rotation은 새 제한키 추가→접속 확인→Secret 갱신→이전 키 폐기 순서이며 개인키·임시 관리자 인증 복사본은 삭제한다.

서버는 `/home/ubuntu/lostparty-backend`의 env·키를 유지하고 root `/var/lib/lostparty-deploy/current.json`이 가리키는 구성을 사용한다. DB/Caddy/네트워크/볼륨·API 운영환경/명령/mount 변경은 사전 중단한다. 후보 Alembic head와 실제 DB revision 불일치도 API 교체 전에 중단한다. 자동 migration/downgrade는 없다. 전체 테스트 통과가 이 차단을 해제하지 않는다.

이미지 source/버전/amd64·여유디스크3GiB·기존 서비스 상태를 확인하고 pull 후 API만 --no-deps/--no-build/--pull never로 교체한다. 120초 안에 healthy·공개 HTTPS /health200(database ok)·raid-catalog200·미인증 /v1/me401을 확인한다. DB/Caddy ID/시작시각과 env/키/mount 보존을 비교한다. 실패하면 직전 이미지/구성으로 복귀하고 같은 점검을 수행하되 해당 배포는 실패로 기록한다.

GitHub 동시 배포는 취소하지 않고 직렬화한다. 서버 flock/systemd/journal은 SSH 중단과 독립 실행하며 재실행은 저장 결과부터 확인한다. 같은 attempt 입력 변경·이전보다 낮은 버전은 거절한다. 현재·직전 정상 이미지를 보존하고 전체 Docker prune/volume 삭제는 하지 않는다.

운영 환경 변경·DB 변경은 백업/복구와 영향에 대한 별도 승인 후 수행하고 baseline을 재정렬한다. 운영 DB/키·환경/복구 구성의 2026-11-07 서버 밖 PC 사본·무결성 확인은 [백업 원장](backup-and-recovery.md)을 따른다. 실제 복원/정기 자동화는 미실행이며 다음 DB·설정 변경 직전 최신 사본은 별도로 확보한다. 이전 release Google 로그인 인수는 보존하고 실사용 토큰/회원 쓰기로 자동 점검하지 않는다.

## 운영 확인과 검증 근거

서버 상태·최근 로그·API만 재시작은 [짧은 운영 안내](lightsail-quick-ops.md)를 따른다. 배포 결과는 다음처럼 비밀 없는 status로 확인한다.

```bash
sudo python3 /usr/local/lib/lostparty-deploy/server.py status RUN_ID-ATTEMPT
sudo systemctl status lostparty-deploy-RUN_ID-ATTEMPT
```

current.json·동결 Compose·전체 env/inspect·키 원문은 출력하지 않는다. 검증 개선의 테스트·수동 실행 결과는 NEXT_WORK/DEV_LOG와 Issue34에 연결하고, 도입 후 새 운영 태그 시험은 별도 사용자 승인으로 수행한다.
