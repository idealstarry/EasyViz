# EasyViz project automatic-check entry

Follow the packaged [original-session trigger procedure](../skills/easyviz/references/session-trigger.md).
The project retains its actual original host/session owner. Work in that same
conversation; do not start another editing worker as a substitute.

On a successfully created native scheduled check, inspect this project's actual
`agent_status`. If the registered trigger is absent, disabled or expired, do
not claim scheduled delivery or restart a native task. At its agreed deadline,
stop the native host task and disable the local trigger registration.

For an active registered trigger, reconnect the original owner when its MCP
lease has expired, then call `wait_for_submission` with a bounded wait. Only
a received submitted job authorizes edits; saved drafts alone do not. Report
actual editing, rendering and reviewing starts, render and inspect a fresh
attempt, then record verified completion. If no batch is available, stay quiet.

Native task creation must succeed before local registration. This file, a
local queue or an intended one-minute interval does not create a host schedule
or prove idle delivery. See the [candidate validation record](validation-v0.5.1.md)
for the current verification boundary.
