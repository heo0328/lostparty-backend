# 다음 실행

2026-11-18 B8: 사용자명시승인으로 release/2.4.0 누적변경을 5e0ee12e897e35f01dcf73f40eee351a15649d52에commit/push하고원격일치를확인했다. 동일source 수동full CI [44117486823](https://github.com/heo0328/lostparty-backend/actions/runs/44117486823) 실행중. 결과와실패원인을확인한다. [게시/CI영수증](../engineering/operations/records/release-2.4.0-ci.json). merge/태그·Release·이미지공개/운영배포는승인범위가아니며미실행이다.

## 다음 실행과 게시 경계

1. 현재수동full CI verify/8회귀구간/validation의최종결과를확인하고필요한실패보완만한다. 실패시원run/소스를보존하고보완source와재실행결과를구분한다.
2. 승인된이번구간은소스commit/push와수동검증이다. merge·태그/Release·불변GHCR공개는별도지시를기다린다. 수동검증의이미지빌드는runner로컬시험이며고정공개digest가아니다.
3. 실제운영전환은새고정후보와전환직전최신백업/정지dump·독립PC확인/운영반영·공동공개승인범위에서수행한다. 운영2.3.0/0036유지, Native고정파일/기존인수재사용·같은시험요청없음.

## 코드·계약·실행 구분

| 구분 | 기준 |
|---|---|
| Git | release/2.4.0, 기능기준18e6bb66283d1eb772c4eee2431eee92c1e25a62, 게시source 5e0ee12e897e35f01dcf73f40eee351a15649d52 원격일치, 후행결과문서는로컬기록 |
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
