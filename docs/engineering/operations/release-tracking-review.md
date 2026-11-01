# 릴리즈·서버 반영 이력 운영 협의

2026-11-01 사용자 요청으로 [Issue34](https://github.com/heo0328/lostparty-backend/issues/34)에 Native 운영 확인을 게시했다. 현재는 **[전체1번째 Flutter 운영 기준 회신](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558053848) 수신·Backend 최소 추적안 정리** 단계다. 아래 최초 조사/질문은 당시 근거로 보존한다. 공통 추적 원칙은 양측 의견이 일치하지만 Backend 태그/자동배포·release 브랜치 정책 채택은 미확정이다. 작업 목적은 릴리즈 소스와 실제 사용/서버 반영 시점의 추적이고, 브랜치는 `chore/release-management`다.

## 조사 근거

Backend Issues에서 APK·태그·릴리즈를 검색하고 관련 본문/최신 댓글을 확인했다. [#13 전체193번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/13#issuecomment-6438130915)와 [#16 전체40번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6530680059)·[전체45번째 Flutter](https://github.com/heo0328/lostparty-backend/issues/16#issuecomment-6531439956)는 Git 통합과 APK/태그/운영 배포를 분리한다. 전용 최신 릴리즈 운영 합의는 이번 검색에서 찾지 못했다. Native 저장소 APK/태그 Issue 검색도 결과가 없었다. 이는 모든 외부 운영 기록의 부재를 증명하지 않는다.

Native 로컬 소스는 읽거나 수정하지 않았다. 원격 main 고정 [`45bb7f1f36acb429552ef3086c27be118aa21f11`](https://github.com/heo0328/LostParty_flutter/commit/45bb7f1f36acb429552ef3086c27be118aa21f11)의 [APK workflow](https://github.com/heo0328/LostParty_flutter/blob/45bb7f1f36acb429552ef3086c27be118aa21f11/.github/workflows/android-apk-release.yml)를 직접 읽었다.

| 항목 | 코드/게시 자료에서 확인한 사실 |
|---|---|
| 트리거 | `v*` 태그 push, 수동 workflow_dispatch |
| 태그 검증 | pubspec `<version>+<build>`와 `v<version>` 일치, 태그 커밋의 origin/main 포함 검사 |
| 산출물 | 서명 release APK, package/version/서명 검증, APK/SHA256 artifact 7일 보관 |
| Release 게시 | 태그 실행만 게시, 기존 Release 덮어쓰기 거절 |
| 현재 게시 상태 | [v1.1.0](https://github.com/heo0328/LostParty_flutter/releases/tag/v1.1.0)에 APK/SHA256, [v1.1.1](https://github.com/heo0328/LostParty_flutter/releases/tag/v1.1.1)은 조회 시 asset0개·신규 Backend 준비에 따른 배포 중단 안내 |
| 새 서버 주소 주입 | build는 `flutter build apk --release`; BACKEND_BASE_URL/GOOGLE_SERVER_CLIENT_ID 주입은 이 파일에서 확인하지 못함 |

워크플로 존재가 현재 유효 APK 배포·최신 Actions 성공·사용자 기기 설치를 증명하지 않는다. 태그 커밋의 main **포함** 검사와 정확한 main HEAD 일치 정책도 구분한다. 실제 운영 담당/승인·브랜치·버전 규칙은 Flutter 회신으로 확인한다.

## Issue34에 게시한 확인 사항

1. 현재 유효 문서/워크플로/성공 Actions run/Release와 v1.1.1 배포 중단 상태.
2. 목적 브랜치→dev→main→태그 순서, main 기준점, 버전/build 증가·생성/승인 담당, 목적 브랜치 정리 규칙.
3. 자동 build/artifact/Release와 실제 기기 설치/인수의 경계, 실패/재실행·긴급 수정·태그 불변 정책.
4. 새 Backend 연결 APK의 base URL/OAuth 등록/환경 주입과 소스/산출물/계약/서버 버전 연결 기록.
5. 양측 독립 버전/호환 조합과 통합·게시·실제 반영·인수의 시각/결과를 구분하는 공통 기록 방식.

다음 담당은 **Flutter 운영 기준 회신**, 이후 **Backend 차이 정리/적용안**이다. 완료 조건은 실제 Native 규칙과 현재 배포 경로를 근거로 확인하고 공통 추적 필드·Backend 적용안을 정리하는 것이다. API/기기 재시험·태그 생성·워크플로 실행·서버 변경을 요청하지 않았다.

## Backend 기준과 검토안

Git dev/main 통합 기준은 `a6c6d7b`, 실제 서버 source는 `6154e45`, API이미지 `dfad04e8`, DB0035다. 실제 반영은 [첫 배포 기록](records/lightsail-first-deploy.json), 같은이미지 환경 보완은 [azp 반영](records/lightsail-google-azp-rollout.json)을 따른다. 후행 문서 SHA·main 최신과 실제 실행 source를 구분한다.

검토안은 기존 목적 브랜치/dev/main 역할을 유지하면서 **고정 릴리즈 태그·소스 SHA → 이미지 ID/digest → 실제 환경 반영 시각/결과 → 사용자 인수**를 연결하는 것이다. DB revision·비밀 아닌 환경 버전 표식·이전 정상 기준/롤백 제약과 같은이미지 환경 변경도 남긴다. 앱/Backend 버전 일치 강제 여부, 태그 규칙·발급 시점·실제 적용 완료 기준은 회신 전 미확정이다.

Backend 태그/Release·CI/CD 구현이나 기존 공유 브랜치 규칙을 변경하지 않았고 과거 배포 태그도 생성하지 않았다. 서버/DB/키/자료·외부 백업 구성은 변경하지 않았다. 기존 통합 완료 Lightsail 브랜치를 되살리지 않고 같은 릴리즈 목적 브랜치에서 협의를 이어간다.

## Native 회신 수신과 확인 결과

전체1번째 Flutter 회신은 현재 APK를 **[v1.1.2](https://github.com/heo0328/LostParty_flutter/releases/tag/v1.1.2)** / `1.1.2+4`, source `9e4a18f733f18506752a910f0ae5b6a45b3ede98`로 명시했다. [Actions41306739482](https://github.com/heo0328/LostParty_flutter/actions/runs/41306739482)의completed/success·push/tag v1.1.2·동일head SHA, Release의게시시각`2026-11-01T12:36:02Z`(한국시간21:36:02)와APK/checksum uploaded·APK digest일치를Backend가읽기대조했다. APK SHA256은`568a59cd1d21560ab1a48908cf801a99043a335aaf87b9c6679a6696c2a5b236`이다. APK 바이너리를 내려받아 설치하거나 독립 서명 검증을 수행한 것은 아니다.

고정 [Native 운영 계약](https://github.com/heo0328/LostParty_flutter/blob/9e4a18f733f18506752a910f0ae5b6a45b3ede98/docs/architecture/GITHUB_ANDROID_RELEASE_PIPELINE.md)을 읽어 태그/수동 실행·서명/산출물·실패 처리 경계를 대조했다. 최초 v1.1.1 asset0/중단상태는당시사실이며현재는v1.1.2로게시를재개했다. CI의명시dart-define이없어도제품의release기본URL을사용한다는회신으로주소주입의질문을해소했다. release기본URL은lostparty.duckdns.org이고Web client ID기본값/명시define우선이며debug로컬기본값은별개라는것은Flutter보고/고정계약기준이다.

| 주제 | 회신 결과와 Backend 처리 |
|---|---|
| Native 브랜치 | 목적브랜치→dev→release/버전, 검증후main/dev반영. release브랜치는보존. Backend에PR/동일보존정책을강제하지않음 |
| 소스와 후행 기록 | APK태그는9e4a18f7에유지, Native최신통합/기록f074e7dd는별도. Backend도실행6154e45와Git최신을구분 |
| 버전 | Native pubspec `<name>+<code>`/v태그, 공개후코드수정은새버전. 앱/Backend는독립버전+호환조합연결에동의 |
| 자동화 경계 | 태그는APK게시까지자동, 수동dispatch는artifact까지. 기기설치/인수는별도 |
| 불변성 | 기존Release/asset덮어쓰기거절·공개태그이동/force push없음. 설명보완은산출물교체와구분 |
| 남은 항목 | release OAuth등록/실제서버allowlist일치·게시APK실로그인, 전체호환manifest/기기인수는미확인 |

## Backend 최소 공통 추적안 — 검토용

같은 원칙은 **소스 통합 / 태그·산출물 게시 / 실제 환경 반영 / 사용자 인수**의 구분이다. 각 단계는 `미실행·진행·성공·실패·미확인`과 실제 UTC시각/근거를 남긴다. 이전 단계 성공으로 다음 단계 성공을 추정하지 않는다. Native `release/<버전>` 보존을 Backend에자동복제하지않고기존목적브랜치→dev→main과완료브랜치정리규칙을유지한다. 별도release브랜치필요성·Backend태그이름/버전원장은설계시결정한다.

| 최소 필드 | 기록 내용 |
|---|---|
| component / release_ref | Native 또는 Backend, 독립 version/tag. 아직태그없으면없음으로기록 |
| source_ref / integration_ref | 실제빌드/실행고정SHA와후행문서/Git통합SHA구분 |
| artifact_ref / digest | APK·checksum/Release/run 또는서버이미지ID/registry digest·build근거 |
| environment_ref / contract_ref | 대상주소/환경·비밀아닌설정식별자, 고정API계약commit/파일 |
| stage / status / timestamp_utc / evidence | 위4단계별결과와실제해당단계시각·검증근거 |
| previous_good_ref / rollback_constraints | 이전정상소스/이미지와DB·설정호환제약. DB자동downgrade를전제하지않음 |
| owner / next_action | 담당·남은입력·완료조건 |

Native는package/build/서명인증서digest, Backend는DB revision/환경변경·API재생성시각을덧붙인다. 비밀키·토큰·회원식별자·전체env는기록하지않는다. 장기원칙은운영문서, 실제반영사실은개별기록, 현재대기는NEXT_WORK로분리한다. 이 표는최소문서안이며기계판독manifest/CI schema나자동화구현이아니다.

**현재조합의표시:** Native v1.1.2/source9e4a18f7/APK게시성공 ↔ Backend태그없음/source6154e45/image dfad04e8/DB0035/azp환경반영기록. API계약ref는해당Backend소스의`openapi/two-cycle.openapi.yaml`로연결할수있다. 이연결은비교후보이며release APK와서버의통합인수완료가아니다. 기존실행에새태그를소급발급하지않는다.

[전체2번째 Backend · 현재 사실 대조·최소 추적안](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558101459)으로 회신했다. 다음은 사용자와 Backend 버전/태그·배포 인증/승인·실패 처리 방식을 정리하는 것이다. Native의현재운영방식회신대기는해소한다. release OAuth는기존debug ID만등록된Backend기준과별도로해당서명의정확한공개client ID를확인해야하며미확인값을추정허용하지않는다. 자동배포나기기정상인수반복을이번에추가실행하지않는다.


## release OAuth 후속 운영 반영

사용자콘솔화면과공개ID전사·반영승인으로 release SHA-1/Android client대조대기를해소했다. [전체4번째 Backend](https://github.com/heo0328/lostparty-backend/issues/34#issuecomment-6558294576)·[반영집계](records/lightsail-release-azp-rollout.json)대로기존debug ID에release ID추가/동일API재생성·14분리검증을완료했다. API시작13:00:31Z·health정상, DB/Caddy·키/다른환경보존이다. 위회신당시release등록미확인은과거이력이며직접콘솔API조회/APK독립인증서추출이나실Google로그인성공을의미하지않는다. 다음사용자가v1.1.2 APK새로그인거래를확인한다. 태그자동화/전체호환manifest는별도미완료다.
