<!-- doc-id: plan-execution -->
# Execution checklist

[한국어](plan.ko.md)

## Release 0.0.10 CI repair

T1.60-1 repairs the bootstrap of the repository-owned CI and push-gate workflows before publication. Current jobs fail before tests because Makefile includes the sibling kit checkout that those jobs do not create.

1. Reproduce the missing sibling checkout with workflow unit tests. Each job must check out the project and kit in sibling folders, install kit before project make targets and use paths relative to the project folder for tools and reports.
2. Update only the repository-owned workflows and their tests. Keep every declared check, the final ci-passed aggregation, action pins and report uploads. Shared release and gates workflows remain owned by kit; any defect in them is fixed in kit and adopted through its tools.
3. Run the owning workflow unit tests and document checks, commit the completed item and push only after no item is active. Hosted CI supplies the full test evidence.
4. Publish 0.0.10 only after the required remote checks pass, then verify the release assets and consumer proof. A preparation commit or a local unit test is not publication evidence.
