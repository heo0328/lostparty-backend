# 개인 Lost Ark API 키

회원별 Lost Ark API 키를 암호화해 저장하고 서버의 외부 호출에 사용한다. 앱 로그인 자격과 게임 API 호출 자격은 별개다.

<a id="behavior"></a>

## 현재 동작

| 명령 | 의미 |
|---|---|
| GET | configured/version/updated_at metadata만 반환. 원문·복호화·외부 호출 없음. |
| PUT | 엄격한 compact JWT 형식을 검사하고 암호화 저장. provider의 서명/유효성 검증 완료를 뜻하지 않음. 새 저장은 version 증가. |
| DELETE | expected_version을 검사하고 현재 키만 제거. 원정대·캐릭터·설정은 삭제하지 않음. |
| POST restore | 인증된 본인의 기기 복원을 위한 별도 명령. metadata GET과 구분. |

원문은 최대16KiB이며 공백·개행·Bearer 접두사를 받지 않는다. AES-GCM 암호화와 회원/version 귀속을 사용한다. 멱등 요청 비교에는 전용 fingerprint를 사용하고 원문을 결과나 로그에 남기지 않는다. 저장 자료 GET은 키 없이도 유지된다.

<a id="section"></a>

## 외부 호출·오류

외부 조회가 필요한 명령은 현재 회원 키의 snapshot을 사용하고 반영 직전에 버전·세션을 다시 검사한다. 실행 중 키 교체/삭제 후 옛 결과를 저장하지 않는다. 미등록·provider 거절·진행 중 키 변경·서버 복호화 장애를 각각 구분하며 앱 인증401로 바꾸지 않는다. 서버 공용 환경키 fallback은 사용하지 않는다.

호출 제한과 외부429는 실패/미시작 항목으로 전달하고 기존 정상 수치·시각은 보존한다. 키가 저장됐다는 사실을 게임 API 인증 성공이나 소유 인증 성공으로 표시하지 않는다.

<a id="decisions"></a>

## 주요 결정과 근거

회원별 호출 자격과 캐시 버전을 분리해 공용 키 의존과 다른 회원 결과 재사용을 방지한다. [저장 계약](../../../archive/work-records/features/account/ISSUE_7_LOSTARK_KEY_CONTRACT_DRAFT.md), [본인 기기 복원·호출 대기 보완](../../../archive/work-records/features/account/ISSUE_7_RETRY_RESTORE_CONTRACT_DRAFT.md).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/me/lostark-api-key` |
| PUT | `/v1/me/lostark-api-key` |
| DELETE | `/v1/me/lostark-api-key` |
| POST | `/v1/me/lostark-api-key/restore` |
