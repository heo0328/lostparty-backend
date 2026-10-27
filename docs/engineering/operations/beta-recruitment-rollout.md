# 베타 모집 개발 서버 반영

2026-10-25 / 작업 구간 **베타 개발 반영·자료 보존 검증·인계** / `feat/raid-recruitment`.

사용자 진행 지시에 따라 기존 로컬 개발 서버에 소스 `d95e3827187966ddfa7a111407afdf9e7dd0c3eb`를 적용했다. API 이미지 `sha256:f458e6d57ab3eab4fd46355758d99f2bb5bd95bf9dface55e387babeca147e57`, DB `0032_beta_recruitment`, two-cycle178경로/199 operation이다. 기본앱116/133·기존612 schema는 유지한다. [공개 검증 집계](records/beta-recruitment-rollout.json)·[전체154 Backend · 베타 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6396368027)를 따른다. 이전 개선87c2a0e/366e868a/0031은 [당시 기록](backend-improvements-rollout.md)이다.

## 백업과 자료 보존

적용 전 기존 DB의 일관된 snapshot/custom dump를 별도 내부 네트워크·포트 없는 tmpfs PostgreSQL에 복원했다. 동일 PG 이미지와 제한 계정으로0032 및 실제 앱 모델 초기화/시작 readiness를 확인했다. 이어 실제 API와 worker를 잠시 중지하고 **그 시점의 최신934행**을 다시 백업했다. 과거993행 백업을 실제 DB에 덮어쓰지 않았다. 비공개 백업·키·환경·감사 원문은 접근 제한된 gitignore backups에 보존했다.

추가0032 적용 직후 및 실제 API 재시작 후 기존108표934행 전체 행hash·열정의·기존시퀀스·DBprofile·키hash 일치를 확인했다. alembic_version의 의도된31→32 변경만 제외한다. 새5개 테이블은0행, 새번호sequence는 미사용이다. 기존 모집을 beta 자료로 자동변환하거나 회원 명령을 실행하지 않았다.

기존 DB 컨테이너ID·이미지·영속볼륨과 API 환경 전체·command·appuser/보안·포트·로그10m×5·키mount source/readonly를 보존했다. Docker Desktop의 UNC 경로는 Windows Compose로 렌더링/적용했고 환경 전체 일치를 먼저 확인했다. 백업 전달은 표준입력 스트림을 사용했다. 임시 복원 검증은 실제 ASGI와 같은 모델 초기화를 거친 뒤 readiness를 확인했다. 이번 작업 소유의 reader/복원DB/네트워크만 제거했고 API/DB 모두 healthy다.

## 실제 실행 검증

- 후보와 실행 API의259개 소스/설정hash, 기본116/133·two-cycle178/199 OpenAPI **전체 객체** 및 runtime31 정확 설치목록 일치 PASS.
- 실제 HTTP16 PASS: health/공개주차2, beta 신청목록/상세/후보 두intent 및 presets 무인증/invalidBearer401 ACCESS_INVALID·details=null·no-store/Bearer10, C/N의 legacy/beta 공개검색200·민감필드 부재4.
- 실제 로그62줄 모두 허용 JSON 필드이며 ERROR/CRITICAL0. auth_cleanup/ownership_settlement/recruitment 성공을 확인했다. 원문/개인정보/키/환경값은 게시하지 않는다.

검증 스크립트의 공개주차 경로를 인증이 필요한 v2 metadata에서 공개 v1로 정정한 뒤16건을 통과했다. 이는 서버 코드 결함/수정이 아니다. 기존 격리beta22/관련기존105와 실제HTTP16은 다른 근거이며 합산하지 않는다. 정상회원 명령·기기/provider·부하/로그rollover·운영 인수는 미실행이다.

## 복구와 다음 담당

0032는 기존 증거를 보존하는 추가 migration으로 downgrade를 지원하지 않는다. 이전 API366e868a는0032를 지원하지 않으므로 **DB32 상태에서 이전 이미지만 재시작하는 복구를 하지 않는다.** migration이31에서 롤백된 경우에만 이전API 재시작이 가능하다.32 커밋 이후 장애는 자료를 보존한 전진 수정으로 처리하고 새 데이터 위에 과거 백업을 덮어쓰지 않는다.

[전체154 Backend · 베타 개발 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6396368027)에서 구현소스와 반영기록의 게시SHA를 구분한다. 다음 Flutter는 A 기반의 beta DTO/화면/영속복구 연결과 정상회원 실제 개발 연동을 진행하며 구체 차이를 Issue13에 전달한다. 동일계약 재수용/정상시험 일괄반복 요청은 없다. Backend는 그 차이에 대응한다. Flutter UI·기기 인수/전체모집 인수·IF-001/원ACK 후속은 미완료·Issue13 OPEN이다. dev/main 병합·AWS배포는 이번 범위가 아니다.
