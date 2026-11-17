# 활동 선택 자동추가·명시제외 검토

<a id="behavior"></a>

## 현재 경계

현재 수동 활동 선택·대표·표시 저장은 제공된다. 신규 발견/첫1700 도달 자동추가와 직접제외 영속화는 별도 미합의·미구현이다. 기존 ‘1700은 최초 기본 선택 기준, 저레벨 수동 선택 허용’ 정책을 변경하지 않는다.

<a id="decisions"></a>

## 검토할 입력과 결정

신규 발견의1700 기준, unconfigured/needs_reconfiguration의 pending, V1 delta/V2 명시제외와 선택 없는 제외 해제, 정상 provider 관찰 세대와 settings409 경합, 같은 회원 삭제·재등록 시 제외 복원 여부가 남아 있다. 레거시 미선택을 명시 제외로 추정하지 않으며 다른 소유자에게 제외/선택을 승계하지 않는다.

준비 설계는 별도 기능 브랜치의 로컬5fff83b/미push로 보고돼 있다. 이 문서 정리에서 다른 브랜치 코드를 가져오거나 새 계약을 실행 OpenAPI에 추가하지 않는다. [초안 접수·별도 소비 검토 대기](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603). 다음 담당과 완료 조건은 [추적표](../../../project/ISSUE_TRACKER.md)를 따른다.

[현재 활동·표시 기능](README.md)

## 상세 분석 후보 별도 검토

2026-11-17 Native 전체4/5의 원정대 갱신 절감 설계·제품 확정에 [전체6 Backend B1](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6942884206)로 회신했다. [최신 설계](refresh-candidate-review.md). 공통 관찰/제외 사실을 재사용하되 상세 분석 후보 완료와 활동 자동추가 완료는 분리한다. 현재 구현/API/DDL 확정이 아니다.

현재 상세 분석 후보는 Issue58에서 구현·개발0038 반영 완료이며 사용자 지시로 작업브랜치에 게시한다. Native N1 일반연결/자동검증 보고도 수신했다. [현재 기준](refresh-candidate-contract.md). 이 문서의 활동 자동추가는 계속 별도 미착수이고 옛5fff83b 경로/상태는 당시 이력이다.
