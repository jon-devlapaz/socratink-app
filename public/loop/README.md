# `/loop` debug surface

`public/loop/` is the standalone terminal UI for direct `/loop` access. It is a
debug and backcompat surface.

The normal learner product flow should enter app-local SEDA through the app
shell and `/api/session`, not through a visible `#nav-loop` route.
