# 다음 실행

2026-11-18 B8: 사용자가 release/2.4.0 누적변경 commit/push 및 해당source의 수동 full CI 실행을 명시 승인했다. 지금 게시/검증을 진행하며 merge·태그/Release·GHCR공개·운영반영은 승인범위가 아니다. 정확한 source/run/원격확인은 후행 DEV_LOG와 게시영수증을 따른다. 아래 B7 미게시는 당시 상태다.

2026-11-18 Issue59 B7: 실제운영Dockerfile 기반 합성이미지로 관리자 CLI/API/PostgreSQL/Caddy 전체통합을 완료했다. 실패후0036복원/구웹재개,0038후보완료후복귀,공동승인공개와probe실패503재차단·실제구/신웹HTML·mount된합성5키보존/정리 PASS. 도구/namespace23시험·정적115PASS. [전체18 Backend B7](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6952581457)·[통합영수증](../engineering/operations/records/release-2.4.0-reset-integration.json)·[실행안](../engineering/operations/release-2.4.0-reset-runbook.md). 임시시험Git/image는운영source/digest가아니며프로젝트HEAD18e6bb6은불변이다. release/2.4.0 미커밋·미push, 새reset도구운영설치/실행·실제초기화/서비스교체/공개없음.

## 다음 실행과 게시 경계

1. 사용자 명시승인으로 release/2.4.0 누적변경 commit/push와 수동 full CI를 진행한다. 누적 VERSION/검증·게시경계/백업·reset도구/회귀fixture 보완과 기록은 같은 release/2.4.0에 모여 있다. 일반 작업 진행은 게시 승인이 아니므로 현재 로컬에 유지한다. 임시시험저장소 commit을 프로젝트 이력/출시 source로 대신하지 않는다.
2. 승인된 게시 범위에서 기준source를 고정하고 release-validation full대로 CI와 불변GHCR이미지/Release를 확보한다. 현재 운영Dockerfile의 로컬 합성빌드·통합은 검증됐지만 실제release source/digest는 없다. 태그/Release·이미지공개·merge는 각 지시 범위를 확인한다. publish-only는 실제운영 자동배포를 차단한다.
3. 실제운영반영 승인/유지보수 구간에서 최신 DB+키/환경/current/도구/활성웹 백업·PC사본을 갱신하고, API정지/연결0 뒤 정지dump/행snapshot·독립PC확인을 확보한다. 준비백업/기존PC token사본은 완료이며 같은복사/새키생성을 반복하지 않는다.
4. 고정후보/웹·APK 공동공개를 Native와 맞춘다. Native 고정파일/기존사용자인수는 재사용하고 새구현/재빌드/동일시험 대기는 없다. 실제전환 preflight/prepare/apply/open과필요시rollback/open-restored는운영실행 승인범위에서만 진행한다.

## 코드·계약·실행 구분

| 구분 | 기준 |
|---|---|
| Git | release/2.4.0, 기능기준18e6bb66283d1eb772c4eee2431eee92c1e25a62, 준비 변경 미커밋·미push |
| 로컬 실행 | image eadaa2cc…37b9/DB0038·기존개발지원 유지. 개발키 변경/삭제 없음 |
| 명세 | 191경로/211동작, SHA25612634daa64a8c4cbdfecfdb53bc7c1aca3bdb721c5ea555d098aea51544b9665; 이번 API 변경 없음 |
| 운영 | v2.3.0/source05daa42·DB0036·웹2.3.0+8, 서비스재시작/DB/웹전환 없음. 새token파일/제한사본만 추가 |
| Native | 빌드source84565024/원장f2f1b759, 웹34자산 로컬검증·비활성stage, APK 크기/hash/ZIP검증. APK서명/패키지검증은 동일원본 Native근거 |

완료된 Issue58 복구/사용자 두화면 인수·dev/main 통합 기록은 [DEV_LOG](DEV_LOG.md)와 [이슈 추적표](ISSUE_TRACKER.md)를 따른다. 반복 시험 대기를 만들지 않는다.

## 별도 유효 대기

Issue17 잔여/기기·15 소유권 이전·18 활동 자동추가·19 통계는 별도 후속이다. Issue58 상세 분석 후보가 Issue18 활동 자동추가의 완료/폐기를 뜻하지 않는다. Issue55/56은completed, Issue57은 사용자 직접삭제 완료다.

## 데이터·운영 경계

운영 lostparty 앱DB 전체 저장자료(회원·세션 포함) 초기화 범위는 사용자 확정이며 실제 삭제는 배포 전제/전환단계에서 수행한다. PostgreSQL역할/볼륨·키/환경·인증서·웹 원본은 보존한다. 운영에서는 키공급·승인 준비백업/backup.py설치까지만 실행했다. 현재추가작업은 로컬검증/도구구현이며 운영전환은미실행이다.

<a id="runtime-consolidation-followup"></a>

현재 create_app·DB0038로 개발한다. 과거 migration·동결 명세·배포 원장은 보존한다. [실행 기준](../engineering/development/runtime-configuration.md).

<a id="recovery-backup-closeout"></a>

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 사본/로컬dump 제외 방침을 유지한다. 새토큰의 서버/WSL/기존개인PC사본은 확인됐으며 외장매체·실제복원은 미실행이다.
