# Issue #8 — 서버 장비 해제 인증 연결

2026-10-16. 사용자 연결 진행 지시와 [기존 Flutter 자료](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6210605354)·[70번째 후속](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211581766)에 따른 작업이다. [착수](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211773213)에 신규 원정대 성공과 기존 ID 연결 보류를 구분했다. 기존 Flutter `8f4209deb980660e227134bf1241677875d02e06`의6부위·무작위1~3해제·Type/Name/Grade·10분·명시 확인 흐름과 과거 Android 확인 경험을 근거로 사용한다.

## 서버가 확인하는 내용

기존 uncached siblings/Armory 호출과 엄격한 parser·ArmoryProfile 서버/이름 검사를 통과한 결과에 `ServerEquipmentObservation`을 생성한다. 대상/주소집합 digest·정규화 장비 digest·서버 수집시각을 담는 내부 타입이며 HTTP 요청/응답 DTO에는 노출하지 않는다. live fetch는 기존 boolean proof_validated를 True로 바꾸지 않는다. 격리 시험용 trusted adapter는 기존 엄격 True 경계를 유지하며 live 수집 근거가 있는 경우 그 근거를 우선 검사한다.

시작에는 기존6부위 완전 착용/부위추첨 및 challenge JSON에 `server_equipment_baseline`을 보관한다. 확인은 지정 부위 부재·비지정부위 Name/Grade 유지·시작/확인 대상/주소 집합 일치, 수집 근거의 장비/대상/시각 일치를 검증한다. 기준 수집시각 ≤ 서버 challenge 생성시각 ≤ 확인 수집시각 ≤ 현재시각 < 만료시각이며 확인 수집은 기준보다 나중이어야 한다. 임의 문자열/객체/응답 변형이나 과거/미래 수집 결과를 검증 근거로 수용하지 않는다. 시작 근거 없는 옛 challenge는 기존 PROVIDER_EVIDENCE_PENDING이며 취소/새 시작 경로를 쓴다.

기존 회원/세션·키version·등록/소유 snapshot 및 현재 revision 검사는 유지한다. confirm의 DB 변경을 savepoint에 두고 소유/등록/캐릭터/감사를 flush한 뒤 아직 pending이었던 challenge의 최종 시각을 재검사한다. 기한을 넘으면 해당 변경을 전부 rollback하고 expired/VERIFICATION_EXPIRED·확인횟수·실행결과만 남긴다. 이미 verified였던 challenge는 이 검사로 expired로 강등하지 않는다. 네트워크 호출은 DB 소유변경 lock 밖에 유지한다.

## 성공 범위와 남은 연결

현재 조회에 이름 claim 충돌이 없는 신규 원정대는 기존 transaction으로 account/등록/canonical 캐릭터/감사를 생성하고 verified와 registration_id를 반환할 수 있다. 기존 Flutter 성공 후 관리화면 연결을 사용하며 활동/대표는 자동 선택·저장하지 않는다. 표시상 unconfigured이며 사용자가 명시 저장한다.

기존 account/ID 또는 타소유 원정대는 여전히 BindingEvidence가 필요하다. 이름/같은 목록/장비 제어를 과거 세대 동일성으로 바꾸지 않으며 live binding=None을 해제하지 않는다. 이 경우 start의 기존 ACCOUNT_BINDING_EVIDENCE_PENDING이 유지되고 실행 이력에 남는다. 기존 owned refresh의 연속성 보류도 이번 신규 인증 연결로 해결된 것은 아니다. 소멸 확정/퇴역·claim 해제·24시간 수동 분쟁/새 통지 API는 추가하지 않는다.

## 검증과 계약

공개 paths/DTO/enum/DB구조 불변, OpenAPI의 live_evidence/challenge_context 설명2개만 변경한다. 새 성공 상태/응답 필드 없이 기존 verified/등록 연결 계약을 사용한다. migration/초기화/자료 삭제/이관·새환경은 없다. 기존 개발8000/DB0010에 API만 반영한다.

실제 수집기·HTTP parser를 사용하되 외부 HTTP 응답은 모의로 제공하고 PostgreSQL은 격리 DB를 사용한다. 신규 등록/직접입력 성공·replay/소유1회·활동자동저장0·null/중복/잘못된 응답/서버 불일치·수집 근거 없음/변형/시각 오류·미해제/타부위변경·최종DB작업중만료의rollback·기존claim보류·HTTP success표식거절을 검증한다. 이는 실제 게임/기기 인수 결과가 아니며 사용자 장비 관찰은 결정대로 나중이다. 실제 실행 결과·게시 SHA/원격 및 API 반영 상태는 DEV_LOG/결과 댓글에 기록한다.

최종 격리 PostgreSQL **317PASS·기존 경고1·188.52초**, 앞선 직접검증125PASS/52.34초와 합산하지 않는다. 추가 늦은 동시 확인 경계도 통과했고 초기 실패는 없다. 기존8000 API 반영·실행 전체OpenAPI 일치·health/새모듈 로드·DB0010 유지 확인, test-db만 중지. 실제게임/기기는 미실행이다.

구현/계약 `13d9f6801c90adb691a6a1a8b0abbbe2cdc4ed04`, feat/representative-selection push·원격일치 확인/dev미통합. [72번째 Backend 결과 인계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6211928415). 다음 Backend 기존ID 연결근거 검토, Flutter 실제 계약차이 대조는 필수선행 대기가 아니다.
