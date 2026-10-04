# WhatsApp and Urdu Conversation Architecture

## Channel principle

WhatsApp is the primary participant interface, but the application owns state, evidence, logic, and audit. Use only the official WhatsApp Business Platform through Meta Cloud API or an approved Business Solution Provider selected later. Browser automation and unofficial session scraping are prohibited.

## Integration components

- Webhook verification/signature middleware.
- Provider-event inbox with unique provider IDs and replay protection.
- Contact resolver using encrypted address plus lookup hash.
- Media fetcher with size/type limits, malware scanning, encrypted object storage, and short-lived provider URLs.
- Message normaliser for text, interactive replies, voice, image/file, status, and unsupported types.
- Workflow dispatcher that issues state-machine commands.
- Outbound outbox/sender with rate limits, retries, message-status reconciliation, and template/free-form separation.
- Template registry with provider template ID, language, version, purpose, approval state, variables, and policy window.

The webhook acknowledges after durable persistence, not after the full workflow. Duplicate, reordered, and delayed events are expected.

## Conversation design

Messages are short, natural Pakistani Urdu, one action at a time, and usable by text or voice. Every step has an intent and structured response contract. Periodic progress updates tell the participant where they are, why a question is asked, what happens next, whether a human is reviewing, and what remains uncertain.

Content is versioned separately from workflow. Variants consider school/college/university/adult track, reading level, Urdu script vs participant-established Roman Urdu preference if later approved, and code-switching. The product language team—not a model alone—owns canonical wording.

## Urdu architecture

Store Unicode text as received. Record detected/declared language and script without treating English fluency as intelligence. Maintain:

- Canonical Urdu content with English internal intent/meaning notes.
- Approved terminology glossary for assessment, careers, consent, privacy, fees, and uncertainty.
- Audience-level variants and culturally reviewed examples.
- Back-translation and human review status.
- Prompt/content test cases for ambiguity, formality, code-switching, gendered phrasing, and low literacy.

AI-generated Urdu is a draft. Validate that it references only approved facts, uses the correct stage, avoids diagnoses/certainty, and does not become needlessly formal. High-stakes consent, safeguarding, fee, privacy, and final recommendation content uses approved templates or human review.

## Voice flow

1. Receive voice event and create a media record.
2. Download using provider authentication into quarantine; validate type/size and scan.
3. Store encrypted object under a random key with retention deadline.
4. Send the minimum audio/context to the approved transcription adapter.
5. Store transcript, language hints, provider/model, confidence/segments if available, and link to audio.
6. If quality is low or meaning materially ambiguous, ask the participant to confirm/rephrase or route to review.
7. Interpret structured evidence separately and preserve lineage.
8. Delete original audio and/or transcript according to independently approved retention policies.

Before choosing speech service, benchmark representative consented or synthetic Urdu, Roman Urdu, regional accents, background noise, low-end-phone audio, and Urdu-English code-switching. Do not assume provider claims are sufficient.

## Templates and the 24-hour boundary

Maintain approved operational templates for continuing assessment, experiment reminders, appointment reminders, recommendation readiness, payment, follow-up, and programme invitations. Before production, verify current WhatsApp policies, conversation windows, consent/opt-in, template categories, pricing, and regional availability. Platform policy is temporally unstable and must not be frozen from this plan.

## Opt-out and reminders

Opt-out detection combines explicit keyword/rule matching in Urdu/English/Roman Urdu with conservative classification. Uncertain intent asks one clarification; obvious intent stops automation immediately. Cancel unsent reminders transactionally. Re-entry requires explicit participant action under approved policy.

Reminder schedules are configuration, not invented here. They use local participant timezone when known, permitted communication hours, small attempt limits, and escalation to `PAUSED` after silence. No repeated pressure or bulk unsolicited outreach.

## Failure paths

- Unrecognised response: simpler clarification, selectable choices, then human review.
- Low-confidence transcript: confirmation before evidence use.
- Provider outage/rate limit: queued retry and operator alert; no duplicate send.
- Failed outbound: status reconciliation, bounded retry, alternate human follow-up only if authorised.
- Unsupported/unsafe media: do not open inline; explain accepted formats.
- Template rejection/policy change: disable template version and route work to operations.

## Provider selection criteria

Compare direct Meta and BSP options on official status, Pakistan availability, webhook reliability, template operations, media/voice support, data processing/retention, subprocessor list, security, exportability, support, rate limits, pricing, and vendor lock-in. Keep provider IDs at the adapter boundary.

## Acceptance criteria

1. Duplicate/reordered webhook fixtures produce one logical message/action.
2. State, not generative chat history, determines the next permitted intent.
3. Template and free-form content cannot cross their policy contexts.
4. Text and voice create traceable proposed evidence with uncertainty handling.
5. Opt-out suppresses queued messages and is auditable.
6. Urdu content passes human linguistic/cultural review for each MVP audience band.
