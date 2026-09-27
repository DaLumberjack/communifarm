# Starter batch lifecycle

Stages: `planned → active → complete`.

Service: `communifarm.transition_batch` with field `stage`.

Each transition appends a `StageChanged` process event. Invalid transitions raise and leave state unchanged.
