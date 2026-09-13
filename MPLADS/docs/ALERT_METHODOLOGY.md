# Alert methodology

Alerts are persisted only from calculated signals and higher combined monitoring priority. A SHA-256 fingerprint of release, work, and rule makes alerts idempotent: repeated runs do not create duplicate alerts. Alert severity describes the rule evidence, not guilt. Categories are Financial, Payment, Lifecycle, Duplicate Candidate, ML Anomaly, and Combined. Every alert records source-backed evidence, release version, generation time, and open status.

AI identifies signals; authorized officials make the final decision.
