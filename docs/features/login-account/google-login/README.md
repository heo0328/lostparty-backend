# Google 로그인·회원 식별

로그인하지 않은 실행과 회원별 데이터 접근을 구분한다. Google 증거를 서버에서 검증해 내부 회원과 세션을 발급하며, 일반 API는 자체 access token만 받는다. 로그인만으로 원정대·등록·캐릭터·활동 설정을 생성하지 않는다.

<a id="behavior"></a>

## 현재 동작

1. 클라이언트가 거래 secret의 해시로 로그인 challenge를 받는다. 서버가 발급한 거래 ID·nonce·만료를 Google 인증과 연결한다.
2. Google 증거와 거래 증명을 교환한다. 서버는 서명·issuer·audience·시각·nonce와 허용된 azp를 검증한다.
3. 같은 외부 identity는 같은 내부 회원에 연결한다. 첫 로그인 경합으로 회원을 중복 생성하지 않는다.
4. 결과의 내부 user UUID와 자체 세션·토큰을 사용한다. Google subject·이름·이메일을 회원 권한이나 공개 식별자로 사용하지 않는다.

앱 인증 실패401과 개인 게임 API 키 거절409는 다르다. 공급 API 키가 거절됐다는 이유로 앱 세션을 로그아웃시키지 않는다. 세션 회전·만료·응답 유실은 [세션 관리](../sessions/README.md), 게임 키는 [개인 API 키](../api-keys/README.md)가 담당한다.

<a id="constraints"></a>

## 정책·미완료

로그인 DTO는 엄격한 입력과 no-store 응답을 사용한다. 클라이언트가 토큰 claims로 서버 권한을 대신 판단하지 않는다. 비로그인 상태에 익명 회원이나 임시 UID를 자동 생성하지 않는다. Apple·Discord 등 추가 공급자, identity 연결·탈퇴·약관·운영 정책은 별도 미완료다.

<a id="decisions"></a>

## 주요 결정과 근거

자체 회원/세션을 사용해 외부 인증 증거와 서비스 접근 권한을 분리한다. [인증 계약 최종 동의](https://github.com/heo0328/lostparty-backend/issues/2#issuecomment-6149615842), [원문 계약](../../../archive/work-records/features/authentication/ISSUE_2_AUTH_CONTRACT_DRAFT.md).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| POST | `/v1/auth/google/challenges` |
| POST | `/v1/auth/google` |
| GET | `/v1/me` |
