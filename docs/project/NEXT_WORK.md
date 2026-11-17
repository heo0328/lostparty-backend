# 다음 실행

2026-11-18 B11: 사용자의 진행지시로2.4.0 검증수용/reuse계획·고정근거·검증도구와기록을release/2.4.0에commit/push한다. 전체회귀/새CI를실행하지않고관련도구21PASS·실제근거해석/새시험목록0·문서/diff를확인했다. 실제merge/태그/공개/운영반영은제외다. 정확한게시source는이커밋과Issue인계로확정하며아래미게시는B10당시기록이다.

2026-11-18 B10: 사용자지시로전체재실행44120909602 cancelled확인·기존7회귀/verify성공+보완파일11PASS수용. 2.4.0한정reuse원장/source조상/후행변경허용목록연결을로컬구현해관련도구21시험PASS·실제근거해석PASS/새회귀0. 원failure/cancelled는보존하며전체CI성공으로표시하지않는다. 추가변경미커밋·미push/새CI·merge/공개/운영전환없음.

[B10회신](https://github.com/heo0328/lostparty-backend/issues/59#issuecomment-6953722160)·[고정수용근거](../engineering/operations/records/release-2.4.0-accepted-validation.json).

## 다음 실행

사용자게시/병합지시범위에서2.4.0수용근거·reuse계획/도구를포함한source를확정한다. 필요검사는정적/고정근거만이며전체회귀는재실행하지않는다. merge/태그/Release·불변이미지공개·운영반영은별도지시를따른다. 앱/시험fixture/마이그레이션/워크플로변경이있으면이예외를자동확대하지않는다. Native고정파일/기존인수재사용·동일시험요청없음.

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
