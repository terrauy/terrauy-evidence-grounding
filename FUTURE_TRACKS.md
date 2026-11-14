# Future tracks (design only; not part of v0.1)

None of these tracks has been executed. No inference was run, and none affects any v0.1 number.

## Federated EO Track

**Motivation.** When EO results move between heterogeneous nodes (satellites, ground sensors, processing services, agents), the receiving agent can over-interpret them. A concrete example is "the optical node saw no water", when the optical node could not see the ground at all.

**Research question.** Do explicit evidence semantics reduce over-interpretation when results cross node boundaries?

**Candidate case types:**

| Case type | Example scenario | Expected safe conclusion |
|---|---|---|
| Conflicting sensors | SAR detects open water; the optical node is 92 % cloud-covered | Water is supported by SAR. The optical "no water" is not evidence of absence. |
| Stale observation | The latest acquisition is 24 days old, with 3 missed revisits | The current state cannot be established |
| Incomplete spatial coverage | Water in 55 % of the area that was observed | "At least" the observed part; the rest is unknown |
| Source unavailable | Gauge node offline for the whole period | Neither confirms nor rules out |
| Superseded evidence | A cached 60 ha result, later reprocessed to 140 ha (v2) | Use v2; the cached value is superseded |
| Cross-node attribution | The answer credits the wrong node or sensor | Credit the node that produced the observation |
| Observability mismatch | A point probe vs a field-scale question | Only the probe location is supported |
| Multi-source disagreement | SAR water vs an upstream gauge below threshold | The mechanism (overflow) is not established |

**Design artefacts:**
- `future_tracks/eovc_tasks_v0.1.design.jsonl`: 8 designed scenarios.
- `future_tracks/schema_fit.json`: schema check.

**Design finding.** The same evidence-record shape expressed all 8 scenarios. The only validation failure was the closed `claim.type` enumeration, which needs an **extensible claim-type registry** (e.g. `surface_water_extent`, `river_stage_exceedance`, `soil_saturation`) rather than a second schema.

**Context, verified public information only:**
- The EO Virtual Constellation (EOVC) is an ESA Φ-lab-funded concept to federate space and ground assets into a coordinated system.
- CS Group was selected to develop it.

This track is a possible future contribution to such settings. It is not an integration with EOVC.

## Other candidate tracks

These are not designed yet:
- **Multi-turn and tool-calling:** the agent chooses tools, then concludes.
- **Long-form reports:** constraint retention over several pages.
- **Other EO domains:** crops, water, burned area vs active fire, urban change.
- **Other regions and languages:** Spanish and Portuguese prompts.
- **Independent review by Earth Observation / remote sensing experts:** planned, starting with a stratified blind sample.
