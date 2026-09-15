<!-- doc-id: distribution -->
<!-- source-sha256: c4f493d8b93e47f14bb7c17639a83b9b5f4f656c253df2fef77ee4c65dc9d2ef -->
# 배포

[English](distribution.md)

<a id="state"></a>
## 확인된 상태

[distribution.json](../distribution.json)에 소스와 게시 관측을 기록합니다. 공통 저장소와 다섯 [구현 저장소](../spec/repositories.ko.md#ownership)는 공개 `main` 브랜치를 제공합니다. 각 구현 관측에는 확인한 소스 커밋이 포함됩니다. 기록된 관측에서 GitHub 릴리스와 버전 태그는 발견되지 않았습니다.

npm, crates.io, Packagist, Go, PHP 확장의 레지스트리 게시는 검증되지 않았습니다. 확인된 로컬 배포는 소스 체크아웃입니다. PIE 메타데이터와 성공한 PIE 빌드는 로컬 빌드 호환성을 확인하며 Packagist 게시 근거는 아닙니다. 확장 패키지는 `ordered-json/ordered-json-extension`, PHP 라이브러리는 `ordered-json/ordered-json`입니다.

소스 버전 문자열은 릴리스된 산출물의 근거가 아닙니다. 레지스트리 게시 워크플로와 호스팅 CI는 설정되지 않았습니다. LICENSE 파일은 없습니다.

<a id="source-publication"></a>
## 소스 게시

변경한 패키지의 필수 검사를 실행하고 공통 계약과 함께 커밋합니다. 승인된 모노레포 소스 푸시마다 다음을 실행합니다.

~~~sh
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
~~~

전체 로컬·원격 저장소 커밋 ID가 일치하는지 확인합니다. 같은 체크아웃에서 통합 검사와 해당 PIE 검사를 실행한 뒤 게시합니다. 깨끗한 복제가 게시된 리비전에서 모든 패키지를 빌드하는지 확인합니다. 공통 계약 변경은 검증기, fixture와 관련 패키지를 같은 리비전으로 게시합니다.

인증 정보는 시스템 인증 저장소나 개인 메모리에서 관리합니다. 게시 관측과 테스트 결과를 구분합니다.

<a id="releases"></a>
## 레지스트리와 릴리스 기록

확립되거나 검증된 레지스트리 게시는 없습니다. 릴리스를 기록하기 전에 패키지 이름, 버전, 포함 파일, 레지스트리, 산출물, 검사한 소스 개정본을 확인합니다. 산출물 URL과 게시 관측을 별도로 기록합니다. 확장 릴리스를 게시할 때는 `php-ext` Composer 메타데이터를 사용해 Packagist를 통해 PIE에 등록합니다.

게시 상태가 변경되면 영어·한국어 배포 문서, 기능 배포 상태, 변경 기록을 갱신합니다. 테스트, 버전 선언, 계획된 태그, 소스 푸시만으로 게시를 추정하지 않습니다.
