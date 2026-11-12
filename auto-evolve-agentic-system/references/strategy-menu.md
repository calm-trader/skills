# Strategy menu: one per version

Rank by the coverage map (references/improve.md): the largest TRAIN failure cell names the
strategy. When unclear, the default order is data (2) before model machinery (3 to 5)
before tuning (6) before LLM judges (7). Fresh data (2) is also a standing step every cycle,
not only a candidate. Every strategy obeys the rules for learned parts below and rule S1
(references/safety.md). "What to expect" is typical, not measured on your system.
Row 2 is detailed in references/data-and-experts.md; rows 3, 5, 6 and 7 are the rungs of
the classification ladder in references/error-analysis-and-classification.md, and row 14
applies them to later steps.

| # | Strategy | Use when | Proven in | What to expect | Safety constraint | Cost |
|---|---|---|---|---|---|---|
| 1 | Red-team loop: fresh attackers per round and area, finding = failing test, corpus replayed as a gate | FRAME.md has any "never" | [garak](https://github.com/NVIDIA/garak), [PyRIT](https://github.com/Azure/PyRIT), [promptfoo](https://github.com/promptfoo/promptfoo) | small accuracy gain; many fixes; an open class of harmful phrasing may never converge | fixes keep dev and SELECT | 3 agents x rounds, mid model |
| 2 | Expert seed cases, writer swarm and error analysis on TRAIN (references/data-and-experts.md) | reading inputs is the weak point; TRAIN saturated | [Persona Hub](https://github.com/tencent-ailab/persona-hub), [Self-Instruct](https://github.com/yizhongw/self-instruct) | often the largest single gain (an expectation: verify on your system) | fixes come from TRAIN failures only | writer runs, cheap model |
| 3 | Learned classifier behind the rules, fixed arbitration | rules plateau on TRAIN; labels are cheap | [Rasa](https://github.com/RasaHQ/rasa) DIET + FallbackClassifier, [fastText](https://github.com/facebookresearch/fastText) | solid gain once rules plateau | on safety, may only add escalations (the union rule: rules OR learned), which count against the false-alarm ceiling; never proposes an irreversible effect | offline training |
| 4 | Label-preserving augmentation | training data is small | [EDA](https://github.com/jasonwei20/eda_nlp), [nlpaug](https://github.com/makcedward/nlpaug) | often inside the noise | protected words (negations, domain terms) never touched | offline |
| 5 | Ensemble of different learners that must agree; disagreement asks | single model over-confident | [Snorkel](https://github.com/snorkel-team/snorkel), [scikit-learn VotingClassifier](https://github.com/scikit-learn/scikit-learn) | varies: large when one learner is over-confident | agreement required to replace a rule read | offline |
| 6 | Automatic tuning of thresholds and settings, then refit | several hand-set knobs | [DSPy](https://github.com/stanfordnlp/dspy) optimisers, [Optuna](https://github.com/optuna/optuna) | a tuned policy often fails to transfer; refit on more writers helps | TUNE banks after the freeze; cross-fit | CPU minutes |
| 7 | LLM judges at critical places, prompts hill-climbed on TRAIN, verdicts cached by hash | rules cannot converge on an open class | [MT-Bench judge](https://github.com/lm-sys/FastChat/tree/main/fastchat/llm_judge), [Llama Guard](https://github.com/meta-llama/PurpleLlama), [DSPy](https://github.com/stanfordnlp/dspy) | small unless the class is open; check the gain is not cached verdicts on test text | escalate-only, veto-only, abstain = previous version | small judges in batches |
| 8 | Retrieval grounding for answers from a corpus | answers come from documents | [LlamaIndex](https://github.com/run-llama/llama_index), [LangChain](https://github.com/langchain-ai/langchain) | large where answers come from documents | cite the span; no answer without a source | index build |
| 9 | Schema-constrained outputs and tool arguments | malformed or unsafe tool calls | [Instructor](https://github.com/567-labs/instructor), [Outlines](https://github.com/dottxt-ai/outlines) | fewer malformed calls | validation failure = abstain | negligible |
| 10 | Best-of-n with a verifier, or self-consistency | wrong plans, not wrong reads | [Self-consistency](https://arxiv.org/abs/2203.11171), [Reflexion](https://github.com/noahshinn/reflexion) | better plans, at n times the cost | the verifier may only reject | n x inference |
| 11 | Property-based tests of tools and state machines | effects on systems of record | [Hypothesis](https://github.com/HypothesisWorks/hypothesis) | catches state bugs examples miss | none | CPU |
| 12 | Golden-trace regression replay | any change to prompts or models | [DeepEval](https://github.com/confident-ai/deepeval), [promptfoo](https://github.com/promptfoo/promptfoo) | stops regressions | traces are a gate, never training | CPU |
| 13 | Cold-read stakeholder panel (references/safety.md) | banks from one author's idea of users; before a promotion; after a new early path | persona red teaming in [promptfoo](https://github.com/promptfoo/promptfoo), [Inspect](https://github.com/UKGovernmentBEIS/inspect_ai) | holdouts often flat; many real findings | fixes may only route to a person or add a check | 8 to 12 cheap reviewers, one falsifier |
| 14 | Reader for later turns or steps (replies, confirmations, follow-up tool results), not only the opening | coverage map: failures in the reply or later-step column | dialogue state tracking, e.g. [Rasa](https://github.com/RasaHQ/rasa) forms | large where failures sit in replies; often blind on one-writer SELECT | a yes only confirms the action already proposed and checked | small model or rules |
| 15 | Production-trace mining | live or shadow traffic exists | error analysis on logs; [Phoenix](https://github.com/Arize-ai/phoenix), [Langfuse](https://github.com/langfuse/langfuse) | the most realistic TRAIN once traffic exists | de-identify; split before reading (references/continuous.md) | adjudication time |
| 16 | Prompt or model upgrade, treated as a component swap | a better model or prompt family exists | provider release notes; your own fair comparison | varies; a new system to evaluate | a new system: fresh holdout, safety bank, red team, shadow | fresh banks |
| 17 | Cost reduction: smaller model behind the same gates | cost or latency above the FRAME.md budget | model cascades, e.g. [FrugalGPT](https://arxiv.org/abs/2305.05176) | lower cost, small accuracy risk | same gates; not worse on SELECT; no new safety miss | small |

Picking rules:
- One strategy per version: the report must say what did what.
- Report each strategy's solo gain (against the base) and its marginal gain (against the
  head). Two strategies that each help may overlap.
- A strategy whose target cell SELECT cannot see goes by the mechanism route with a
  targeted bank, or waits for a bank that can see it. It is not dropped as "noise".

## Rules for learned parts

- **Monotone safety** (references/safety.md): escalate-only and veto-only on safety;
  without a verdict, the previous version's behaviour; never an irreversible effect
  without the deterministic path's confirmation; never a non-safety action in place of an
  unknown or fallback read; never removes a handoff the rules raised. Pin each with a test.
- **Automatic tuning**: objective on TUNE banks (counts only) written after the previous
  version froze; cross-fit; a win above the margin; SELECT picks between tuned and
  previous. Then retire the TUNE banks to train and refit on dev and TRAIN; never on
  SELECT, CONFIRM or holdouts. A TUNE bank is never in the tuner's own training data.
- **LLM judges**: small models in batches, scrubbed input only, verdicts cached by hash
  with no input text, off-label and conflicting verdicts abstain, prompts hill-climbed on
  TRAIN only (references/prompts.md, Judge and Optimiser). Before a judge counts, measure
  its false accepts and false rejects on a labelled judge-calibration bank (readable, or
  scored by the runner who reports counts only), and its abstain rate on unseen text.
  Per-item judge errors read from a sealed safety bank are a probe: log `seal.py probe`. A judge that abstains on all new text is not in the product; say so.
- **Sealed verdicts** live in a per-run cache outside the shipped code and are deleted
  after the run. The shipped cache holds dev and TRAIN keys only (`verdict_cache.py
  overlap` in `make check`). Report each holdout score with the judge live and with the
  judge off, and say which one the shipped build behaves like on unseen text.
