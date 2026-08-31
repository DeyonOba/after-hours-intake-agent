# Submission Description (for the HackerEarth form)

**After-Hours Intake & Triage Agent** — When a small plumbing company's phone
goes unanswered at 11 PM, this agent fills the empty dispatcher seat: it
triages severity, walks emergencies through an approved safety playbook while
paging the on-call plumber, and turns everything schedulable into a priced,
slot-assigned draft ticket the owner approves next morning. The design layers
rails around the model's judgment: a deterministic severity floor (code, not
prompt), price-book/calendar/ML-duration tools, a clarifying-question policy,
a programmatic verifier with mechanical enforcement, and phone-keyed customer
memory — with a human gate on every consequential action.

Measured on 18 cases (seeded from real NYC 311 plumbing complaints and a
home-repair QA dataset) against the brief's canonical single-prompt baseline:
critical escalation recall 75%→100% with 0% false pages throughout, usable
quotes 5.6%→100% (0.0% average total error), hallucinated billing codes
16/18→structurally impossible, playbook-cited mitigation 0/6→6/6, ~$0.24 per
intake. The improvement changelog documents every iteration with evidence,
including two real bugs found and fixed — and the hot take they produced: the
model can argue with a revision request; it cannot argue with code. Fully
reproducible: one .env, three commands, deterministic scoring, all agent
trajectories committed.
