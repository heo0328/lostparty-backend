# 다음 실행

문서 운영 #29는 공통 원본·양측 참조 반영 및 [상호 대조](https://github.com/heo0328/lostparty-backend/issues/29#issuecomment-6520322169) 완료로 추가 수정 대기를 해소했다. Issue 종료는 별도이며 상세 근거는 [DEV_LOG](DEV_LOG.md)에 보존한다. 기존 그룹 기기 인수와 기술 진단 후속은 별도다.

## 다음 실행 — 상세조회500 추가 근거 대조 (현재 미재현)

[Issue16 전체36번째 Flutter 조사 요청](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6529904340)의 두request_id는 실제 상세500으로 확인했다. 현재 READ ONLY의 C/N·모든프로필/그룹표시와 과거anchor조회는 예외가 재현되지 않았다. 당시 로그는 예외종류/stack·query/대상세대를 보존하지 않아 원인은 미확정이며 해결 완료가 아니다. [조사 집계](../features/groups/detail-500-investigation.json)·[결과 이력](DEV_LOG.md#group-detail-500-investigation)을 따른다.

[전체39번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530221606)에서 당시 입력/동작 원기록은 없다고 회신했다. 같은 과거기록 요청은 반복하지 않는다. 후속 ASGI HTTP 확인(조율대기 on/off·모든프로필/그룹표시)도 재현0이며 추가17:48:47의500은 입력/예외근거가 없어 원인미확정이다. 자연재발 시 UTC/request_id와 민감값 없는 입력근거를 받아 Backend가 표적 재현/원인 대조를 이어간다. 정상통과 기기시험을 반복하지 않는다. 서버교체·실자료수정/초기화는 요청범위에서 제외하며 코드/API 변경 필요성은 근거 확인 후 판단한다.

[전체37번째 Flutter 앱기기 전체통과](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6529987970)를 수용해 현재 그룹·레이드 변경의 연결/기기 대기는 해소했다. 연결88a69fa7·후행개방/UTC수정3ec0f54f·최신안내055e0608의 자체보고 기준이며 상세500·Penpot/다른보류기능·운영릴리즈 인수와 구분한다. 추가 정상시험을 요청하지 않는다.

[전체40번째 Flutter 통합](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530680059)의 dev/main b8b20b50·전체2,730PASS/분석0은 자체보고로 수용하며 Backend 조사/시험과 합산하지 않는다.

현재 실행sourceb8542ef/이미지930c25f8·DB0035·API healthy와 [기존 반영 기록](../engineering/operations/cycle-group-policy-rollout.md)은 유지한다. 상세500 후속 조사 checkout은 최신 dev1f0b588에서 분기한 fix/raid-detail-errors다. 사용자 승인으로 [PR31](https://github.com/heo0328/lostparty-backend/pull/31)·병합9fa0f7e에 그룹/F01/개선 인계·상세500 조사기록을 통합하고 main도 dev와 같은 최종 기록 커밋으로 동기화한다. 통합된 feat/raid-group-policy·fix/backend-beta-readiness는 로컬/원격 정리했고 미완료 feat/activity-selection은 보존한다. 후속 구현은 최신 dev의 목적 브랜치에서 이어가며 서버교체·AWS/release·자료초기화·Issue종료는 하지 않았다.

## 보류 추적 — Backend 베타 개선

[F01](DEV_LOG.md#f01-registration-cleanup)은 `c94ce88`로 구현·격리 검증·commit/push 완료, PR31로 dev/main 통합하며 코드는 기존0035 이미지에 함께 반영됐다. 미처리 대상0·수동 정리 실행 없음은 [반영 기록](../engineering/operations/cycle-group-policy-rollout.md)을 따른다. [개선 계획의 F02 재개 조건](backend-improvement-plan.md#f02-resume)을 따른다. F02는 로컬 설정 조사 후 공개 경로 미정으로 보류하며 AWS 공개 준비 때 재개한다. 사용자는 Lightsail 생성 전·테스터 총20~50명 예상·도메인 미보유다. 지금 인프라를 확정하지 않는다. F03 내부 장애 추적은 개선 복귀 시 다음 후보이며 미착수다. 그룹 작업을 막지 않는다.

## 이전0034 기준과 기존 변경의 기기 대기 (이력)

2026-10-30 기준, 그룹 브랜치는 dev/main 통합 후 로컬·원격 정리했으며 현재 checkout은 `feat/raid-group-policy`다. 기존 그룹 핵심 흐름·관리, 초대 후보 대소문자 검색·역할별 표시, 모집 최초 그룹 연결·목록 그룹명 표시까지 Backend 구현·검증·개발반영을 완료했다. main/dev는 그룹 병합 `fc6c06a`와 후행 통합 기록을 포함한다.

| 구분 | 확인된 기준 |
|---|---|
| 업무 구현·계약 | `6dac5ab2cc67e197979e7188a9c97ce2c27fb548` |
| 실제 개발서버 | source `2602e4595a868eebdf12b04e1fd51502142069b3` / 이미지 `5bd8dde6` / DB `0034_group_features` |
| 기존 게시 기록 | 반영 기록 `ad095c3`, 이슈 인계 링크 기록 `603fe2d`까지 commit/push 완료 |
| 문서 인계 | `48bf88c` 게시 및 PR30 dev/main 통합 완료. 문서/Git 통합과 실제 실행 소스는 구분한다. |

위 표는 이전0034 반영 당시 기준이다. 현재0035 실행은 위 다음 실행/반영 기록을 따른다. 실행 소스와 후행 문서 커밋을 구분한다. 이전 게시 이력은 유지하며 되돌리거나 재작성하지 않는다.

## 이전 계약 소비·기기 확인 대기 (새 #16 정책 요청과 구분)

[#12 전체40번째 Flutter · 목록/소속 표시 소비 인계](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6503895589)·[#16 전체26번째 Flutter · 최초 연결 소비 인계](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6503895060)를 확인했다. Flutter는 `feature/group-backend-integration`의 `5f024e536fbf4963a77903f7763b7ca460939a34` commit/push·local/origin 일치, 최초 연결 context/기존 PUT·목록 metadata·프로필별 배지 연결 완료를 보고했다. 이는 공식 Issue의 자체 보고이며 Flutter 로컬 소스는 읽지 않았다.

- Flutter 검증 보고: 전체 test 2,707PASS이며 직접 경계43PASS는 포함 수다. analyze 오류/경고0·기존 info3, 포맷/diff/review 완료다. Backend 시험과 합산하지 않는다.
- 기존 인계 대비 변경: Flutter 신규 계약 소비는 구현 완료 보고로 갱신한다. **당시 추가 API 변경이나 Backend 재검증 반복 요청은 없었다.** 이후 #16 전체27/28의 새 정책 정정은 위 다음 실행으로 별도 추적한다. 기존 그룹 정상 기기 인수는 유지한다.
- 다음 담당은 사용자 변경 경계 기기 확인과 Flutter 결과 대응이다. 일반 방 최초 그룹 연결, 같은 그룹 공개범위 왕복, 서버 그룹명/긴 이름, 비그룹원 시점 배지, 생성 선택 기본값을 확인한다. 실제 최초 연결 허용 context/명령 성공은 여전히 미확인이다.
- 비그룹원 배지 원 제보는 Backend/Flutter 합성 검사에서 미재현이다. 결함 해결 완료로 판정하지 않고 실제 기기 차이가 생기면 해당 응답/렌더링 위치를 좁혀 대응한다.
- Backend는 구체 차이가 회신되면 해당 경계만 수정·검증한다. 이전 계약의 동일 시험을 반복하지 않으며 새 #16 정책 설계는 별도 진행한다. 기존 회신 결과는 이번 진단 인계 구간에 함께 보존한다.
- Flutter의 Penpot03 갱신/시각 검수는 도구 미제공으로 대기한다는 보고이며 Backend API 추가 작업으로 확대하지 않는다. 새 기기 인수·운영배포·Issue 종료는 미완료/별도다. Backend Git 병합은 PR30으로 완료했다.

완료 조건은 연결된 새 앱의 변경 경계 기기 결과 확인이다. 이번 문서 인계에서는 Issue 변경/추가 댓글·서버/DB 작업은 하지 않는다.

## 유지할 검증·인수 근거

- [격리 검증 집계](../features/groups/raid-link-verification-2026-10-30.json): 신규/기존 회귀47PASS, 추가 경계4PASS, 토큰1PASS. 반복 합산 없이 선택49시나리오이며 전체 프로젝트 또는 동일 HEAD 일괄시험 결과는 아니다. 두 OpenAPI 전체 일치, 기본 객체·기존 schema 값 불변을 확인했다.
- [개발 반영 집계](../engineering/operations/records/raid-group-link-rollout.json): 교체 전후114업무표2,015행·sequence·설정·키·DB볼륨 보존, migration 없음. 소스274파일/runtime31·두전체계약·HTTP12·읽기전용 목록/프로필·worker·API/DB healthy를 확인했다. 이는 반영 당시 검증 결과이며 이번 문서 작업에서 서버 검증을 반복하지 않았다.
- 실제 context 샘플은 현재 G1/방 상태로 거절됐다. 긍정 경계는 격리 검증을 따르며 실서버 최초 연결 성공으로 표시하지 않는다. 실회원 변경 명령을 임의 실행하지 않았다.
- [#12 전체36번째 Flutter · 기존 그룹 사용자 기기 인수](https://github.com/heo0328/lostparty-backend/issues/12#issuecomment-6502226347)·[#16 전체21번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6502226876)의 안내 범위 통과는 유지한다. 초대 검색/역할별 표시·기존 관리·필터/기존 참가 보존도 해당 보고 범위이며 새 최초 연결/표시 변경 인수로 확대하지 않는다.
- [#16 전체22번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6502336731)의 `9d1baa39` 생성 UI 기본값/기존 생성 API 1회·29PASS는 Flutter 자체 보고다. Backend 시험에 합산하지 않는다.
- 그룹원 동등 개설·실제T 공대장 관리를 유지하며 그룹장 전용 레이드 명령은 없다. 복구승계·활동 자동추가는 별도 미결정이고 로컬 활동 선택 브랜치 `89a3248`은 보존한다.

## 다른 미완료 주제

모집1차인수/Issue13종료는유지하고차후정밀도/알럿/UX/소켓은 [보완대장](../features/recruitment/follow-up-backlog.md)을따른다. 다른Issue상태는 [추적표](ISSUE_TRACKER.md), 완료/결정/검증·장애는 [DEV_LOG](DEV_LOG.md)에보존한다. IF-001/002/003 비활성·원자료/pending/ACK·별도성능/실회원원ACK 검증경계는유지한다.

상세조회500 조사 공식 회신: [#16 전체38번째 Backend · 현재미재현/추가근거 대조](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530073442). 조사기록1be55a7 commit/push·원격일치 완료, 다음 Flutter 당시기록 확인/Backend 후속대조이며 원인해소·Issue종료가 아니다.
