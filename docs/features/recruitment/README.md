# 모집·일정

2026-11-10 [Issue17 완료 오류·계정 복구 구간 인수](completion-and-records/completion-recovery-acceptance-20261110.md)와 Native5df515f 게시를 확인했다. 누락 캐릭터/부분 완료 자료·기기 검증과 일괄 완료 기획은 별도 후속이며 전체 Issue 종료는 아니다.

[2026-10-27 통합 체크포인트](integration-checkpoint-2026-10-27.md)에 현재까지의 기능·대표 커밋·계약·검증·개발 반영·Native 수신·남은 인수를 상세히 정리했습니다. Backend 구현 구간의 완료와 전체 기기/운영 인수는 구분합니다.

기능별 현재 동작과 정책은 아래 문서에서 확인합니다. 구체적인 요청·응답 형태는 실행 OpenAPI, 현재 담당·미완료는 [NEXT_WORK](../../project/NEXT_WORK.md)가 원본입니다. 과거 작업 순서를 읽지 않아도 각 기능의 현재 설명을 이해할 수 있게 구성했습니다.

## 구현 파일 찾기

[폴더 분류·이전 경로 추적 방법](../../engineering/development/source-layout.md#현재-파일을-찾는-순서)에서 전체 기준과 1·2차 대응표를 확인합니다. 다음 링크는 현재 구현 위치입니다.

| 찾을 내용 | 현재 위치 |
|---|---|
| 현재주·다음주 HTTP 진입 | [cycle_router.py](../../../app/raid_rooms/api/cycle_router.py) |
| 다음 주 참가 업무 | [cycle_continuation.py](../../../app/raid_rooms/admissions/cycle_continuation.py) |
| 현재주·다음주 입출력 정의 | [cycle_schemas.py](../../../app/raid_rooms/schemas/cycle_schemas.py) |
| 현재주·다음주 DB 모델 | [cycle_models.py](../../../app/raid_rooms/models/cycle_models.py) |
| 원정대 경고 OpenAPI 보정·자원 로딩 | [roster_openapi.py](../../../app/raid_rooms/contracts/roster_openapi.py) |

## 기능 문서

| 하위 기능 |
|---|
| [현재주·다음주 모집 관리](weekly-cycles/README.md) |
| [모집 검색·그룹원 캐릭터 필터](search/README.md) |
| [모집 생성·공통 설정·편성](creation-and-settings/README.md) |
| [참가·승인·캐릭터 변경](participation/README.md) |
| [가능 시간·일정 조율·명시 확인](scheduling/README.md) |
| [완료·정정·보관 기록](completion-and-records/README.md) |
| [탈퇴·추방·해산·공대장 복구](membership-actions/README.md) |

[전체 문서 안내](../../README.md) · [이슈 추적표](../../project/ISSUE_TRACKER.md) · [원문 대응표](../../engineering/documentation/README.md)
