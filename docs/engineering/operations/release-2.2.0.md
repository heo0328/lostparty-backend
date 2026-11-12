# 2.2.0 공동 운영 배포

2026-11-13 / `release/2.2.0` / [Issue51](https://github.com/heo0328/lostparty-backend/issues/51). 사용자가 Backend dev push/main 동일화와 필터 개선 운영 배포를 지시했다. [전체1 Native의 사용자 확정](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6829149247)에 따라 제한 접근/임시 운영 계정·사용자 재인수 및 기존 dev 기능 시험은 반복하지 않는다. 실제 릴리즈·서비스·정적 파일 검증은 수행한다.

## 포함 범위와 호환

- dev/main은 `9775c1e555b767b71610b5dad35ef84b272f2a32`에 atomic push·원격 동일 확인했다. 완료 `refactor/backend-runtime`은 dev 병합/원격 게시 확인 후 로컬 정리했다.
- #50 탐색의 기존 POST 선택 `discovery-1`·전체 count·50개 페이지와 기본 현재 앱/명세 이름 정리를 함께 포함한다. 현재 계약 원문 `3fdc0661…7052`, legacy 원문 `18491bc0…c3dd`는 유지한다.
- 기존2.1.0 앱은 response_profile 생략 시 기존 응답을 유지한다. 새2.2.0 앱/웹은 Backend discovery 지원 뒤 활성화한다. endpoint 추가·DB migration·환경/OAuth·키 교체는 없다.

## 재사용과 새 검증

이번2.2.0 한정 `reuse`는 [로컬 실행 검증 원본](records/runtime-consolidation-local-rollout.json)의 고정 원문 hash와 검증 코드8a54c485→승인9775c1e 사이 비문서 변경 없음, 승인 소스 이후 앱/DB/의존성/Compose/기능 시험 불변을 강제한다. 고유2001PASS·최종 캐시 보완58PASS·도구84PASS는 기존 실행이며 새 CI 전체 green으로 표시하지 않는다. 새 validation.json은 신규 app executed_tests=[]·regression/contracts reused로 출처 원문을 보존한다. 다음 버전의 상시 생략 승인이 아니다.

이번 추가 코드는 VERSION/계획·증거 제어와 기존 웹 도구/백업 파일명 처리뿐이다. 웹 수령은 고정 receipt 버전으로 파일명을 정하고 ZIP/manifest/source/run/hash·경로/중복/링크 검사를 그대로 적용한다.2.1.0→2.2.0 실제 원본 이름 유지·배치/활성/복귀와 위조/불일치를 시험한다. 릴리즈 준비 허용 경로는 이 도구와 관련 시험으로 제한하며 앱 코드 변경 시 재사용을 거절한다.

## 선행 작업과 실행 순서

1. 실제 운영2.1.1/source d16734d·DB0036·웹2.1.0+6·정상 서비스와 설치 도구 hash·미완료 배포0을 확인한다. 새 Compose는 image와 동등한 factory 이름 외 운영 설정이 같아야 한다.
2. 기존 운영 자료/환경/키/동결 구성·설치 제어기·현재 웹 원본을 새 비공개 백업으로 확보하고 기존 사용자 PC 보관 폴더에 사본/hash를 확인한다. 키는 재발급하지 않는다. [백업 기준](backup-and-recovery.md).
3. 배포 잠금과 미완료 작업 검사를 유지하며 설치 common.py/server.py를 함께 갱신한다. 기존/신형 release.json 검증과 현재 baseline preflight를 확인한다. 제한 SSH/sudo/인증·DB/API/Caddy는 바꾸지 않는다.
4. Backend2.2.0 불변 태그/이미지·schema2 메타데이터를 준비하고 표준 API-only 배포를 사용한다. 기존0035→0036 전환용 release-deployment.json은 현재 소스에서 제거해 `standard`로 복귀하며 과거 태그/기록은 보존한다. 배포 후 실제 HTTPS·두 전체 명세·현재DB/구 응답/신 discovery와 자료/키/DB/Caddy 보존을 검사한다.
5. [고정 웹 인계](records/web-handoff-2.2.0.json)의 원3파일을 수령/검증해 비활성 배치한다. Backend 성공 뒤 같은 산출물로 웹 포인터를 원자적으로 전환하고 실제 HTTPS index/JS/WASM/manifest/hash·API·404/캐시를 확인한다. IP 제한/점검503을 새로 만들지 않는다.
6. [Backend 전체4 준비 회신](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6831158426) 이후 실제 source/image/DB/health/웹 hash를 같은 Issue에 회신한다. 다음 Native는 같은 source의 Android 공개 Release/파일 재검증이다. Issue 종료는 별도 지시다.

## 복귀와 자료 경계

API 실패 시 표준 제어기가 직전 DB0036 호환 image7aa19edf와 동결 명령으로 복귀한다. legacy DB0023 앱이나 DB downgrade를 사용하지 않는다. 웹 실패 시 이전 pointer의2.1.0 고정 원본으로 복귀한다. 새 서버는 기존 앱/웹도 지원하므로 웹 복귀 때문에 DB/키/환경을 되돌리지 않는다. 새 계약을 소비하는 앱이 공개되기 전 Backend/API·웹 성공을 먼저 회신한다.

기존 서비스·백업/태그는 삭제하지 않는다. 서비스 교체로 사용자 자료가 초기화되지 않아야 하며 기존 PC 사본과 실제 복원 시험은 별개다. 실제 수행 결과는 DEV_LOG와 [NEXT_WORK](../../project/NEXT_WORK.md)에 기록한다.

## 실제 운영 완료

Backend v2.2.0/source c31d90da·image cc753718…406dae·DB0036을 표준 Actions43274053529로 반영했다. common/server 설치 갱신·schema1/2 preflight와 직전/반영후 백업·기존 PC 사본 hash를 확인했다. 기존118표의 COPY 행 전부가 직전 dump와 일치하며 DB/Caddy 컨테이너·환경/키/mount를 유지했다. 웹은 Native source994db44a/ZIP517166ca의 원본 그대로 공개했고 실제HTTPS34자산 hash·기존/신규 검색응답·health/인증 경계를 확인했다.

[전체5 Backend 운영 완료](https://github.com/heo0328/lostparty-backend/issues/51#issuecomment-6831720284)를 게시하고 실제 전체 순번/작성 측/다음 Native Android 공개를 재조회했다. [공개 실행 집계](records/release-2.2.0-deployment.json). 새 사용자 재인수·자료 쓰기 시험·DB migration/키 교체는 없다. 다음 Native Android Release/실제 게시 검증과 Issue 종료는 구분한다. 고정 태그/이미지는 후행 기록 커밋으로 다시 배포하지 않는다.
