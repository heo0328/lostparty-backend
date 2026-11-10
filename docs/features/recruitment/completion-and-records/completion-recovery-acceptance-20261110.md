# Issue17 완료 오류·계정 복구 구간 인수 결과

2026-11-10 / Backend 문서 최신화. 공식 Issue17 전체 댓글53개를 조회해 [전체52번째 Native 사용자 인수·시점 정정](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756433040)과 [전체53번째 Native 커밋/푸시 결과](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6756529672)를 확인했다. 이번 완료 오류/계정 복구 구간의 최신 완료 기준이다. Issue17 전체 기능 종료·누락 캐릭터 검증 완료로 확대하지 않는다.

## 완료 범위와 근거

| 구간 | 결과·근거 |
|---|---|
| Backend 완료 profile 계약 | 고정16c9cd4/feat/character-lifecycle 게시, 실제 지원65동작/누락10개 선언 보정. two-cycle SHA256864de38b53ec23a305074bb3844a7a603ba1f992815427fdba3e6931793119b6. [보정/반영 기록](completion-profile-contract-fix.md) |
| Backend 실제 로컬 반영 | API image101cd82d/DB0036, 후보·게시 소스/전체 계약 일치와 당시 자료/키·환경 보존 확인. 이번 문서 작업에서 재배포/DB 재시험하지 않음 |
| 계정 BUG-033 옵션 | 신규 정정 GET/POST·수동 PUT은 group_policy_version만 연결. 기존 recruitment-v2 namespace/원옵션·본문·ACK 보존. [최소 옵션 조사](account-completion-group-profile-bug033.md) |
| 기존 v3 막힘 복구 | 원무옵션 재전송의 현재409/CLIENT_UPGRADE_REQUIRED→정확한 대상 GET→명시적 현재 상태 채택의 좁힌 경로 연결. 과거 결과 확정·ACK 합성·서버 완료 삭제 없음. [계약/검증](bug033-current-state-adoption.md) |
| Native 완료 안내/복구 | 확인창 한정 안내·첫 오류 취소·원요청/ACK 보존·늦은 ACK 처리·ACK 후 GET만 복구, 계정 원query/불명 이력 보관 연결. Native51/53 보고 |
| 사용자 디바이스 인수 | Native52가 사용자 통과를 공식 기록. 기존 계정 복구는 **버튼/안내 문구 변경 요청 전에 이미 정상 완료**했다는 사용자 시점 확인 포함. 이전 복구 미확인/추가 시험 대기는 해소 |
| Native 소스 게시 | [5df515f7841a7963faa7d3c6ed930cd31ab8b3bf](https://github.com/heo0328/LostParty_flutter/commit/5df515f7841a7963faa7d3c6ed930cd31ab8b3bf) / feature/raid-character-missing-recovery. 누적30파일 단일 커밋·push, HEAD/origin/원격 동일·clean은 Native53 보고. Backend가 Native 로컬 소스를 읽거나 시험한 것이 아님 |

최종 버튼은 **‘현재 정보로 화면갱신’**, 기존 canUseCurrent 조건의 두 번째 안내는 **‘현재 정보로 화면을 갱신하면 다시 사용할 수 있습니다.’**다. 기존 useCurrent 동작을 그대로 사용하며 문구 변경이 복구 기능을 새로 만든 것이 아니다. 이미 완료한 계정 복구를 다시 만들거나 같은 기기 시험을 반복 요청하지 않는다.

## 검증을 구분한 기록

| 근거 | 확인한 범위·결과 |
|---|---|
| Backend 보정 영향 회귀 | 최종 고유114PASS, 도구63PASS. [원본](completion-profile-contract-fix.md). 과거 전체1921PASS/기존2FAIL과 합산하지 않음 |
| Backend 추가 조사 | [두 key/완료 종류 도착 순서](completion-retry-order-check.md)6PASS/96.21s, [계정 group 옵션](account-completion-group-profile-bug033.md)2PASS/48.98s, [기존 worker fencing/현재 상태 보존](bug033-current-state-adoption.md)1PASS/22.79s. 각각의 한정된 합성/HTTP 근거이며 실제 기기 통과로 대체하지 않음 |
| Native 자동 검증 | 최종 전체2856PASS/analyze0, 포맷/diff 통과. 직접50/88PASS·중간 실행과 Backend 수를 합산하지 않음. 게시 시 Dart21파일 포맷0변경/diff만 확인하고 같은 전체 시험 반복하지 않았다는 Native53 보고 |
| 사용자 기기 | 2026-11-10 이번 완료 오류/계정 복구 구간 통과. 실제 계정 복구 미확인 대기를 해소하지만 원서버 과거 개별 요청의 성공/실패 이력을 확정하는 것은 아님 |
| 이번 문서 작업 | 현재 기록/링크·동결 자료·문서 검사/diff만 확인. 서버/DB·앱/기기 재실행과 추가 업무 회귀 없음 |

## 남은 범위와 다음 담당

- 누락 캐릭터/부분 완료 개발용 자료 준비와 해당 기기 검증은 별도 후속이다. 이번 복구 인수로 완료 처리하지 않는다. 자료 준비·실자료 변경의 대상/방법은 사용자 지시 범위에서 정한다.
- 묶음 레이드 체크박스 선택/일괄 완료는 사용자 요청을 Native 후속 문서에 기록한 **미구현 기획**이다. 이번 구현/계약·인수에 포함하지 않으며 Backend API 설계/구현 착수로 해석하지 않는다.
- 이번 구간에 추가 Backend 수정/배포 요청이나 동일 복구 재수용 대기는 없다. 다음은 사용자 선택 후 위 후속 범위를 구체화하거나 새 차이에 대응한다.
- dev/main 병합·운영/APK 배포·Issue 종료는 하지 않았다. 이후 사용자 지시로 Backend feat/character-lifecycle을 dev에 병합(aa7058c)·원격 반영한 뒤 로컬/원격 작업 브랜치를 정리했다. Native 브랜치 보존/통합은 Native 지시 범위이며 Backend가 변경하지 않는다. main과 서버/배포는 변경하지 않았다.

## 기록 상태

Backend 업무 구현16c9cd4·후행 기록f744a1e 이후 조사/회신·인수 문서13개를 `afd5ba21d443d85f73b98d29043eefe3583b8cd7`에 커밋·push했다. 사용자 지시로 현재 브랜치 전체를 dev에 병합 `aa7058c5f93ad799033116608f2b3f52931b0dfe`·원격 반영했고 feat/character-lifecycle은 로컬/원격 삭제, checkout은dev다. 후행 문서 커밋은 이 통합 결과를 기록한다. 별도 배포·로컬API 교체·DB/키·환경 변경은 없다.

기존 [보정 당시 검증 JSON](../../../engineering/operations/records/completion-profile-contract-verification.json)의 Native 대기/기기 미확인 값은 당시 기록으로 보존하고 현재 인수·Git 상태는 이 문서와 [NEXT_WORK](../../../project/NEXT_WORK.md)를 따른다. 과거 조사·실패/대기 원본과 공유 이력을 재작성하지 않았다. Issue17 전체 종료/새 기능 착수로 확대하지 않는다.

공식 Issue 본문 상단도 Native52의 기기 인수·시점 정정과 Native53 게시 결과/별도 후속으로 최신화했다. 새 댓글·Issue 종료는 실행하지 않았다.
