# Infrastructure and VPS Deployment

## Baseline topology

Use Docker Compose with pinned images and non-root containers:

- Caddy reverse proxy/TLS
- Django web process
- Dramatiq worker processes split by queue
- Scheduler/dispatcher
- PostgreSQL
- Redis
- S3-compatible object storage or external bucket
- Minimal metrics/log collection and alerting

Only ports 80/443 are public. Database, Redis, object storage, and telemetry bind to a private network. Administrative SSH uses keys, restricted users, firewall, updates, and preferably VPN/allow-list. Production secrets and data volumes sit outside the Git checkout.

## Capacity assumptions

Participant count is not the main load driver; message rate, voice minutes, media retention, AI calls, reviewers, and campaign bursts are. Estimates below assume a guided journey over days/weeks, roughly 100–200 messages/events per participant, moderate media, low concurrent operator count, and asynchronous processing. Validate with load tests and real pilot metrics.

| Scale | Suggested starting compute | Database/storage | Service shape |
| --- | --- | --- | --- |
| 100 participants (pilot cohort) | 2–4 vCPU, 8 GB RAM | 80–160 GB SSD plus encrypted off-site backups; object storage sized by voice policy | One VPS acceptable; 1–2 web processes, 2–4 worker processes. Strong monitoring/backups matter more than scale. |
| 1,000 active/enrolled participants | 4–8 vCPU, 16 GB RAM | 200–500 GB SSD or separate managed/DB VPS; external object storage | Separate DB preferred, queue-specific workers, optional second app node, tested failover/restore. |
| 10,000 participants | 8–16 app vCPU and 16–32 GB RAM across 2+ app/worker nodes | Dedicated PostgreSQL 8–16 vCPU, 32+ GB RAM, 0.5–2 TB fast storage; replicated/off-site backups; external object storage | Load balancer, stateless app replicas, dedicated worker pools, managed/HA Redis if needed, read replica/reporting only after measurement. |

These are engineering starting ranges, not purchases or cost promises. If 10,000 means cumulative records with low concurrency, smaller infrastructure may suffice; voice/media or burst campaigns may dominate. Conduct 2x expected peak load tests and maintain at least 30% headroom.

## Storage estimation

Relational structured data is likely modest (kilobytes to low megabytes per journey including indexes). Raw event payloads and logs grow faster; voice/media dominates. Track per-participant:

- database bytes and row counts
- message/event count
- voice minutes and average bitrate
- retained transcript/media age
- audit/log volume
- backup size and duration

Retention decisions are prerequisites for credible storage/cost forecasts. Lifecycle-delete media and verbose provider payloads according to policy; never rely on disk size as a retention strategy.

## Availability and recovery

Provisional targets for the controlled pilot, to be approved:

- RPO: at most 24 hours initially, target 1 hour once real participants are active.
- RTO: 8 hours initially, target 4 hours for controlled growth.

Use daily full plus continuous/WAL or frequent incremental PostgreSQL backups once production begins, encrypted off-site in a different failure domain. Back up object-store metadata/content according to retention. Test restoration to an isolated environment at least quarterly and before material migrations; record achieved RPO/RTO. Backing up is not complete until restore is verified.

## Deployment

1. CI builds immutable image and software bill of materials; runs all gates.
2. Staging deploy applies migrations, health checks, contract and smoke tests.
3. Production backup and migration compatibility check.
4. Deploy with rolling/restart strategy appropriate to one/two nodes; workers stop taking jobs gracefully.
5. Run synthetic health transaction without participant data.
6. Monitor errors, queues, message delivery, and DB health; documented forward-fix/rollback decision.

Database migrations use expand/migrate/contract. Never restore production data into development/staging.

## Monitoring and alerts

Alert on availability, webhook processing delay, queue oldest age, dead letters, outbound delivery failures, provider errors, review backlog/urgent safety case age, CPU/memory/disk, DB connections/locks/replication, Redis memory, certificate expiry, backup/restore verification, error rate, and unusual privileged access. Alerts contain IDs and impact, not message text or phone numbers.

## Self-host vs external

Self-host application logic, database, workflows, operator console, audit, analytics, and optionally object storage/observability when operations can support them. Use official external WhatsApp transport, regulated payment settlement, independent off-site backups, and approved AI/speech services until a self-hosted alternative proves Urdu quality and operational/security economics.

## Scaling triggers

Scale by evidence: sustained CPU >70%, DB latency/connection saturation, queue age violating SLO, storage/backup windows, provider throttling, operator review backlog, or isolation requirements. First optimise queries/indexes, cache safe reference data, and add worker/web replicas. Microservices are a last response to clear boundaries and measured need, not participant count alone.
