# `osce_assessment`

The consumer-agnostic assessment engine: contracts, the exam catalogue,
prompt rendering and LLM evaluation. It knows about frameworks, scenarios,
transcripts and rubrics — never about a product, a tenant or a backend.

Depends on pydantic and nothing else. LLM clients and LiveKit are injected by
whoever uses it.

```python
from osce_assessment.contracts import AssessmentDefinition, Transcript
from osce_assessment.evaluation import LLMEvaluator
```

## Installing it

```toml
osce-assessment = { git = "<repo>", tag = "engine-v0.6.0",
                    subdirectory = "packages/osce_assessment" }
```

Packaged separately from the repo root so a backend that only scores a
transcript does not install livekit, openai and anthropic with it.

## Why this exists

The engine was vendored into `b2c-api` and `b2b-api` with `git subtree` and
drifted: `prompts/debrief_prompt.py` differs between all three copies while
all three report `__version__ = "0.6.0"`, so the version pin could not detect
it. Shipping it as a real dependency makes that impossible.

Bump `version` here and `__version__` in `__init__.py` together, then tag
`engine-vX.Y.Z`.
