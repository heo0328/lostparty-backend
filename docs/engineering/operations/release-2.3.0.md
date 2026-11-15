# 2.3.0 공동 운영 배포 준비

2026-11-15 / release/2.3.0 / [Issue54](https://github.com/heo0328/lostparty-backend/issues/54). 사용자 진행 지시로 Backend 준비/협업 회신을 수행한다. **현재 운영 미반영, 릴리즈 준비 파일 미커밋·미push, 새 태그/registry digest/최종 배포 source 미확정**이다. Native 버전은2.3.0+8, 고정 소스027f8215cfcf65caa93d9db7aea5a33a38d5b83a다.

## 대상과 기준

| 구분 | 확인 사실 |
|---|---|
| 현재 운영 기준 | v2.2.0/sourcec31d90da4fb5c1eaa9d731623f5648cedc8c00d2·imagecc753718…406dae·DB0036. 기존 [확정 원장](records/release-2.2.0-deployment.json). 이번 공개 HTTPS health는status/database ok. 서버 내부 source/digest·설치도구·동결 baseline의 새 대조는 운영 실행 전 필요 |
| 이번 업무 source | main/dev b7c03615827ac93a6e2ec7e417afe297d13ec359의 같은 앱/계약. VERSION/검증 계획을 올린 준비 브랜치의 최종 게시 SHA는 아직 없음 |
| 새 이미지 | ghcr 불변 digest 미생성. 로컬 add28707…1f71f2는 기능 검증 기준이지 운영 registry digest가 아님 |
| 계약/DB | 현재194경로/216동작, legacy125/142. current canonical SHA256=95b2449b3c3e05970473858f97fd1388c51b0c126d1d6280f128a1fd921bb200, legacy=8936e00f6481d77772751d5fa857ca442007fbbc76ce279a0e8e08f43bf5faa6. DB0036_roster_presence 유지 |

## v2.2.0 대비 포함 범위

- 예약 GET /v2/me/raid-reservations·personal-reservations-1(fe5e082): 달력 수00시와 게임 수06시 구분, 본인 미해제 예약·페이지/결과세대 검증.
- 같은 v2 character-settings GET/PUT의 관리 정책2(9308ce7): main-only·대표 자동 선정/유효대표 유지·활동/대표/순서 원자 저장·부원정대 null/전체movable·구 원문/ACK 복구. v1 writer와 등록/bootstrap 등 현재 앱 reader도 같은 정책을 사용한다.
- 미개방 다음 주 모집 상세의 그룹 표시 None 참조 수정(BUG-036/9a61d0e). 정상 membership relation_only200·일반 상세 TARGET_NOT_OPEN·비회원403 유지.
- #52 기록 표시/페이지 소비 수정은 Native 범위이며 Backend API/DB 계약은 보존한다. Native의 UI/시간표/반응형/생성·상세 개선과 함께 공개한다.
- v2.2.0..b7c0361의 변경을 대조해 migration·배포 common/server/transport·워크플로·운영 Compose/Docker 구성·의존성은 동일함을 확인했다. 새 배포 도구 설치/DB migration·키/OAuth·환경 교체는 계획하지 않는다. 실제 설치된 도구 hash가 기존 원장과 같은지는 교체 전 확인한다.

## 검증과 게시 전 단계

VERSION=2.3.0, release-validation.json은baseline v2.2.0의 **full** 모드로 준비했다. 기존2.2.0 전용 reuse 예외를 연장하지 않는다. app/main.py는 보호 경로이므로 selected도 현재 guard가 거절한다. 기존 기준을 우회하거나 검증 도구에 새 예외를 넣지 않는다.

기존 근거: 정책2 관련 고유220PASS, 예약19+동시 snapshot1, BUG-0365PASS, Native 전체3032PASS/analyze0 및 사용자 보고는 각 당시 검증이며 새 릴리즈 full 성공으로 표시하지 않는다. 이번 배포/웹/릴리즈 도구 선택36시험 PASS와 계획 파싱/문서/diff를 확인했다. 최초 unittest 패키지 경로 오류1건은 PYTHONPATH=scripts/tests의 정식 sibling import 경로로 재실행해 해소했고 도구 코드는 바꾸지 않았다.

1. 준비 파일을 검토/게시해 최종 release source를 고정한다(commit/push는 사용자 직접 지시 기준). 해당 source의 기존 수동 workflow_dispatch는 검증/이미지 build만 하고 publish/deploy를 하지 않는다. full 8-shard·계약·static/도구·Docker 교체/복귀·synthetic web smoke의 새 evidence를 확보한다. 아직 실행하지 않았다.
2. 실패가 있으면 실제 원인/영향을 해결한다. 기존 일부 PASS로 전체 성공을 대체하지 않는다. 성공한 검증 source와 배포 source가 같아야 한다.
3. Native 고정 artifact/해시 인계와 운영 백업/복귀 준비가 갖춰진 뒤 불변 tag v2.3.0을 만든다. tag push는 publish와production deploy까지 이어지므로 단순 검증으로 실행하지 않는다. 기존 태그/Release/공개 파일은 재작성하지 않는다.

## 웹·Android 인계 상태

[Native 전체1](https://github.com/heo0328/lostparty-backend/issues/54#issuecomment-6885858229)의 APK run43653096756·웹 run43653104251을 확인했다. 이후 [전체2 고정 웹 인계](https://github.com/heo0328/lostparty-backend/issues/54#issuecomment-6885913490)를 수신해 artifact14137081307을 연결 도구로 독립 다운로드했다. outer archive digest와 Native가 인계한 내부ZIP/checksum/manifest3파일의 bytes/hash를 모두 비교하고 기존 web_release.verify/stage로 자산34개·source/version/API origin·경로/중복/링크·사이즈·서비스워커 정책을 확인했다. [고정 receipt](records/web-handoff-2.3.0.json). 로컬 /tmp 비활성 stage만 성공했으며 AWS upload/server stage/activate는 하지 않았다. artifact 만료는2026-11-28T23:28:04Z다.

API 성공 후 같은 고정 원본으로 서버 비활성배치→pointer 원자 교체→실제HTTPS 자산/hash/캐시·API 확인→Native Android 공개 순서다. 이후 [전체3 Native](https://github.com/heo0328/lostparty-backend/issues/54#issuecomment-6885949785)가 APK run43653096756 성공/artifact14137081624·기존 서명 검증 완료를 인계했다. APK는 Native 검증 보고로 수용하며 Backend가 APK를 독립 설치/서명검사한 것으로 표시하지 않는다. BUG-038은미재현/미해결로 보관하며 수정완료로 공개 안내하지 않는다.

## 운영 실행 직전 보존·교체

[백업 원장](backup-and-recovery.md)의 기존 키/환경 사본을 재사용한다. DB는서비스 중 변경되므로2.2.0 당시dump를 최신으로 간주하지 않는다. 새 날짜의 운영 DB dump·동일 키/환경·동결 baseline/제어기·활성 웹/pointer를 private backup에 확보하고 기존 PC 보관 경로로 사본/hash를 확인한다. PC 경로나 비밀 원문은 Issue/Git에 남기지 않는다. 실제 복원 시험과는 구분한다.

운영 lock/진행 배포 유무·disk 여유·DB0036·실제 source/digest/서비스와 baseline·설치도구 hash를 먼저 읽어 대조한다. schema2 표준 API-only 경로로 신규 registry digest를 적용하며 DB/Caddy/volume·키·환경/포트·프록시/worker 설정을 보존한다. DB 초기화·마이그레이션/키 재생성·임시 운영회원 쓰기는 하지 않는다. 실제 자료/환경 비교는 사용자 활동으로 달라질 수 있어 같음을 확인한 범위와 차이를 구분한다.

## 복귀 경계

API/웹 공개 전 기술 실패는 표준 제어기의 직전 image·동결 설정과 이전 웹 pointer로 복귀할 수 있도록 원본을 남긴다. DB downgrade/과거 dump 덮어쓰기/ACK 삭제는 사용하지 않는다.

**2.3.0 정책2가 실제 사용된 뒤에는2.2.0의 같은 DB 호환만으로 앱/멱등 복구까지 안전하다고 보장할 수 없다.** 특히 같은 자원의 옛 DTO/원 ACK와 신규 정책2 명령이 함께 존재한다. 자동 제어기의 image 복귀는 프로세스 복귀일 뿐 계약 보장이 아니다. 신규 명령 drain/서비스 교체 순서를 관리하고, 새 API/웹 확인 뒤 Android 공개로 노출을 늦춘다. 노출 이후 장애에는 우선 정책2·기존 원ACK를 지원하는 서버를 유지/전진 수정한다. 전체2.2.0복귀가 필요하면 신규 소비·journal 영향과 쓰기 정지 경계를 별도 검토한다. 복귀 수단을 확인하기 전 배포 준비 완료로 표시하지 않는다.

## 완료 판단

지금은 포함 범위/설정·검증/보존·복귀 계획 준비와 운영 health만 확인한 단계다. full 릴리즈 evidence·최종 source/registry image·운영 내부 preflight/최신 백업·Native APK 최종 인계도 수신했다. 웹 고정 산출물의 독립 로컬 검증은 완료했다. 최종 준비 결과와 실제 운영 교체 결과를 구분해 Issue54에 회신한다. 이번 준비 지시로 tag/push·운영 교체·자료 삭제·Issue 종료는 실행하지 않는다.

## 최초 full 검증과 시험 정정

run43654230797은verify성공/회귀7분할성공·3번분할258PASS1FAIL로종료했다. legacy 최초설정 시나리오가 현재앱에서도 부원정대에 새대표nonnull을 보내200을기대한것이원인이다. 서버는합의대로409 MAIN_REGISTRATION_CHANGED를반환했다. 현재앱시험만메인/부원정대로분리해정책에맞는무대기·원자성·충돌/원ACK검증을보존하고원본legacy시험은그대로뒀다. 새2+legacy1의표적실행3PASS/12.91초. 앱/OpenAPI는불변이며새고정source로full전체를재실행한다. 실패한기존run의7성공을새source전체PASS로재사용하지않는다.
