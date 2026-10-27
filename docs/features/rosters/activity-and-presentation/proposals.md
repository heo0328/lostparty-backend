# 활동 선택 자동추가·명시제외 검토

<a id="behavior"></a>

## 현재 경계

현재 수동 활동 선택·대표·표시 저장은 제공된다. 신규 발견/첫1700 도달 자동추가와 직접제외 영속화는 별도 미합의·미구현이다. 기존 ‘1700은 최초 기본 선택 기준, 저레벨 수동 선택 허용’ 정책을 변경하지 않는다.

<a id="decisions"></a>

## 검토할 입력과 결정

신규 발견의1700 기준, unconfigured/needs_reconfiguration의 pending, V1 delta/V2 명시제외와 선택 없는 제외 해제, 정상 provider 관찰 세대와 settings409 경합, 같은 회원 삭제·재등록 시 제외 복원 여부가 남아 있다. 레거시 미선택을 명시 제외로 추정하지 않으며 다른 소유자에게 제외/선택을 승계하지 않는다.

준비 설계는 별도 기능 브랜치의 로컬5fff83b/미push로 보고돼 있다. 이 문서 정리에서 다른 브랜치 코드를 가져오거나 새 계약을 실행 OpenAPI에 추가하지 않는다. [초안 접수·별도 소비 검토 대기](https://github.com/heo0328/lostparty-backend/issues/18#issuecomment-6264981603). 다음 담당과 완료 조건은 [추적표](../../../project/ISSUE_TRACKER.md)를 따른다.

[현재 활동·표시 기능](README.md)
