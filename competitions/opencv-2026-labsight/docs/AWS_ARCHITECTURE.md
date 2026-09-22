# AWS deployment architecture

Target competition deployment:

1. Browser/demo client submits microscopy imagery.
2. API Gateway or an Application Load Balancer routes to ECS Fargate.
3. The container runs OpenCV 5 and LabSight's deterministic QC toolchain.
4. S3 stores evaluation fixtures and generated evidence.
5. CloudWatch records latency, tool decisions, failure reasons, and QC outcomes.
6. Visual evidence determines a later action: accept, CLAHE plus re-analysis, recapture request, or human review.

Competition evidence still required:
- OpenCV runtime version showing 5.x
- pinned dependency lock and container digest
- P50/P95 latency on a fixed corpus
- decision accuracy on synthetically degraded and consented/open microscopy images
- trace showing vision output changing a later tool call/action
