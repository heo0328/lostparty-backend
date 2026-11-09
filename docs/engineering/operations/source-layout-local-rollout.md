# 1·2차 폴더 정리 후 로컬 개발 API 반영

2026-11-09 사용자 지시로 현재 소스를 실제 로컬 API에 반영했다. 이 작업은 구조 정리의 실행 기준을 맞추는 것으로, [Issue17 완료 오류 조사](../../features/recruitment/completion-and-records/completion-context-profile-audit.md)의 프로필 불일치를 수정한 배포가 아니다. [반영 집계](records/source-layout-local-rollout.json)가 실행 근거이며 [현재 실행](../../project/NEXT_WORK.md)을 따른다.

## 반영한 소스와 실행 환경

- 브랜치 `feat/character-lifecycle`, 실행 앱은 게시된 `ccf091d5d52d72582ae33d4680ffd7aa73d27474`와285파일 바이트 일치. 미커밋 조사/반영 문서는 런타임 이미지에 포함하지 않는다. 별도 commit/push/merge는 하지 않았다.
- 실제 로컬 API: `sha256:ce59926c2eb63752a0bc69add54ee9239d6d017deff6cf1acaf493d322d9582c` → `sha256:2f86172d390ee70b29ba9617efc7f476c965b425627f6d3d0b21150b2038a763`, 기동시각 `2026-11-09T15:29:46.796551+09:00` (KST). two-cycle factory·환경·포트·키 mount·보안 설정을 유지하고 API만 재생성했다. DB 컨테이너는 중단/재생성하지 않았다.
- Native debug의 기존 로컬 대상을 사용한다. 운영/release 대상과 키·자료·기기는 변경하지 않았다. Native 전체32번째의 기존 오류 분류/진단 한계 수용을 확인했고 전체33번째의 사용자 승인 구현·Backend 계약 보정 요청을 후속으로 접수했다. 새 계약은 아직 미작성이다.

## 보존과 검증

후보와 실제 실행에서 앱285파일·Python282모듈 import와 기본125경로/142동작·two-cycle188경로/209동작의 전체 OpenAPI 객체가 현재 저장소와 같다. 두 계약의 SHA도 기존 값이다. `app.main:create_two_cycle_app`과 worker의 새 경로로 정상 기동했고 API/DB healthy다.

반영 직전/직후 read-only snapshot에서 DB0036·117업무표357행의 전체 행 hash·컬럼/제약/index 구조·sequence가 동일하다. 키4개 내용/권한/소유자·호스트 .env·API 설정·DB ID/image/start/mount/volume도 동일하다. 비밀값/행 원문은 집계에 기록하지 않았다. 새 키·접속 설정·migration·자료 삭제/복원·로컬 DB dump는 없다. 기존 유효한 환경/키 보관본과 로컬 dump 제외 결정을 재사용한다.

실제 localhost listener7개 점검: health/공개주차200, 보호된 경고 GET와 두 완료 POST의 무인증401/ACCESS_INVALID·no-store, docs/openapi.json404다. 완료 POST는 합성 UUID/빈 body·무인증으로 거절됨을 확인했으며 실제 회원의 완료/교체/원정대 갱신 쓰기는 하지 않았다. 새 실행 로그48이벤트에서 오류0을 확인했다. 장시간 성능·모든 사용자 흐름 인수와 구분한다.

## 남은 문제와 후속

선택 프로필 GET과 공대/개인 완료 POST의 공개 선언 불일치는 그대로다. 구 프로필 토큰 검증·원ACK·저장 pending을 유지하며 이번 반영으로 오류 해결을 주장하지 않는다. 새 wire 코드·details.reason·프로필 일괄 제거·자동 새 명령을 도입하지 않았다.

기존 격리 전체1921PASS/기존 기대 불일치2FAIL·신규 미해결0 및 프로필 버그 재현8PASS를 재사용했다. 이번에는 현재 소스의 런타임 이미지/계약/시작·실행 보존 검증을 수행했으며 같은 전체 회귀를 반복하지 않았다. 다음 Backend는 Native 전체33번째의 요청 범위인 완료2경로 및 추가8경로 계약 보완·실제 query 연결 회귀와 고정 계약/hash 인계를 진행해야 한다. Native는 오류 분류·진단정보 보존과 새 계약 소비를 검토하며 기기 성공은 별도다.

공식 반영 인계: [전체34번째 Backend 로컬 반영](https://github.com/heo0328/lostparty-backend/issues/17#issuecomment-6733877672)
