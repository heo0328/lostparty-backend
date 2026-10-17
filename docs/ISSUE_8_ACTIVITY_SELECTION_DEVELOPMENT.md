# Issue #8 — 수동 활동·대표 선택과 최초 기본 선택 분리

2026-10-17. [115번째 사용자 정책](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230281148)·[118번째 작업 설계](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6230431817)가 아래 과거 수동1700 제한을 대체한다. 현재 작업은feat/raid-services에서 진행한다.

## 현재 동작

- 수동 활동/대표 선택은 현재 소유·등록 범위·canonical UUID·active/confirmed·정상NameClaim으로 판단하며 레벨 하한을 두지 않는다. 레벨 미상이나 잘못된 저장 수치만으로 정상 UUID의 활동 권한을 지우지 않는다. provider 파싱을 느슨하게 바꾸지는 않는다.
- 1700은 Flutter의 최초unconfigured 기본 선택에 유지한다. 서버 GET/갱신은 자동 활동선택/대표 교체를 하지 않는다. 실제 레이드 입장레벨과 전투력 수집 기본값은 별도 정책이다.
- 기존 전체설정PUT/대표전용PUT·DTO·CAS/소유/roster revision·멱등·원자성을 유지한다. 전용명령 main/대표의활동집합포함·타회원/소유상실·suspect/retired/claim 차단도 유지한다.
- settings_out은 레벨만으로 ineligible_character_ids에 넣지 않으며 reconcile은 레벨 하락만으로 needs_reconfiguration을 만들지 않는다. V1 eligible/V2 usable의 lifecycle/claim 의미는 유지한다.
- 이미 needs_reconfiguration인 설정은 GET으로 덮지 않고 기존 선택/대표/revision을 보존한다. 현재 유효한 선택을 기존 명시 전체설정PUT으로 저장하면 configured가 된다. DB 보정/migration/초기화는 없다.
- OpenAPI x-game-account-policy.activity_selection의 minimum_item_level은 initial_selection_minimum_item_level로 바꾸고1700이 초기기본선택임을 명시한다. HTTP 경로·DTO와 다른 정책은 보존한다.

구체 검증·게시·서버 반영 결과는 [설계/결과](ISSUE_8_MANUAL_ACTIVITY_POLICY_PLAN.md)와 [DEV_LOG](project/DEV_LOG.md), 해당 구현 인계 댓글이 기준이다. 아래는 당시 구현/검증 이력이며 현재 수동 자격으로 적용하지 않는다.

# 과거 기록 — 활동 저장1700 검증·초기 대표 연결

2026-10-16. [사용자 UX 정정](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209360031)·[최종 정리](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209491349) 및 사용자 진행 지시를 따른다. [Backend 착수/연결 대조](https://github.com/heo0328/lostparty-backend/issues/8#issuecomment-6209535500)를 게시했다. 현재8000/DB0009/기존자료와 기존관리화면을 유지한다.

## 서버 변경

`activity_policy.py`는 기존 공통 `DEFAULT_MIN_ITEM_LEVEL`을 참조한다. 활동 대상으로 저장하려는 canonical 캐릭터는 현재 소유·등록 범위·active/confirmed/NameClaim에 더해 유효한 item_level >=1700이어야 한다. null/잘못된 수치는0이나정상으로추정하지않는다.

- 기존 전체 character-settings PUT의 선택집합 전체와 대표 전용 PUT 대상을 검사한다. 같은대표 no-op도현재version/자격검사후처리한다. 미달/불명확 대상은기존409 CHARACTER_UNUSABLE, 외부/타원정대/생명주기불가 대상의기존오류경계는유지한다.
- 전체설정은 기존대로 활동집합과 그 안의 명시대표를 같은 transaction에 저장한다. 일부만 저장하지 않는다. 대상/버전실패 시 설정·대표·활동쓰기모두rollback한다. 신규endpoint/DTO/DB구조를추가하지않는다.
- 현재 선택된 저레벨/불명확 대상은 `ineligible_character_ids`에 표시한다. GET이 저장된활동/대표/version을고치거나기존자료를삭제하지않는다. 정상roster갱신에서현재활동이기준미달이면기존needs_reconfiguration경로를사용하되대표/선택목록을보존한다.
- 기존V1 eligible/V2 usable은 lifecycle/claim 상태 의미를 유지한다. 활동저장은최소item level도추가검사하므로Flutter기존공통사용정책과함께판정한다. 소유/canonical상태를item level만으로생성하지않는다. owned 수동상세/전투력권한·미인증기본조회정책은변경하지않는다.

## 초기 대표와 양측 연결

기존대표가있으면유지한다. GET/앱재실행/레벨역전·roster갱신으로대표를최고레벨에맞춰교체하지않는다. 기존관리화면에서현재소유·전체canonical·설정GET의대표없음을확인한뒤초기후보를draft에놓고, 명시적활동집합과그안대표를기존PUT한번으로저장하는방식을Flutter와대조한다. 이미선택한대표와새수동선택을초기자동선정으로덮지않는다. 조회실패/미인증을대표없음으로해석하지않는다.

서버는기존CAS/멱등저장으로초기draft의늦은덮어쓰기를차단한다. 후보는최종명시활동집합포함제약도충족해야하며활동전체자동추가·메인자동전환을하지않는다. 초기후보선정의실제Flutter연결은별도회신/검증대상이다. 서버가null입력을초기자동선정명령으로재해석하거나독립자동선정endpoint를선제구현하지않는다. 별도복구화면/사용자절차를추가하지않는다.

## 검증·실행 경계

신규시험은1700포함경계/불명확값전체rollback·대표no-op자격·저레벨기존선택보존·부원정대설정·초기최고후보명시저장/CAS·재실행/레벨역전무재선정·정상갱신후needs_reconfiguration을포함한다. 실제Flutter화면/게임/소유증거성공시험과구분한다. 실제결과/초기실패·게시/실행반영은DEV_LOG/Issue인계가기준이다. 이구간으로live소유/원정대연속성·퇴역보류를해제하지않는다.

최종 검증: **192PASS·기존경고1·94.07초**. 신규15경계와대표/전체설정/생명주기/V2/개인설정/기본권한/모델·계약직접회귀를실행했다. 기존8000에반영·health/실행소스/전체OpenAPI일치·DB0009유지를확인했다. 초기최고후보를고르는Flutter실제화면연결은회신대기이며서버가자동선정을구현했다고표현하지않는다. 실제게임/소유증거/실기기인수는미확인이다.
