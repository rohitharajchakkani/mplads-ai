# Review authorization

All review APIs require the existing protected monitoring role and scope headers. Scope is enforced in SQL for every read and mutation; case identifiers, frontend visibility, and query parameters grant no authority.

- MP: matching MP source scope only.
- District Authority: matching district / IDA only.
- State Nodal Authority: matching state only.
- Ministry and Platform Administrator: national/system scope.

Mutating endpoints additionally require `X-MPLADS-Actor`. In the current prototype this is a development identity header, not production government authentication. It exists so audit events and notifications are tied to a supplied authorized actor; a production identity provider must replace it.

Out-of-scope cases and source records return 404, avoiding cross-scope record disclosure.
