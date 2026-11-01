# 릴리즈·서버 반영 이력 운영 협의

2026-11-01 사용자 요청으로 [Issue34](https://github.com/heo0328/lostparty-backend/issues/34)에 Native 운영 확인을 게시했다. **조사/질문 게시 완료·Flutter 회신 대기**이며 공통 정책이나 Backend 태그/자동배포 구현 확정이 아니다. 작업 목적은 릴리즈 소스와 실제 사용/서버 반영 시점의 추적이고, 브랜치는 `chore/release-management`다.

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
