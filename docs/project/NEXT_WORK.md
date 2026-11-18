# 다음 실행

2026-11-19 서울 Lightsail 배포 연결을 완료했다. `8c57dca`가 dev/main에 반영됐고 GitHub production은 main만 허용한다. [v2.4.0 사전 점검](https://github.com/heo0328/lostparty-backend/actions/runs/44347756030)에서 기존 배포 키를 사용해 `preflight_only` 성공과 DB0038을 확인했다. 점검 후 운영 도메인은 서울 IP에서 HTTPS 정상·DB 정상 응답을 반환했다.

## 다음 실행

시드니 인스턴스 삭제 후 사용자가 시드니 목록에서 대상이 사라지고 서울 인스턴스가 유지된 것을 확인했다. 공개 운영 도메인의 서울 HTTPS·DB 정상도 확인했다. 다음 수정 버전은 승인 후 표준 릴리즈로 게시·배포하고 검증·게시 시간과 배포 시간을 각각 기록한다. [서울 배포 절차](../engineering/operations/backend-release.md#서울-연결-순서).

## 코드·계약·실행 구분

| 구분 | 기준 |
|---|---|
| Git | 서울 배포 연결 코드 8c57dca를 dev/main에 게시. 완료된 feat/production-deployment 정리 후 최종 상태 문서는 dev에 기록 |
| 로컬 실행 | image eadaa2cc…37b9/DB0038·기존개발지원 유지. 개발키 변경/삭제 없음 |
| 명세 | 191경로/211동작, SHA25612634daa64a8c4cbdfecfdb53bc7c1aca3bdb721c5ea555d098aea51544b9665; 이번 API 변경 없음 |
| 운영 | v2.4.0/source970b2f4·DB0038·웹2.4.0+9 공개/사용자 정상 확인 완료 |
| Native | 빌드source84565024/원장f2f1b759, 웹34자산 운영 활성·공개 완료, APK 크기/hash/ZIP검증. APK서명/패키지검증은 동일원본 Native근거 |

완료된 Issue58 복구/사용자 두화면 인수·dev/main 통합 기록은 [DEV_LOG](DEV_LOG.md)와 [이슈 추적표](ISSUE_TRACKER.md)를 따른다. 반복 시험 대기를 만들지 않는다.

## 별도 유효 대기

Issue17 잔여/기기·15 소유권 이전·18 활동 자동추가·19 통계는 별도 후속이다. Issue58 상세 분석 후보가 Issue18 활동 자동추가의 완료/폐기를 뜻하지 않는다. Issue55/56은completed, Issue57은 사용자 직접삭제 완료다.

## 데이터·운영 경계

서울 스냅샷에서 복원된 현재 DB를 기준으로 사용한다. 스냅샷 이후 시드니 변경분은 이관하지 않는다. 이번 준비에는 DB 초기화·마이그레이션, 서버 재설치, 실제 운영 배포가 포함되지 않는다.

<a id="runtime-consolidation-followup"></a>

현재 create_app·DB0038로 개발한다. 과거 migration·동결 명세·배포 원장은 보존한다. [실행 기준](../engineering/development/runtime-configuration.md).

<a id="recovery-backup-closeout"></a>

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 사본/로컬dump 제외 방침을 유지한다. 새토큰의 서버/WSL/기존개인PC사본은 확인됐으며 외장매체·실제복원은 미실행이다.
