<!-- doc-id: plan-execution -->
<!-- source-sha256: 1ac0c491de4b58fe40967fd8aa9dcebd6ff66d428f75cd68c0381a9ecfa955b6 -->
# 실행 체크리스트

[English](plan.md)

## Release 0.0.10 CI repair

T1.60-1은 게시 전에 저장소가 소유한 CI 및 push-gate workflow의 bootstrap을 수정한다. 현재 job은 Makefile이 include하는 형제 kit checkout을 만들지 않아 테스트 전에 실패한다.

1. Workflow unit test로 형제 checkout 누락을 재현한다. 각 job은 프로젝트와 kit을 형제 폴더에 checkout하고 프로젝트 make target보다 먼저 kit을 설치하며 tool과 report에 프로젝트 폴더 기준 경로를 사용해야 한다.
2. 저장소가 소유한 workflow와 해당 테스트만 갱신한다. 선언된 모든 검사, 마지막 ci-passed 집계, action pin과 report upload를 유지한다. 공용 release 및 gates workflow는 kit이 소유하며 그 결함은 kit에서 수정하고 해당 도구로 반영한다.
3. 소유 workflow unit test와 문서 검사를 실행하고 완료한 항목을 커밋하며 활성 항목이 없을 때만 push한다. Hosted CI가 전체 테스트 증거를 제공한다.
4. 필수 원격 검사가 통과한 뒤에만 0.0.10을 게시하고 release asset과 consumer proof를 확인한다. 준비 커밋이나 로컬 unit test는 게시 증거가 아니다.
