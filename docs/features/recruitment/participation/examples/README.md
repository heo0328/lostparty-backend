# 계약 예시·기준 시점 자료

이동 전 JSON 바이트와 내부 $id·버전·상태·역사적 경로를 보존했다. 파일명이 기능 중심으로 바뀌어도 새 계약 합의나 API 변경을 뜻하지 않는다. 설계 snapshot과 합성 응답·성능/실행 보고의 확인 범위를 구분한다. 현재 wire는 실행 OpenAPI가 원본이다.

- [session-display.schema.json](session-display.schema.json)
- [후보조회 제안1 schema](application-character-candidates.proposal.schema.json) — 미합의 초안/최신요구 이전 기준
- [후보조회 제안1 작성 예시](application-character-candidates.proposal.examples.json) — 합성 작성 자료/실제 응답 아님

[전체 자료 대응표](../../../../engineering/documentation/README.md)

- [신청·변경 보완 계약2 schema](candidate-contract-v2.schema.json) — 검토 제안/실행계약 아님
- [보완 계약2 작성 예시21개](candidate-contract-v2.examples.json) — 합성 정적 자료/실제 응답 아님
