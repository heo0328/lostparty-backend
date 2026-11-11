# 다음 실행

2026-11-11 KST 기준. 실제 Backend 코드/Git과 각 담당의 현재 코드 확인 결과를 사용한다. Native 코드 상태·완료 판단은 Native가 작성하며 Backend가 대신 검토하지 않는다.

## 현재 우선 — 승인 6단계 실행 / 1단계 정리·첫 통합

- [Native 전체17](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6792945284)로 W3 협의공백 해소 확인. 전체18 exporter/manual workflow 구현, 전체19 새OAuth·준비소스push, 전체20 웹실물/새서명APK CI성공 인계. [Backend 전체21/W4 수령결과](https://github.com/heo0328/lostparty-backend/issues/49#issuecomment-6793947409)·[검증 원본](../engineering/operations/records/web-handoff-2.1.0.json).
- 웹run43005927315/artifact13849320316/source89951f4b71e7a225d442ccaf9510c83de86aaea7·2.1.0+6·운영origin. 정확ID 인증수령/외피API digest·실ZIP hash/14,333,833bytes·고정3파일/내외manifest·site34개/35entry/POSIX안전경로/개별hash PASS. 원3파일 보존·ignored backups/web-handoff/artifact-13849320316/inactive/site **로컬비활성 배치완료**, AWS전송/서버staging/활성화 미실행. 옛1ba ZIP은 계속 제외. 실artifact 재제출 불필요.
- 웹artifact 만료2026-11-25T10:46:33Z. 수령원본을 재압축/재빌드하지 않고 최종Native Release v2.1.0 asset에 동일bytes 승격. 일반재사용 수령/활성화 도구는 미구현, 실제HTTP MIME/캐시·브라우저/worker/기능인수 미완료.
- APKrun43003690946/sourcee9bfa96/artifact13847258618은 GitHub job의 빌드/서명검증/upload성공·Release skipped 직접확인. APK 자체검증/앱소스동일성은 Native 보고, Backend APK다운로드/실기기시험은 없음. 웹과APK source를조합기록에서구분한다.
- 새Android client 574337852234-2m3nnr5jaa46okro5vpbvsgddgrloob3.apps.googleusercontent.com을 운영실행/동결Compose와대조: 미포함. 적용준비는 기존azp2항목보존+새client1개추가, Web audience/서명/nonce유지. 운영환경/동결configuration revision과함께 실제적용은미실행. 운영웹origin등록은사용자확인Native보고, 실운영로그인과구분.
- [승인된 실행 설계](../engineering/operations/release-2.1.0.md)를 작성했다. 첫 통합은 현재 CORS/기록/설계만 포함, 도구구현은 release 브랜치에서 진행한다. 문서282/링크3202·diff PASS, CORS4·두 전체 계약은 실행 결과를 DEV_LOG에 연결한다.
- 다음 Backend: 사용자지시의 첫현재브랜치 기록·현재변경정리→dev통합→main동일시점→push→release/2.1.0 운영준비. 짧은중단허용/PC기존백업폴더재사용·기존자동화/제한SSH/DB인프라보호를유지하고 서버웹/Caddy·수령활성화도구·구APK조건부회귀/전체계약·최신백업/0036migration/복귀를준비한다. 지금은 수령확인만수행, Git통합/게시미실행.
- 최종공개는 Backend·웹·APK함께/Native안내문사용자확인완료. 새APK/웹+구0035지원제외, +신0036이번인수대상. 구APK+신Backend조건부거절/원ACK경계회귀는미완료. 새탭/재접속 첫공개·준비/교체탭종료/필요시강력새로고침·구탭미전송자동이전/무중단미지원. 자료초기화승인없음.
- AWS W2는v2.0.0/source51b1cb3/imagef33f4c6c/DB0035·187/208, dev0036·192/213(새5경로). CORS로컬반영/자동4·두계약검증/사용자로컬로그인·모집생성보고유지. 운영반영/새백업/자료쓰기·기기인수는별도다.

## 현재 — 문서·묶음 완료 dev 통합/게시 완료 / 다음 Issue17 정리

- #47 묶음 선택 완료와 #48 복구 안내/일정 읽기는 사용자 지시로 **completed 종료**했다. 추가 구현·계약 확인·동일 시험 대기는 없다. [완료 색인](ISSUE_TRACKER.md#completed)·[개발 이력](DEV_LOG.md).
- 다음 순차 정리 대상은 [#17](https://github.com/heo0328/lostparty-backend/issues/17)이다. 완료 오류/기존 계정 복구는 사용자 인수·양측 dev 통합 완료다. 누락/부분 완료 자료와 해당 기기 경계·원래 생명주기 요구는 별도 남아 있다. Native가 현재 코드 기준으로 최신화한 본문과 Backend 구현을 구분해 잔여 범위만 정리한다. 지금 자료 생성·DB 조정·반복 기기 시험을 시작하지 않는다.
- **#15·#18·#19의 다음 작업 선택은 전체 정리가 끝난 뒤로 보류한다.** 장기 계약/미구현 요구는 [이슈 추적표](ISSUE_TRACKER.md)에 보존한다. 자동 착수·미합의 계약 추가는 없다.

## 현재 코드·게시·실행 기준

| 구분 | 확인 기준 |
|---|---|
| checkout/통합 기준 | feat/webview-support / 분기 dev9d6f180, 로컬 CORS 미커밋·미push. 이전 업무 통합 병합b1400a489d4cc785244c3abfa1ed610cc6926de6 |
| 업무 구현/원격 | 업무44eb4ba·반영 기록624ef00·문서962c1cd9321328f19a8e1ea6b5071fa07380782b를 dev에 이력 보존 병합·push. 원격 병합 SHA 일치/전체 feature tip 포함·동일 tree 확인. app/tests/openapi422파일은 기존 검증 코드와 동일 |
| 로컬 dev | 웹 CORS 추가 이미지986f8d80로 API 재생성/healthy·실제 HTTP 및 두 전체 계약 확인. DB0036 유지. 이전 업무 runtime ae6b3e0a/앱288파일 비교는 당시 근거. [반영 원본](../engineering/operations/records/batch-completion-local-rollout.json) |
| 전체 계약 | 기본125경로/142동작, two-cycle192경로/213동작. 정확한 hash는 [구현/계약 근거](../features/recruitment/completion-and-records/batch-completion-implementation.md) |
| 후행 통합 기록 | 현재 브랜치/게시 상태·기능 브랜치 정리 결과는 dev의 후행 문서 커밋으로 보존. 업무 코드/시험/계약 변경 없음 |

사용자 지시로 #47의 Backend dev 병합·push를 완료하고 feat/raid-batch-completion을 로컬/원격에서 정리했다. main·로컬 서버·운영은 이번 통합에서 변경하지 않았다. 이후 새 게시/병합/배포는 별도 지시 범위다. 실제 개발 DB의 행 수는 사용자 테스트로 변할 수 있으므로 반영 시점의 건수를 현재 고정값처럼 사용하지 않는다.

## 담당별 후속을 구분

Native #47 게시47a30dad, #48 후속 lib/test/문서의 미커밋·미push·dev 미통합은 Native 담당 보고다. 두 이슈의 승인 범위 연결/추가 구현 없음도 Native 확인에 따른다. Penpot 디자인은 Native 차후 후속이며 종료된 이슈의 대기 조건이 아니다. 미보고 기기 경계·후속 갱신/레드닷·웹소켓을 이미 완료로 확대하지 않는다.

<a id="runtime-consolidation-followup"></a>

## 별도 선택 후속 — 실행 구성 단일화

[조사](../engineering/development/runtime-consolidation-review.md)와 [개선 대장](backend-improvement-plan.md#runtime-consolidation)은 보존한다. 기본0023 앱과 현재 two-cycle 실행을 혼용하지 않는다. 구현 착수/기존 코드 삭제·운영 반영은 별도 선택이다.

<a id="recovery-backup-closeout"></a>

## 환경·백업 보존

[백업 원장](../engineering/operations/backup-and-recovery.md)의 기존 키/환경 사본·운영 기준본을 재사용한다. 로컬 DB dump 제외 방침과 실제 복원/정기 자동화·외장 매체 미확인 상태는 그대로다. 새 백업/키 생성·자료 삭제 요청은 없다.

이전 실행/협의 경과는 [최신화 직전 기록](../archive/project/status-before-refresh-20261110/NEXT_WORK.md), 완료/결정·검증은 [DEV_LOG](DEV_LOG.md)를 따른다. 현재 상태를 과거 문단 위에 반복 누적하지 않는다.
