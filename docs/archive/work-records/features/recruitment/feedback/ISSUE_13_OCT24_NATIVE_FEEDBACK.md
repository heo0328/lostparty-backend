> **보관된 작업 원문:** 아래 현재·다음·미구현 표기는 작성 당시 상태입니다. 현재 설명: [weekly-cycles](../../../../../features/recruitment/weekly-cycles/README.md) · [creation-and-settings](../../../../../features/recruitment/creation-and-settings/README.md) · [participation](../../../../../features/recruitment/participation/README.md) · [scheduling](../../../../../features/recruitment/scheduling/README.md) · [completion-and-records](../../../../../features/recruitment/completion-and-records/README.md) · [membership-actions](../../../../../features/recruitment/membership-actions/README.md) · [search](../../../../../features/recruitment/search/README.md). [문서 대응표](../../../../../engineering/documentation/README.md). 원문 바이트와 근거는 기준 커밋 `7f7f767`에서 확인합니다.

# 2026-10-24 — 네이티브 구현 결과·검색/탈퇴/해산 정책 변경 수신

후속설계(같은날): 사용자기획/설계지시에따라 #24 검색/#25탈퇴·해산으로분리하고 [전체137번째 Backend](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6368822874)에설계안1을회신했다. 현재 다음실행은 NEXT_WORK·두설계문서를따른다. 아래는수신당시기록이며구현완료가아니다.

공식 이슈 본문/전체댓글 확인: #22 총5개(새댓글없음), #23 총5개, #13 총136개. 이번은 회신 확인/문서정리이며 새 API/코드/서버·DB 변경·시험·외부댓글/Issue종료는 없다. 구현결과/시험수는 Flutter 보고수신이고 Backend 독립재현이 아니다.

## 구현 결과 수신

- [#23 전체5번째 Flutter · E23 구현/표적검증](https://github.com/heo0328/lostparty-backend/issues/23#issuecomment-6363846643): b6720079b363703d49c0a43e5f78142b1849ed34 push/원격일치 보고. Backend0eed67c/174경로·DB0030 소비, 현재/양T 추방·option별token·review/null/전용ACK·선택T갱신 연결. 고유178mock(신규45+직접기존133)/분석0 보고. D22의133과 합산하지 않는다.
- [#13 전체133번째 Flutter · A 본인완료해제](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6364089791): e9d2783d51ba079c0a3fe6ae88f5a4099b58978a push/원격일치 보고. Backend8bbcfc8/완료정정2경로 소비·0eed67c확장과동일대조, 구 schema1/2 원PUT복구 및 신규schema3 정정원명령/ACK/디스크호환. 최종94mock(신규34+직접기존60)/분석0 보고.
- [#13 전체134번째 Flutter · B 참가/기록·보관읽기](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6364976336): 797c16b3cfcffda849428593fe6c12502eb27499 push/원격일치 보고. current/ended/all·미확정gen review복구행·보관회원detail/plan·새쓰기차단·stopped재개/열린N격리 소비.159mock(신규19+직접기존140)/분석0 보고.
- D22/E23/A/B의 코드·관련자동경계는 Flutter 구현완료 보고다. 정상실회원HTTP/사용자기기 전체인수·성능/메모리·dev/main/운영 완료로 확대하지 않는다.

## 새 실기기 차이 및 Backend 요청

[#13 전체135번째 Flutter · 2차실기기/검색·C탈퇴 보완](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6366977367): 사용자보고로 C단독/C+N생성·기존마지막1인해산 정상. N단독생성 실패는 앱이 effect=target_only를 target_is_next로 오인한 것으로 Flutter407328ef push/직접21mock·분석0 수정보고. Backend 수정요청은 없고 수정본 실제N생성은 미확인이다. 추가 소유인증 원정대/회원이 없어 다인가입/탈퇴/승계는 조건미충족이며 실패/통과로 단정하지 않는다.

검색은 선택T/현재generation의 본인 실제participating 및 필요한review 참가 방을 **서버 SQL 페이지 전** 제외하는 새 요청이다. 단순 지속관계/legacy/not_selected/취소나 반대T 참가를 잘못 제외하지 않는다. 비로그인·정렬/필터/커서·탈퇴뒤 재노출 및 내참가/기록/회원detail/plan·그룹projection 보존을 검증해야 한다. 앱의 페이지뒤필터/카드별GET/내참가사전전체조회로 대체하지 않는다. 기존응답 재사용 우선·계약의 검색기본의미 변경을 정확히 인계한다.

## 최신 정책 — 전체136번째가 135번째 요청2의 이전 제한을 대체

[#13 전체136번째 Flutter · 사용자 최신확정 전달](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6367266418)이 현재 기준이다. 기존 '리더 사전위임/마지막지속회원1인 해산/다인해산 제외'를 새행동의 요구로 계속 적용하지 않는다. **기존 end/leave/cancel API·pending/24h 원ACK의 원효과는 보존**하며 새 행동과 구분한다. D22 완료후탈퇴의 기존인계를 이번 수신만으로 변경하지 않는다.

1. 선택T 탈퇴: C/N 본인참가만 종료. 리더이면 실제참가 순서로 자동승계/빈T종료·반대T보존. 인원수/리더/사전위임을 탈퇴거절조건으로 삼지 않는다. 재참가·동시탈퇴/리더십CAS를 고정한다. 남은review/소유·활동상태로 승계가 어려워도 탈퇴를 막지 않으면서 권한을 부당 확대하지 않는 복구상태를 설계해야 한다.
2. 모두탈퇴: 한명령/한트랜잭션으로 본인 C/N 참가와 지속관계를 정리하고 각T의 자동승계/빈T종료를 독립처리. 반대T리더여도 사전위임하지 않는다.
3. 모집해산: 본인이 리더인 **C/N 주차 전체**를 한명령으로 전원탈퇴/모집종료. C리더/N일반은C만, 반대는N만, 양T리더면양T. 다인도허용·전체마지막지속회원1인 제한제거. 비공대장T의 본인/타인/리더·예약/완료보존. 대상집합을Context/확인/명령/ACK에고정하고 확인중권한/대상변경은재확인하며 범위를몰래확대/축소하지않는다.
4. 참가상세의 두탈퇴버튼은 인원수/승계가능여부로숨기지않음. 해산은리더인관리T가있으면표시·마지막1인사전조회제한제거, 기존위치/빨강·흰글씨/아이콘유지. 확인창은영향주차·날짜와 '해산 대상 주차의 모든 파티원이 탈퇴 처리됩니다.' 및비대상T보존을알림·취소쓰기0.
5. 영향T의 참가/자리·점유/예약·미결신청/일정을정리하고활성검색/참가중에서제외. 다른T유효하면Room전역종료금지. 모든유효T종료시방수명/지속관계·한도정합성을함께처리하고과거완료/감사/기록보존. 취소/해산을게임완료로기록하거나물리삭제하지않음.

## 다음 실행·완료 조건

다음 담당 Backend: 검색과 새 탈퇴/해산의 독립완료조건에 맞는 추적범위를 정리하고 현재구현을 대조한 정확한 계약/호환·권한·복구상태를 설계·회신한다. 미구현이며 새 endpoint/version/DDL 필요여부는 미확정이다. 기존 명령의 본문을 새 효과로 재해석하거나 두 cancel/완료→탈퇴/end 순차호출을 원자명령으로 꾸미지 않는다.

합의된 새범위 구현·표적검증→commit/push·원격확인→closed OpenAPI/대표Context·ACK·리더null/승계 예시/개발API·DB상태 인계가 완료조건이다. 최대8인/마지막1인/역할혼합·review후계·동시탈퇴/확인중권한변경·원ACK/기록/반대T보존에 집중한다. 이후 Flutter가 DTO/원ACK·버튼/확인/영향T무효화·성공이탈을연결한다. 현재이슈는OPEN유지하며기존전체시험/정책재수용을반복요청하지않는다.
