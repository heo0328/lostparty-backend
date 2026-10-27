# 서버 주차·개인 완료 원장

서버의 주차와 본인 캐릭터의 개인 완료·파티 완료·현재 점유를 구분해 읽고 기록한다. 수동 체크는 실제 파티 참가나 게임 클리어 검증 증거가 아니다.

<a id="section"></a>

## 시간·조회

주차는 Asia/Seoul 수요일06시부터 다음 수요일06시까지의 `[시작, 종료)`다. API의 실제 cycle_key와 서버 시각을 사용한다. 현재 두 주차 모집의 완료·정정은 현재 T와 수요일10시 이후 조건을 별도로 검사한다.06시 주차 전환과10시 동작 허용을 혼동하지 않는다.

기본 개인 주간 상태 GET과 현재주·다음주 summary POST를 제공한다. summary는 본인 현재 소유 캐릭터 최대50개와 실제 C/N 최대2개를 같은 읽기 snapshot에서 조회한다. 없는 원장은 기본 revision/빈 근거로 읽으며 생성하지 않는다. 확정 참가·검토 필요·명시 의도를 임의로 같은 참가로 표시하지 않는다.

<a id="section-2"></a>

## 쓰기·다른 원천 보존

수동 완료는 본인 권리의 현재주 명시 PUT이다. 난이도별 화면 선택과 같은 레이드의 공유 완료 원장은 별개다. CAS·현재 소유·시각·점유 조건을 검사하고 명령/완료 저장을 원자적으로 처리한다.

manual=false는 본인 수동 근거를 정리하는 기존 의미이며 과거 party snapshot·예약을 되살리는 명령이 아니다. 후속 [본인 완료 정정](../../recruitment/completion-and-records/README.md)은 실제 manual/party 근거를 다루는 별도 context·명령이다. 단순 개인 완료와 [개인 완료후 탈퇴](../../recruitment/membership-actions/README.md)도 구분한다.

<a id="decisions"></a>

## 주요 결정과 근거

하나의 주간 원장에 원천을 구분해 보존하고 조회·수동 입력·실제 참가의 의미를 섞지 않는다. [개인 원장 계약](../../../archive/work-records/features/raids/ISSUE_11_RAID_WEEKLY_DEVELOPMENT.md), [두 주차 summary 근거](../../../archive/work-records/features/recruitment/development/ISSUE_13_W2_READ_SLICE.md), [완료 정정 구현](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6360251618).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)

<a id="api"></a>

## API 계약 찾아보기

표는 현재 실행 OpenAPI에서 수집한 경로입니다. v1/v2가 함께 있어도 입력·효과·ACK의 동등성을 뜻하지 않습니다. 정확한 필수/nullable·오류는 [실행 계약](../../../../openapi/two-cycle.openapi.yaml)을 확인합니다.

| Method | 경로 |
|---|---|
| GET | `/v1/raid-cycle` |
| GET | `/v1/me/raid-weekly-states` |
| PUT | `/v1/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion` |
| GET | `/v2/raid-cycles` |
| POST | `/v2/me/raid-weekly-summary` |
| PUT | `/v2/me/characters/{character_id}/raid-weekly-states/{raid_id}/manual-completion` |
