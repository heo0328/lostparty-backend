# 실행 정리 이후 배포 도구 전환

2026-11-13 / 준비 설계. 이번 작업은 로컬 반영까지이며 운영 서버에는 적용하지 않는다. [실행 정리](../development/runtime-configuration.md)와 [기존 배포 절차](backend-release.md)를 함께 따른다.

## release.json의 파일명 의미

| release.json schema | openapi.yaml | 두 번째 파일 |
|---|---|---|
| 1（기존） | legacy DB0023 계약 | two-cycle.openapi.yaml = 당시 현재 계약 |
| 2（신규 생성） | 현재 계약 | legacy.openapi.yaml = DB0023 계약 |

형식은 필드 `schema`로 구분한다. validation.json·배포 계획·웹 manifest의 schema는 각자 별개다. 기존 Release 파일·태그·hash·운영 상태를 새 파일명으로 소급 변경하지 않는다. 새 제어기는 두 형식을 엄격히 수용하고 혼합 파일명·미지원 schema·hash 불일치를 거절한다. 원문 파일 hash와 실행 생성 객체의 canonical JSON hash는 각각의 검증 목적대로 구분한다.

maintenance의 생성 명세 probe도 schema별 이름 의미를 선택한다. 신형/구형 이미지에서 각각 명시 legacy factory 또는 당시 전역 앱을 사용한다. 표준 API 교체 도구는 schema2에 한해 command의 정확한 `app.main:create_two_cycle_app` 토큰을 동등한 `app.main:create_app`으로 비교한다. worker 수·프록시·환경·mount·DB/Caddy 차이는 여전히 거절하며 실행 중 baseline drift 검사도 유지한다.

## 함께 배포될 변경

운영 원장의 현재 서버는 `v2.1.1` / source `d16734d86e694579cd4e4e043c2ca89cc81c1b64` / DB0036이다. 이번 작업 시작 dev `ffda8db8a00e50719b104605225dc5249f4ae171`과 업무 코드 비교에서 모집 탐색 개선7모듈（192추가/12삭제）이 운영보다 앞서 있다. 즉 다음 배포에는 이번 실행 정리와 함께 #50 `discovery-1` 선택 응답·전체 count·50개 페이지/결과세대 cursor가 포함될 수 있다. #50 기존 응답은 유지되며 새 DB migration은 없다.

다음 운영 승인 직전에 실제 installed source/current 상태와 후보 전체 diff를 다시 대조한다. 위 비교는 저장소/운영 원장 기준이며 이번 작업의 운영 접속 결과가 아니다. 배포 버전·태그·release-validation 계획은 이번에 임의 변경하지 않는다. 공통 main/scripts/config 변경이므로 실제 릴리즈 계획은 full 검증을 선택해야 한다.

## 설치 도구 갱신 순서

1. 운영 배포 승인 시 포함 기능·새 전체 검증 결과·현재 DB0036 호환 이미지·서비스 교체/복귀안을 먼저 제시한다. 운영은 이번 로컬 작업의 자동 연장이 아니다.
2. 배포 작업이 실행 중이지 않은 상태에서 관리자 경로로 `/usr/local/lib/lostparty-deploy/`의 기존 `common.py`·`server.py`·호출 의존 도구와 `/var/lib/lostparty-deploy/` 상태/동결 Compose를 비공개 사본으로 보존한다. 기존 키·환경은 재사용하고 [백업 원장](backup-and-recovery.md)에 변경 도구/시점을 연결한다.
3. 설치 파일 hash가 검토한 기존 값과 같은지 확인하고 **common.py와 server.py를 함께** 검토된 새 버전으로 설치한다. 실행 중인 submit/run/preflight가 없도록 배포 잠금과 관리 창을 사용한다. 먼저 형식2 파일만 보내면 구형 common이 거절하므로 새 이미지 교체보다 선행한다. 제한 SSH·sudo·기존 공개키는 변경하지 않는다. bootstrap/키 생성은 반복하지 않는다.
4. 로컬 격리에서 확인한 schema1/2 검증과 실제 설치 파일 hash·문법을 확인하고 기존 형식 요청의 읽기 전용 preflight로 현재 baseline/HTTPS를 확인한다. 새 형식 요청도 preflight 성공해야 다음 단계로 간다. 기존 request/result와 불변 Release를 다시 쓰지 않는다.
5. 새 Release의 이미지 digest/source/계약/Compose를 고정한다. schema2의 새 명령 외 운영 config는 같아야 하며 DB0036/head 일치가 필수다. 표준 제어기로 API만 교체하고 실제 HTTPS·인증거절·DB/Caddy 동일성·환경/키/mount 보존을 확인한다. 이미지 안에서도 두 생성 명세 전체 객체를 후보와 대조한다.

이 순서는 준비된 절차이며 설치 작업을 이미 실행했다는 의미가 아니다. 운영 전용 보호 설정과 파일명 의미를 바꾸는 수동 우회는 하지 않는다.

## 실패와 복귀

API 교체 실패 시 제어기의 journal에 보존된 직전 정상 이미지/동결 Compose로 API만 복귀한다. DB0036·환경·키·Caddy는 그대로다. 구 명령 `create_two_cycle_app --factory`를 가진 직전 이미지가 대상이며 `create_legacy_app`은 대상이 아니다. 격리 Docker 시험은 이 API 교체/복귀를 실제 컨테이너로 확인하며 DB 업무 검증과 구분한다.

신형 제어기는 schema1도 읽으므로 앱 복귀만을 위해 제어기를 되돌릴 필요는 없다. 구형 제어기 자체로 돌아가야 한다면 실행 중/미완료 journal이 없음을 확인하고 보존한 도구 사본을 함께 복구한다. 새 schema2 요청을 구형 도구에 제출하지 않는다. schema2 current 상태에서 구형 도구를 곧바로 사용하지 말고 검토된 schema1의 이전 이미지/동결 구성을 신형 제어기 또는 관리자 복귀 절차로 먼저 회복한다. 일반 배포의 낮은 버전 차단을 해제하거나 기존 Release JSON을 schema1로 재작성하지 않는다. 자동 복귀 실패 시 추가 배포를 중단하고 비공개 journal을 조사한다.
