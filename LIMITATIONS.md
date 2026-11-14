# Limitations of TEGB v0.1

Read this before citing any number.

1. **Small dataset.**
   - 82 tasks (74 test tasks plus 8 controls) is small compared with broad EO benchmarks.
   - Category sizes are 6–10 tasks, so per-category and per-model differences have wide intervals.
   - Pooled paired contrasts (984 pairs) are the most reliable numbers.
2. **Origin in TerraUY's operational context.**
   - The evidence structure, statuses and method parameters come from assessments of assets monitored by TerraUY's own organization, produced by TerraUY's land-change and fire-context methods.
   - The method's thresholds and corroboration rules shape what counts as "supported".
3. **Synthetic area values.**
   - For privacy, every area value of 2 ha or more in 66 tasks was replaced by a synthetic equivalent, using independent factors and preserving the method thresholds.
   - The tasks therefore do not describe any real property's actual values. Only 15 tasks are `real_derived`.
   - In an exploratory development-run comparison, the substitution did not change conclusions beyond run-to-run noise (technical report §14).
4. **Coverage of EO.**
   - Only forest change (Hansen, JRC, MGAP) and thermal anomalies (FIRMS), in one country (Uruguay).
   - Not covered: SAR, optical indices, water, crops, urban change, disasters, in-situ sensors, multi-modal imagery.
   - A design-only extension is described in [FUTURE_TRACKS.md](FUTURE_TRACKS.md).
5. **LLM-as-judge.**
   - Labels come from two LLM judges plus a lexical detector.
   - Judge agreement is substantial (κ = 0.732 on UC), but absolute UCR levels depend on the instrument. Pooled RAW UCR is 50.8% with the primary label, versus 38.0% with the Claude judge alone and 18.6% with the detector alone.
   - The paired differences, not the levels, are robust across instruments.
   - The judges see the answer key and a neutral fact sheet. They could still infer something about the condition from the wording of a response, for example quoted field names.
6. **No independent human review of the public baseline.**
   - A 120-response blind review exists only for the development run. It used ChatGPT-generated assessments adopted by the project owner, so it is a robustness check, not independent human or expert validation; ChatGPT also belongs to the same model family as one automated judge.
   - A new blind sample of the public baseline is ready in `results/baseline/blind_review/`. An independent review of it is a prerequisite for strong external claims.
7. **Claude agent truncation.**
   - Provider-default reasoning counts against the preregistered 600-token output cap. 133 of 738 Claude answers were truncated: 121 in RAW, 6 in TEXT, 6 in STRUCTURED.
   - They were not re-run. Excluding the affected pairs does not change the STRUCTURED vs TEXT conclusion.
8. **Anthropic sampling.**
   - `claude-sonnet-5-5` does not accept `temperature`, so the preregistered T = 0 primary run could not be enforced for the Claude agent or judge.
   - Its three runs are three default-temperature samples.
9. **Mixed run dates.**
   - The 16 tasks without area values reuse responses from the first run (identical prompts, verified by hash). The 66 substituted tasks were run later the same day, with the same model ids and serving configuration.
   - API model behaviour may drift between runs.
10. **EVE configuration.**
    - EVE-Instruct was evaluated with the benchmark's common neutral system prompt. That is not the system prompt shown in its model card's code example, and its native setup was not otherwise reproduced.
    - The tasks measure grounding to provided tool evidence, not EO domain knowledge.
11. **Structure vs text.**
    - The result concerns one structured design (`evidence-unit/0.1-exp`) passed directly to agents as JSON, under one prompt.
    - It does **not** show that JSON or structured representations are inherently worse.
    - Other designs (inline constraints, tool schemas, rendering structure into prose) were not tested.
12. **EO specialization.**
    - EVE-Instruct had higher UCR than its base model under this configuration.
    - This is **not** causal evidence that EO specialization reduces grounding. Training data, alignment, prompt format and decoding all differ in ways this design does not isolate.
13. **Prompted single-turn setting.** Agents answered one question from given evidence in ≤ 150 words. Multi-turn, tool-calling and long-form report settings are untested.
14. **Model versions drift.** API models change. The model ids are the exact ids returned at run time (2026-11-13), and future runs of the "same" model may differ.
