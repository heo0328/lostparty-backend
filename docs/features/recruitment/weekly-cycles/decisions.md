# 주차 관리의 주요 결정과 근거

## 주차별 참가를 지속 관계와 분리

방에 남아 있는 회원 관계가 현재주·다음주 모두의 참가를 뜻하지 않는다. 주차별 공대장·참가·예약·완료를 분리해 다른 주차 취소가 기존 주차 자료를 없애지 않게 한다. [주차별 공대장 설계](../contracts/ISSUE_13_TWO_CYCLE_LEADERSHIP_R2.md), [계약 소비 검토 마감](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310097083).

## 생성 시 명시 선택과 다음주 개방

C/N 선택을 하나의 생성 명령으로 확정하고 명시 개방에서만 새 주차를 만든다. 과거 자동 개방 설정을 새로운 참가 동의로 간주하지 않기 위한 결정이다. 조회·설정만으로 새 N 생성/가입을 하지 않는다. [계약 보완](../contracts/ISSUE_13_TWO_CYCLE_CONTRACT_R4.md), [합의 기준 인계](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6310051618).

## 같은 주차 재개와 다음주 개방 구분

사용자가 드문 중단·재개 조작을 줄이기로 결정해 `close_weekly`와 같은 주차 `weekly_resume`를 앱에서 비활성화했다. 데이터 삭제나 기존 명령 복구 차단으로 확대하지 않는다. 다음주 `reopen`은 유지한다. [사용자 최종 결정 전달](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6370006371), [Backend 보존 반영](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6371302557).

## 새 탈퇴·해산과 구 명령의 호환

현재주·다음주 탈퇴·자동 승계와 본인이 리더인 모든 주차의 다인 해산을 새 명령으로 제공한다. 기존 pending/ACK의 원래 효과를 바꾸지 않기 위해 구 leave/end/cancel을 재해석하지 않는다. [정책 변경과 후속 분리](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6368822874), [구현·개발 반영 인계](https://github.com/heo0328/lostparty-backend/issues/25#issuecomment-6371618996).

당시 작업 순서·시험 숫자·배포 전 상태는 원문과 DEV_LOG에 보존한다. 이 문서는 그 상태를 현재 상태로 복제하지 않는다.
