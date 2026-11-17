# DB0038 모집·현황 호환 복구

2026-11-17 / Issue58 / feat/roster-refresh-policy. 사용자가 선택한 직접 복구·회귀 보강안이다. API 계약·DDL·그룹 권한 정책은 변경하지 않는다.

## 원인과 직접 수정

실제 요청 e8752b04-742f-4476-8950-b821eea6c68c는 GET /v2/me/raid-room-memberships에서 GROUP_FEATURE_NOT_READY/503을 반환했다. POST /v2/raid-rooms/search에도 같은 오류가 확인됐다. DB0038에서 일반 group features는 true지만 cycle_group_policy.enabled의 명시 지원목록은0037까지만 허용했다. 추가 정적대조에서 admission_history의 재참가/완료 이력 판정2곳도0038이 누락돼 있었다.

모집 그룹정책1곳과 이력 판정2곳에만0038 지원을 추가했다. 지원목록을 공통 모듈로 옮기거나 미래 버전을 자동 허용하지 않는다. 소유/usable·현재 그룹회원/공개범위·종료증거/세대 검증·원ACK 보존은 기존 업무 코드 그대로다.

## 검증 구성

현재 migration head를 실제 조회해 fixture와 같은지 확인하는 회귀5개를 기본 current 검증에 포함했다. 기존 end-to-end 사례를 재사용하므로 검증 논리를 복제하지 않고 HTTP 모집검색·공개/비회원 권한·HTTP 회원참가목록·HTTP 재참가/원이력·완료/이탈 혼합 재진입을 실행한다.

수정 전 새 current-head 모집 사례가 GROUP_FEATURE_NOT_READY503으로 실패함을 격리PostgreSQL에서 재현했다. 수정 후 모집그룹정책·발견검색·재참가 전체관련회귀와 기본current를 검증한다. 수치는 완료 후 아래에 남긴다. 이전Issue58의131/86/17PASS를 이번 누락 경계의 통과 근거로 사용하지 않는다.

## 개발 반영·협업 경계

[Native 전체10 복원 요청](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6947073003)을 반영한다. 앞선 사용자 “작업완료후 개발서버 반영까지” 지시와 이번 계획 구현 승인 범위에서, 검증 후 개발 API만 교체한다. DB0038 migration을 재실행하거나 DB/키/환경·자료를 변경하지 않는다.

Native는 Backend의 실제 지원 회신 뒤 모집목록·레이드현황 두 화면만 확인한다. 코드의commit/push/dev·main병합/운영배포·Issue종료/삭제는 이번 작업에 포함하지 않는다. 기존 미커밋 진단 문서는 보존한다.

## 완료 근거

기본current136PASS/하위13PASS(새smoke5개포함), 모집정책·이력·검색회귀67PASS. 후보/실행API 전체191경로계약 일치, 명세hash12634daa64a8c4cbdfecfdb53bc7c1aca3bdb721c5ea555d098aea51544b9665 불변. source는88f1f45 위 미커밋·미push다.

[전체11 Backend B6](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6947547141)·[반영/인증HTTP집계](../operations/records/schema0038-recruitment-recovery.json). 실제개발group policy=True, API/DBhealthy, 현재/다음주 모집POST200/각0건·회원GET200/각2건. Native/사용자두화면확인대기다. 기존세션단기인증은메모리에서만사용했고 데이터/세션쓰기·provider호출없음. 앞선B5의진단만/코드미수정설명은당시기록이다.

## 게시·다음 담당

사용자 문서최신화/커밋·dev병합·push 지시로 복구 `08212c31215adae1c3a09cb9705409103af1ebdd`를 이력화했다. 기존 후보구현/계약8f29271 및 문서88f1f45 위 수정이다. 누적작업 전체를 dev에 통합하며 main/운영은 변경하지 않는다. [Native 전체12](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6947614833)에서 복구·dev지원수용, 사용자 두화면결과대기를 보고했다. 원격/병합의 정확한 SHA는 [DEV_LOG](../../project/DEV_LOG.md) 게시 영수증을 따른다. 위 미게시 설명은 실제rollout당시 상태다.

## dev 통합·사용자 정상확인 완료

복구08212c31215adae1c3a09cb9705409103af1ebdd·문서b6105ef를 dev 2e78854ef9644a02fd7a00b4c247c79f89e25f25로 통합/push/원격일치, 작업브랜치양쪽정리완료. [전체14 Backend B7](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6947695749). [Native 전체13](https://github.com/heo0328/lostparty-backend/issues/58#issuecomment-6947638411)의 사용자두화면 오류해소확인으로 화면대기를해소했다. 추가Backend수정/동일시험요청없음. 현재 실행/계약/DB는 B6 그대로이고 이게시로재배포하지않았다. 신규/삭제/소멸 실제사례후속과 Native게시/Issue마감은별도다.
