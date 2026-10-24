> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [scheduling](../../../../../features/recruitment/scheduling/README.md) · [participation](../../../../../features/recruitment/participation/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# #13 R2-A 개인 가능표·방 제출표

2026-10-20. `feat/raid-recruitment`에서 R2의 가능표 저장 구간을 구현했다. R2 전체 완료가 아니다. 다음은 R2-B 지속 membership·캐릭터/슬롯·item/round/assignment와 주간 원장 연결이다. 기존 R1-B 원천/0020을 사용하며 추가 migration은 없다.

## 구현과 계약

- `availability_schemas.py`: strict 입력, required/명시 nullable, ISO 월~일 1..7, HH:mm/5분, end_day_offset 0/1, 양수~24시간, 32bit 양의 버전. DTO는 [고정 초안 §2.1](../contracts/ISSUE_13_FIXED_CONTRACT_DRAFT.md)의 Availability/Submission을 따른다. 제출표 state는 missing/ready/unavailable이며 정상 저장은 ready다.
- `availability.py`: 개인표 GET/PUT, 방 제출표 GET/PUT. 원본 행 순서와 다음날 표현을 보존하고 월요일 00시 기준 분 좌표로 합집합을 파생한다. 일요일 넘김은 경계에서 분할하고 인접·겹침을 병합한다. 미저장 version1/exists=false, 첫 빈 표도 version2/exists=true. 순서까지 같은 원본은 버전·시각을 바꾸지 않는다.
- 방 복사는 개인표·membership·submission 세 CAS를 확인해 같은 transaction에서 snapshot을 저장한다. 같은 source version 재취득은 noop이다. 개인표 PUT/GET·제출표 GET는 다른 표를 갱신하지 않으며 개인 변경 후 이전 제출표를 유지한다. 예약/일정/주간 원장 행과 시각도 그대로다.
- 새 쓰기는 현재 본인 소유·인증된 원정대의 활성 등록이 필요하다. 개인표 기존 조회는 등록 해제 후에도 본인 인증 범위에서 허용한다. 방 표는 현재 membership으로 제한하고 타인/없는 방은 404로 숨긴다. 종료 방/검토 전 legacy 방 신규 복사는 거절한다. legacy 자료를 임의로 ready로 승격하지 않는다.
- 기존 game mutation 잠금/CAS/멱등 원장을 사용한다. 성공 ACK를 함께 저장하고 재송은 현재 인증·방 membership 세대를 확인한 뒤 원 응답을 반환한다. 재송으로 새 버전을 덮어쓰지 않으며 재가입은 이전 membership의 ACK를 사용할 수 없다. 실패 시 표와 ACK가 함께 rollback되고 동일 키 재시도가 가능하다.
- `availability_router.py`는 위 4개 동작의 **미활성 라우터**다. 읽기 body/모든 query·중복 인증/멱등 header·중첩 중복 JSON key·비정상 JSON을 거절한다. 본문은 streaming 단계에서 32768 bytes로 제한한다. GET transaction은 REPEATABLE READ + READ ONLY다.

정확한 미활성 계약은 [recruitment-availability.draft.json](../../../../../../openapi/recruitment-availability.draft.json)이며 `availability_contract.draft_openapi()`와 전체 대조한다. 422 대신 실제 400, no-store/401/REQUEST_IN_PROGRESS 헤더를 반영했다. **원본 openapi/openapi.yaml/main의 실제 공개 계약은 그대로**이며 R5 통합 활성화 때 새 모집 동작과 함께 병합한다. 현재 개발DB0016에 새 라우터만 부분 장착하지 않는다. 일정 불일치·다른 예약 경고는 R3 일정/참가 응답에서 연결하며 이번 저장 서비스가 일정 동의·예약 변경을 수행하지 않는다.

## 입력 상한 근거

기존 P1와 같은 32KiB request 상한을 streaming 수신 중 JSON 파싱 전에 적용한다. 별도 임의 구간 개수 상한은 두지 않으며 인코딩된 body 크기로 제한한다. 합성 5분 간격 분리 구간을 compact JSON 32766 bytes/519행까지 채워 DTO 검증+원본 변환+정규화를 500회 측정했다. 출력519행, median1.997ms/max20.181ms였다. 전용 Docker 테스트 환경의 로컬 CPU 측정이며 실서버 부하/SLA·Flutter 성능 검증이 아니다. HTTP에서 정확히32768 bytes 통과/32769 bytes 거절을 검증한다.

## 검증·미완료

`tests/test_recruitment_availability.py`: 실제 격리 PostgreSQL17/제한 LOGIN + TestClient, 합성 사용자/모의 인증을 사용한다. 원본 복원/빈 표/정규화·CAS/noop/원 ACK·타인 scope/등록 해제·재가입 세대·읽기 무쓰기·크기 경계/strict 입력·동시 CAS 단일 성공·실패 rollback/같은 키 회복·예약/주간/일정/참가 자료 hash 보존·draft/기존 공개 OpenAPI 대조를 검증한다.

실제 API8000/개발DB0016/이미지·자료·외부 provider/Flutter·기기에는 반영·검증하지 않았다. commit/push 상태와 최종 실행 결과는 DEV_LOG/NEXT_WORK를 따른다. R2-B 및 R3~R5는 Backend 후속이며 Flutter 추가 설계 회신 대기가 아니다.
