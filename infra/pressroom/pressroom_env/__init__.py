"""pressroom-env — the PressRoom's stages (ENTW, TEST, PROD) on one server.

Three ideas carry it:

  1. A stage is a team folder, a mount, a cockpit and a runner — described in envs.toml, nowhere else.
  2. Test data is production, cloned. A developer never works against an empty or invented pipeline.
  3. Code is staged, rules are not: develop is checked out per stage at its own reference; canon and
     skills are shared and pulled before every run.
"""

__version__ = "0.1.0"
