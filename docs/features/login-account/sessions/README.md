# 세션·갱신·응답 유실 복구

access token과 refresh token을 사용하는 자체 세션의 수명·회전·응답 유실을 관리한다. 회원 상태와 세션 폐기 여부는 서버 DB가 판단한다.

<a id="behavior"></a>

## 현재 동작

- `/v1/me`는 현재 회원, `/v1/auth/session`은 현재 세션을 조회한다. 로그아웃은 해당 세션을 폐기하며 다른 회원 데이터나 개인 설정을 삭제하지 않는다.
- refresh는 자격 증명을 회전한다. 동일 refresh 거래의 제한된 재시도는 이미 발급한 결과를 복구하고 별도 새 세션으로 중복 처리하지 않는다.
- 합의된 복구 창은60초이며 최초 요청 뒤 추가2회의 동일 거래 복구를 허용한다. 이후 재사용·다른 거래의 사용은 replay 정책으로 처리한다. 정확한 응답·오류·만료는 실행 계약과 서버 저장 시각을 따른다.
- 절대 만료와 유휴 만료를 함께 검사한다. 로컬 시계나 access token 문자열이 남아 있다는 이유로 세션이 유효하다고 단정하지 않는다.
- 회원·환경별 미확정 refresh 거래의 원 secret/거래 식별자를 보존한다. 불명확한 결과를 무조건 새 로그인 거래로 덮지 않는다.

<a id="section"></a>

## 오류·데이터 책임

만료·폐기된 세션401과 정지 회원403을 구분한다. 모든 보호 API에서 현재 세션을 재검증한다. 복구 가능한 동일 거래와 자격 증명 탈취를 의미하는 replay를 같은 무한 재시도로 처리하지 않는다. 원문 refresh·거래 secret·JWT를 로그나 URL에 남기지 않는다.

인증 세션의 refresh 복구와 업무 API의 Idempotency-Key/24시간 ACK 복구는 서로 다른 프로토콜이다. [공통 업무 명령](../../../engineering/data/commands.md).

<a id="decisions"></a>

## 주요 결정과 근거

회전 응답 유실로 정상 사용자가 중복 세션이나 강제 재로그인에 빠지는 문제를 제한된 거래 복구로 처리한다. [복구 설계](../../../archive/work-records/features/authentication/ISSUE_2_REFRESH_RECOVERY.md), [인증 계약](../../../archive/work-records/features/authentication/ISSUE_2_AUTH_CONTRACT_DRAFT.md). 전체 세션 실기기·release 인수와 운영 정책은 기존 후속 목록에 유지한다.

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/auth/session` |
| POST | `/v1/auth/refresh` |
| POST | `/v1/auth/logout` |
