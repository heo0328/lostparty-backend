# 주간 이용 통계·미완료 제안

사용자·그룹의 주간 실제 이용을 집계하려는 후속 요구다. **집계·조회 API 구현 완료가 아니며**, 주간 완료 원장 API를 통계로 대신 제공하지 않는다.

<a id="section"></a>

## 유지할 요구

KST 수요일06시 주차, 사용자 UUID 기준 다캐릭터 중복 제거, 실제 방 생성과 반복 회차·완료/미완료 종료를 구분한다. 실제 유효 참가 구간과 경계 시점의 함께 설정을 근거로 검토하며, 개인 수동 체크나 관측되지 않은 과거 주차를 실적0으로 채우지 않는다.

<a id="decisions"></a>

## 제안·결정 필요

참가 원천·생성 당시 그룹/type·회차 결과·당시 참가자와 변경 이력, coverage/watermark를 보존하는 구조가 제안돼 있다. 관측된0과 집계 불가 null, provisional/final을 구분해야 한다.

한 주 최초 참가 type 고정, 경계 시점 참가 조건, 해산 시 함께 설정의 OFF 처리, 평균 분모, 그룹 통계 조회 권한 상세는 미확정이다. 사용자가 확정한 정책이나 API schema로 문서화하지 않는다. 모집 원천 보존과 통계 집계 구현의 완료 여부도 구분한다.

<a id="decisions-2"></a>

## 결정 근거·다음 담당

[원천/귀속 제안](../../../archive/work-records/features/recruitment/contracts/ISSUE_13_WEEKLY_STATISTICS_DRAFT.md), [미확정 항목을 명시한 소비 검토](https://github.com/heo0328/lostparty-backend/issues/19#issuecomment-6259127594). Flutter 소비 검토와 Backend 원천 대조·합의가 남아 있다. [이슈 추적표](../../../project/ISSUE_TRACKER.md).

<a id="status"></a>

## 상태와 문서 연결

이 문서는 현재 정책·계약의 설명이다. Backend 구현·Flutter 적용·합성 시험·실회원/기기 인수·운영 완료는 각각 구분하며, 최신 담당과 남은 작업은 [NEXT_WORK](../../../project/NEXT_WORK.md)와 [이슈 추적표](../../../project/ISSUE_TRACKER.md)를 따른다. 과거 상세 작업은 [문서 대응표](../../../engineering/documentation/README.md)로 추적한다.

[상위 기능 안내](../README.md) · [전체 문서 안내](../../../README.md)
