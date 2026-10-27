# 신청·캐릭터 변경 통합 자격 개발 반영

2026-10-24 / 작업 구간명: 모집 신청·캐릭터 변경 통합 자격 개발 반영(#26). 작업 내용은 검증 이미지 교체·자료 보존 확인·실행 계약/HTTP 검증·네이티브 인계이며, 브랜치는 `feat/raid-recruitment`다.

사용자의 진행 지시로 중단된 개발 반영을 재개했다. 구현 source `484ca1719e21b01a59da75b62a1d3b1568ada2c3`, 이미지 `sha256:fdd256ea670f250997d8d6d1f188694f2118a9699c1bdb271da68f6ee5f8b98c`를 실제 로컬 개발 API와 같은 lifespan의 worker에 반영했다. `compose.yaml` + `compose.two-cycle.yaml`, `app.main:create_two_cycle_app --factory`를 유지한다. 신규 후보GET과 신청/context/변경/승인의 공통 판정을 사용할 수 있다.

## 보존·복구 기준

교체 전 API/worker를 정지하고 비공개 DB custom dump·키 백업·설정·읽기 감사를 확보했다. 백업 archive catalog 읽기와 백업 중 DB 불변을 확인했다. DB0031은 그대로이며 migration을 실행하지 않았다. 교체 전후 108테이블·780행 전체의 행 hash·열 정의·시퀀스·DB profile·키 hash가 동일하다. DB 컨테이너/볼륨, API 환경·명령·포트·보안 설정·키 원본 mount 경로/읽기전용도 동일하다. 이미지 소스239파일은 현재 소스와 바이트 일치한다. 비공개 백업 원본은 커밋/게시하지 않았다.

기존 이미지 `sha256:67322372b0e7a92344e62e37b06d06e97f1cbc097d0b8fcaffeab49d86695db6`는 `lostparty-backend-api:before-eligibility26`로 보존했다. 복구 필요 시 먼저 장애·현재 새 쓰기의 호환성을 확인한 뒤 API 이미지만 되돌린다. 과거 DB 백업을 덮어쓰거나 키/볼륨을 초기화하지 않는다. 백업은 archive 읽기까지 확인했으며 이번 구간에서 별도 restore 리허설은 수행하지 않았다.

## 실제 실행 결과

[공개 집계](records/eligibility-rollout.json): 실제 교체 컨테이너에서 two-cycle177/기본116 OpenAPI 객체 전체 일치. HTTP8건은 health200·공개 주차200·신규GET 양intent 각각 무인증/잘못된Bearer401 ACCESS_INVALID·Bearer challenge/no-store4건·C/N 공개검색200/no-store2건이다. API/DB healthy이며 임시 읽기 컨테이너는 제거했다.

기존 [격리45PASS](../../features/recruitment/participation/validation/eligibility-results.json)·Flutter [전체9 구현/493PASS 자체보고](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6382646003)와 이번 실행 검증은 별도 근거다. 실제 회원 세션에서 토큰을 만들거나 회원 명령/자료변경·provider 호출·기기 조작을 수행하지 않았다. 정상 로그인 신청·승인/변경 성공 및 실기기 인수는 미확인이다. dev/main 병합·AWS/운영 배포는 수행하지 않았다.

## 다음 담당

Flutter가 정상 로그인한 앱에서 후보/허용 역할→신청·수락을 소수 항목부터 인수하고 실제 차이가 있으면 #26에 재현 구간·식별정보를 제거한 오류를 회신한다. 변경/반대파티 동의와 생성/상세·일정·완료/해산·C/N 직접 영향도 계속 추적한다. 1~5는 사용자 수동 시험량 구분이며 구현/회귀 제외 기준이 아니다. Backend는 재현 차이에 대응한다. 같은 정책 재수용·기존 전체 시험 반복을 요청하지 않으며 Issue OPEN을 유지한다.

공식 인계: [#26 전체10번째 Backend · 실제 개발 반영/자료보존 검증](https://github.com/heo0328/lostparty-backend/issues/26#issuecomment-6383315604). 반영 근거0096319b027c1da9d2ba0b7cf3667171489c5d9d commit·push·원격일치 확인 후 게시했으며 댓글 전문/실제 전체 순번을 재조회했다.
