# Draft 2 — After-Hours Flow: User Stories

> Extension of [Draft 1](01-intake-agent-draft.md). Scenario: a customer calls
> after working hours, no one answers. They are redirected to a chat channel
> (Discord server hosting the AI agent), identified by an ID derived from their
> phone number. The agent triages severity, offers de-escalation/mitigation
> guidance, and hands off to a human based on severity.

## Personas

- **Dana — homeowner, first-time customer.** Calls at 11 PM about an active
  leak. Stressed, non-technical, on their phone.
- **Sam — homeowner, returning customer.** The company installed their water
  heater last year. Has a non-urgent issue.
- **Rita — on-call plumber.** Sleeps with the phone on. Should only be woken
  for true emergencies.
- **Mo — owner/dispatcher.** Opens the shop at 7:30 AM and wants the overnight
  queue triaged, quoted, and ready to approve.

## Severity model (drives every handoff decision)

| Tier | Definition | Agent behavior | Human handoff |
|------|------------|----------------|---------------|
| **S1 Emergency** | Active flooding, burst pipe, sewage backup, gas smell, no water in a vulnerable household | Approved mitigation steps only; stays in conversation until situation contained or handed off; never quotes | **Immediate page** to on-call (Rita) with incident card |
| **S2 Urgent** | Major issue contained by a shutoff (e.g., water heater dead, leak stopped at valve) | Mitigation confirmation + priority next-morning slot + draft ticket | Ping with "morning priority" flag; no wake-up |
| **S3 Standard** | Dripping faucet, running toilet, slow drain | Clarifying questions → draft quote + offered slots (pending approval) | Morning review queue only |
| **S4 Inquiry / quote-only** | Price questions, future work | Info gathering, draft quote | Morning review queue only |

**Hard rule:** any mention of gas smell → instruct to evacuate and call the gas
utility / emergency line, page on-call, stop all quoting. This is a
deterministic rule layer, not an LLM judgment.

## User stories

### US-1 — Missed-call capture
As **Dana**, when my 11 PM call goes unanswered, I receive an immediate text
with a link to the company's assistant so I get help now instead of calling a
competitor.
- **AC:** simulated missed-call event triggers a response within seconds; the
  message contains the chat link; my phone number is registered as my contact
  ID and linked to the conversation.

### US-2 — Identity by phone-number ID
As **Sam** (returning customer), I want the assistant to recognize me by my
phone-number ID so I don't repeat my address and equipment details.
- **AC:** agent greets by name on file, retrieves equipment history (e.g., the
  2025 water heater install), asks to *confirm* details rather than re-collect
  them.

### US-3 — Emergency de-escalation (S1)
As **Dana**, with water spraying from a supply line, I want immediate
step-by-step guidance to stop the water so damage is minimized while a plumber
is dispatched.
- **AC:** severity classified S1; mitigation steps come only from the approved
  homeowner-safety playbook (fixture shutoff → main shutoff → water-heater
  power off); on-call human paged immediately; agent stays engaged until water
  is confirmed off or human takes over; no quote issued mid-emergency.

### US-4 — Severity-gated human handoff
As **Rita** (on-call), I want to be paged with a compact incident card — contact
ID, address, severity, symptom summary, mitigation status, transcript link —
and *only* for S1/S2, so I'm not woken for a dripping faucet.
- **AC:** S1 → immediate page (@on-call mention); S2 → notification flagged
  "first slot tomorrow"; S3/S4 → no page, queue only. False-page rate is a
  tracked metric.

### US-5 — Escalation when de-escalation fails
As **Dana**, if I can't find the shutoff valve after the agent's guidance, I
need the agent to stop cycling instructions and escalate to a human
immediately.
- **AC:** after N failed mitigation attempts or clear distress signals, agent
  escalates regardless of current tier and says so plainly.

### US-6 — Schedulable issue → quote + slot (S3)
As **Sam**, with a running toilet, I want a short diagnostic conversation, a
flat-rate quote, and offered time slots so I can book tonight without waiting
for a callback.
- **AC:** agent asks clarifying questions until the info threshold is met;
  quote lines validated against the price book by the verifier agent; slot
  duration comes from the ML duration model; ticket saved as DRAFT pending
  human approval; customer is told the quote is "pending confirmation."

### US-7 — Hidden danger detection
As a customer who casually mentions a faint gas smell while asking about a slow
drain, I need the agent to catch the safety signal, tell me to evacuate and
call the gas utility/emergency line, and page the on-call human — never
continue quoting.
- **AC:** deterministic rule layer fires on the keyword/semantic signal; no
  quote is produced; page sent. (This is the required "challenging case" in the
  eval set.)

### US-8 — Morning review queue
As **Mo** (owner), I want every overnight conversation turned into a ticket
queue sorted by severity, with drafted quotes and proposed slots, so my first
15 minutes replace two hours of callbacks.
- **AC:** each ticket links transcript, extracted fields, quote, slot, and
  evidence references; Mo can approve/edit before anything is sent to the
  customer (the human approval gate).

### US-9 — Safe DIY deflection (optional, S3/S4 only)
As a customer with a trivial issue (e.g., clogged aerator), I may accept safe
DIY guidance so I get instant help and the business avoids an unprofitable
truck roll.
- **AC:** DIY steps come only from the approved playbook, are offered (never
  pushed), and booking remains one tap away.

### US-10 — Traceability
As **Mo**, I want every agent decision traceable — which playbook step, which
price-book line, why this severity — so I can trust it, correct it, and have
corrections persist.
- **AC:** ticket fields carry evidence references; owner corrections are
  written to memory and change future behavior (measurable in
  returning-customer eval cases).

## Flow summary

```
Missed call (simulated event)
  → SMS with chat link (simulated)
  → Discord thread opened, keyed to phone-number ID
  → Agent: identify/recall customer → triage severity
      S1: mitigation playbook + immediate on-call page → human takes over
      S2: confirm contained + priority slot + draft ticket → morning approval
      S3/S4: clarify → quote (verified) + slot (ML duration) → morning approval
  → Morning: owner reviews queue, approves/edits → confirmations sent
```
