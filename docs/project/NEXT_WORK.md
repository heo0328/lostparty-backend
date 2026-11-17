# 다음 실행

2026-11-18 CI후속: 원full CI44117486823/source5e0ee12는7개회귀성공·6번1FAIL(216PASS/2subtests),verify성공·validation실패/publish·deploy skipped다. 수요일점검과충돌한명시출발시험의시계를조회/명령/reconcile모두일치하도록고정해표적1PASS·파일전체11PASS(46.30s). 앱/API변경없음. 동일승인게시/CI구간에직접필요한시험보완/기록만최소게시후새source수동full CI를실행한다. merge/공개/운영은제외다.

## 다음 실행

1. 최소보완커밋/원격일치후새source수동full CI의최종결과를확인한다. 원run/실패를보존하고새run/source를별도로기록한다. 원source의단순재시도는보완코드를사용하지않으므로하지않는다.
2. 전체성공뒤merge/태그·Release/불변이미지공개는별도사용자지시범위다. 운영전환은별도승인과직전정지백업/PC확인·공동공개조건을따른다.

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
