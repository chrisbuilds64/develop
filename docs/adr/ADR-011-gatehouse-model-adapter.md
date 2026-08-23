# ADR-011: Gatehouse Model Adapter

**Status:** Accepted
**Date:** 2026-08-22

---

## Context

Gatehouse (UC-AG-004) uses a language model to generate follow-up questions during elicitation. That means client answers are sent to a model. Where that model runs, and who operates it, is the first question any client data protection officer will ask, and it is the question that decides whether the product can be sold into regulated or cautious environments at all.

Client positions differ and none of them can be argued away:

- Some clients hold their own API subscription and want it used.
- Some run models in their own cloud tenant under an existing data processing agreement.
- Some will not let content leave the building and require an on-premise model.
- Some have no position yet and want a recommendation.

A second, quieter reason: model providers and their terms change faster than client contracts do. A product wired to one vendor inherits that vendor's roadmap.

## Decision

**All model traffic passes through one adapter interface. Endpoints are named profiles, tasks are routed onto profiles, and credentials are resolved by the environment.**

Three parts:

**1. One narrow interface.**

The interface is deliberately narrow:

```
send(prompt: str, context: list[Message]) -> str
```

Text in, text out. No provider-specific features, no tool calling, no structured output modes at this stage. Anything a specific provider offers beyond this is out of scope for the core; if it turns out to be indispensable, that is a new decision, recorded separately.

**2. Profiles and task routing.** Configuration declares named profiles (an adapter, a model, a destination) and maps tasks onto them. Not every task warrants the strongest model: follow-up questions during an interview are many small calls, while a synthesis is one call where reasoning quality decides the result. Splitting them is a client decision about cost, made in configuration, and an unknown task name or a task pointing at an undefined profile fails at startup rather than mid-interview.

**3. Credentials belong to the environment, not to this program.** The adapter uses the official Anthropic SDK and constructs a bare client. The SDK then resolves, in order: an API key variable, an auth token, a signed-in profile on disk, workload identity. Gatehouse reads no key and writes no key. A profile may name an explicit key variable when a client keeps several accounts apart on one machine; that is the exception, not the path.

Two obligations sit at the adapter boundary rather than in each implementation:

- **Every outbound call is logged** before it is sent: timestamp, endpoint, the content sent, and token counts. The audit log lives in the instance directory alongside the answers.
- **Configuration declares the destination in plain terms** — provider, endpoint, and whether it is local. This is what appears in the record handed to the client, not a URL buried in an environment variable.

## Alternatives

- **Bind to one provider directly.** Simplest to build, and it converts every client with a different position into a lost sale or a fork.
- **Use an abstraction library** (LangChain or similar). Broad provider coverage for free, at the cost of a large dependency tree that has to pass client IT review, and an interface that changes on someone else's schedule. Against ADR-010's dependency constraint.
- **Call the REST endpoint over raw HTTP and set the key header ourselves.** This was the first implementation and it was wrong. It looked lighter, and it silently ruled out every way of authenticating except a long-lived API key in an environment variable — the one form most likely to be refused by a client's IT department. Nobody decided that; it fell out of an implementation detail. The official SDK is the same dependency weight in practice and keeps all four credential paths open.
- **One model for everything.** Simplest configuration, and it forces a client to pay reasoning-grade prices for mechanical calls or accept weak output on the calls that matter.
- **Route through a gateway service operated by ChrisBuilds64.** Central control and usage visibility, and every client's content passes through our infrastructure. Same objection as hosted SaaS in ADR-010.

## Why the narrow interface

- **A narrow interface is what makes on-premise realistic.** Local models are weaker at provider-specific features and equal at text in, text out. Every capability added to the interface narrows the set of models that can satisfy it.
- **Model choice is a selling point, not a feature.** "You choose the model, and here is the record of what was sent" is a statement that survives a data protection review. "It runs on your hardware" alone does not, because a call to a public API is a call to a public API regardless of where the process started.
- **Logging at the boundary cannot be forgotten.** If each implementation logged its own traffic, a new adapter would silently ship without an audit trail. One choke point means the guarantee holds for adapters that do not exist yet.

## Consequences

**Benefits:**
- A client's existing model contract is honoured instead of displaced.
- On-premise deployment is a configuration change, not a port.
- The audit record is complete by construction, and records which task and which profile each call belongs to.
- Cost is steerable per task without touching code, which is a selling argument as much as an engineering one.

**Trade-offs:**
- Provider-specific capabilities are unavailable. Prompt quality has to carry what tool calling or structured output would otherwise handle, and prompts must work across models of differing strength.
- Output quality varies by configured model, which means support conversations about results that are actually about model choice. The audit log makes this diagnosable.
- More configuration surface. A wrong profile name is a possible mistake that a single endpoint could not make. Mitigated by validating names at startup and by `--check`, which makes one real call per profile before an operator sits down with a client.
- Credential resolution is now invisible to the program, which is the point and also means a misconfigured machine fails at the first call rather than at load. `--check` exists for exactly that.
- The audit log contains client answers verbatim. It inherits the instance directory's protection and must be named explicitly in any data processing agreement rather than treated as a technical detail.
