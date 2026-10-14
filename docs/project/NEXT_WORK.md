# 현재 작업과 다음 실행 계획

기준일: 2026-10-14. 현재 그룹은 **Issue #3 조회 인계 완료 후 등록 관리 구간 준비·대상 보완**입니다.

## 근거·범위

[Issue #3](https://github.com/heo0328/lostparty-backend/issues/3), [Flutter 수용](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6159847616), [설계](../ISSUE_3_IMPLEMENTATION_PLAN.md), [실행/인계 안내](../ISSUE_3_DEVELOPMENT.md), [원본 OpenAPI](../../openapi/openapi.yaml)가 기준입니다. [협업 작업 단계](../API_COLLABORATION_WORKFLOW.md)에 따라 구현 가능한 영역을 먼저 완료하고 실검증 입력을 분리했습니다.

[등록 관리 후속 계획](../ISSUE_3_REGISTRATION_FOLLOWUP_PLAN.md)이 이번 구간 실행 기준입니다.

브랜치 `feat/3-account-restoration`, 기준 dev `e6c72e4`. 구현·계약 커밋 `254cb5de125ab1bcb2aa084e091eae976e9a078a`을 원격 작업 브랜치에 게시했습니다. dev/main은 변경하지 않았으며 병합은 별도 후속입니다.

## 현재 상태

| 단계 | 상태 |
|---|---|
| 요구/계약 방향 합의 | A/B·버전·멱등·등록·대표·보존/제한 수용 회신 확보 |
| Backend 로컬 구현 | 12개 업무API, auth 재검사, 등록/전체설정/pagination, challenge/identity/소유권/audit, atomic 활동/대표, TTL/quota/summary합류 구현 |
| DB/원본 계약 | additive0002의11개테이블, 기존7경로/인증schema 보존·신규12operation 반영 |
| Backend 자동 검증 | 이전전체114개통과. 이번lease헤더보완 대상10개통과/106개제외,기존경고1개. 두새HTTP사례·rollback/worker상태보존 검증 |
| 로컬 API 적용 | 개발DB additive migration·API 갱신, 기존 인증6테이블 건수 보존, health200/미인증업무401·전체OpenAPI 일치 확인 |
| 원격 게시/계약 SHA 인계 | 작업 브랜치 push 완료. 구현/계약 `254cb5de125ab1bcb2aa084e091eae976e9a078a`이 기준. Issue에 정확한 SHA로 인계 |
| Flutter 업무 API 적용 | [최신 인계](https://github.com/heo0328/lostparty-backend/issues/3#issuecomment-6161970774): 계약254cb5d, 두GET 연결·dev3cedd9d·1159자동검증/빈등록·로그아웃·로컬보존 보고. 쓰기 미연결 |
| 실provider/장비 | 키/schema/해제표현·quota/지연 미확인. live확정은pending 증거보류, 감소roster 자동missing/이전 보류 |
| 운영 배포 | 미실행 |

mock proof는 pytest dependency에서만 주입하며 공개 API/임의env 우회가 없습니다. 소유권 transaction은 구현·자동 검증했고 실제 미실증 입력의 성공 판정만 보류합니다. 현재 game 쓰기는 짧은 전역advisory lock으로 직렬화하며 네트워크는 밖에서 수행합니다. 처리량 개선은 실사용 근거에 따라 후속 검토합니다.

## 다음 실행

1. lease generation/만료 REQUEST_IN_PROGRESS의 Retry-After2 보완·대상10개회귀·로컬적용은 완료했다. 기존계약254cb5d는유지하며 보완구현 `db0f3ae438021b4f5fa3738b76fd926687871b0d`을 작업브랜치에게시했다. main/dev통합은별도후속이다.
2. Flutter는 기존 preview/등록/PATCH/DELETE/refresh를 연결하며 동일key/payload·GET복구·503제한·로컬보존을 구현한다. 장비인증 인수를 선행조건으로 두지 않는다.
3. 사용자·Backend가 로컬 .env의 LOSTARK_API_TOKEN을 안전하게 준비하고 API만 재생성한다. key값/개인정보는 출력·Issue게시하지 않는다.
4. key 준비 후 Backend가 실제 siblings를 parser와 대조한다. 기대schema와 같으면 추가코드변경 없이 preview→등록→두GET→수정/본계정전환→refresh→명시제거의 공동인수를 진행한다. 실차이가 있을 때 해당adapter/오류만 대상검증·수정한다.
5. 신규수정은 구현SHA/계약변경 여부·대상검증을 인계한다. commit/push·dev/main통합은 승인범위를 따르고 아직미통합작업브랜치는보존한다.

이번보완은로컬API에적용됐다(보완구현 db0f3ae438021b4f5fa3738b76fd926687871b0d). DB0002·health200·원본계약254cb5d/런타임OpenAPI일치·기존인증6테이블건수보존·server key비어있음확인. 테스트는격리DB대상10개통과/106개미실행,114전체반복없음. 개발DB자료삽입/초기화·migration재적용없음. 장비/소유권/활동쓰기 Flutter연결은 이후별도그룹이다.

## 후속 입력과 완료 기준

기존 구현/계약 commit/push는 완료했다. 새 입력은 안전한 server key 준비와 실제siblings 근거·등록 관리 Flutter 테스트 결과이며 조회 인계/소비SHA는 확보했다. 신규수정 게시·dev/main통합은 기존 승인범위를 확인한다. 같은 미확인 자료를 반복요청하며 Backend 구현을 미루지 않습니다. 실제인수/Flutter적용/운영완료는 자동테스트 통과와 별도입니다. Issue는 임의 종료하지 않습니다.

#2 인증 원본 SHA `519c609495966a3d785c6671c09bf513b28875a6`은 기존인증 기준입니다. #3의 새로운 업무 계약 SHA로 사용하지 않습니다. #2의 전체세션/실기기/release 인수는 기존잔여작업으로 보존하며 Flutter 최신 회신의 로그인/재실행/로그아웃 성공보고는 독립 실검증의 참고 근거입니다.

## 이슈 종료 상태와 인증 후속

사용자승인으로 [#1 협업연결테스트](https://github.com/heo0328/lostparty-backend/issues/1#issuecomment-6162336853)와 [#2 합의된Backend인증1차범위](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6162337920)를Completed로닫았다. #3은등록관리/실provider·Flutter인수작업이남아OPEN이다. 이슈/댓글을삭제하지않았다.

#2 종료후에도실기기/release·운영HTTPS/배포·탈퇴/약관,모든로그인유지선택별실기기재시작·실제refresh유실복구/늦은응답격리의전체인수는별도잔여다. 기본로그인/재실행/로그아웃성공보고와자동검증을전체실기기인수로확대하지않는다. 실제인증결함이나오면이슈재개또는후속이슈로관리한다. 이번종료검토는기존근거를사용했고테스트/서버/DB를재실행하지않았다.
