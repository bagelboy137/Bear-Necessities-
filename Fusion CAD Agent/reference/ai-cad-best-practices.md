# AI-driven CAD: what the evidence says, and what this project does about it

Researched 2026-10-17 for connecting Claude to Autodesk Fusion. Sources are at
the end. Where only an abstract or a search summary was available - several
papers are newer than anything that could be fetched from this environment - the
source is marked *(abstract)* and the claim is no stronger than that.

The procedure that puts this into practice is `.claude/skills/fusion-cad/SKILL.md`.

## The short version

1. **The kernel is the verifier; appearance is a second opinion.** ReliCAD
   argues that "it executed" and "it looks right" are weak signals and builds its
   loop on deterministic CAD-kernel evidence checked against the specification
   *(abstract)*. This project reached the same conclusion independently: bncad
   measures every solid against its spec, and its test suite exists because a
   validation report here once went green over broken geometry.
2. **Feedback has to carry numbers and point at the cause.** In the FEA-feedback
   study, pass/fail verdicts barely moved results for five attempts; adding the
   failure margins and naming the relevant selector or load case produced the
   second large jump *(abstract and summary)*. bncad's "measured, wanted, delta"
   messages are the same finding. A bare "invalid" does not converge.
3. **Small steps, each checked by the kernel, beat one big script.** Embodied CAD
   has the model choose actions from a layered skill library, executes each in a
   CAD backend and feeds solver results back; strong planners executed every
   benchmark workflow *(abstract)*. Autodesk's own Fusion MCP guide says the same
   in practitioner terms: at least one small script per step, validate after
   each.
4. **Look the API up; do not trust recall.** Autodesk's guide tells agents to
   call the API-documentation tool before using any non-standard-library class.
   Work on documentation-augmented generation found retrieval helps most for
   rarely seen APIs and can hurt common ones when the retriever is weak, so
   retrieve selectively. Fusion's API is a rarely seen one - this repo's
   `fusion-api-notes.md` lists members a 7B invented, a different wrong one each
   run.
5. **Visual review helps when it is rich and early, as a second signal.** In the
   FEA study a rich multi-view image review at attempt 2 gave the first large
   jump *(abstract and summary)*. CADCodeVerify (ICLR 2025) has a VLM ask and
   answer verification questions about rendered output and reports gains in
   point-cloud distance and success rate. Autodesk's guide asks for a screenshot
   after every step and a definition of "good enough" ("reasonably centered is
   not good enough").
6. **Nobody one-shots engineering-grade parts yet.** The same FEA study reports
   that Codex (GPT-5.5) and Claude Code (Opus 4.7) agents produced no
   strict-passing artefact in its first-attempt sweep; the best configuration met
   about 20% of typed requirements on average *(abstract and summary)*. Design
   for iteration, and say explicitly that iterating is allowed - Autodesk notes
   agents otherwise accept poor results to avoid redoing work.
7. **Be explicit about units, axes and placement.** Autodesk's guide: state
   dimensions per axis with units. A community skill for Claude + Fusion
   documents that sketch Y on the XZ plane maps to world -Z by design (confirmed
   by Autodesk engineering in the forum thread it cites) and prescribes
   predicting the post-operation bounding box before every operation. This repo's
   own 25.4x STEP bug belongs to the same family.
8. **An assembly is mates and function, not non-intersection.** ASSEMCAD notes
   mechanical function depends on mates, contacts, kinematic constraints and
   assembly topology *(abstract)*. The fusion-mcp-client skill makes it concrete:
   two non-intersecting parts can still be disconnected or misaligned, so check
   mating axes, insertion travel and fastener reach, and track intentional
   overlaps separately from collisions.
9. **Without a verifier, sample several and pick by consensus.** Generating N
   CAD programs and returning the one most geometrically consistent with the rest
   beat random selection by 1-10% Chamfer distance, and matched or slightly beat
   EvoCAD's verifier on its candidate pools *(abstract)*. The margins are small;
   it matters only where the checks cannot tell candidates apart.
10. **Sessions and timeouts are part of the design.** From the maintained
    fusion-mcp-client: a timeout does not tell you whether a script ran, so
    inspect before retrying a write, keep operations sequential, and guard writes
    with the document id and version you expect.

## What the Fusion MCP is and is not good at today

Autodesk's sample-server guide is unusually candid: the MCP is particularly good
at retrieving and analysing information from designs, editing properties of
existing components, and helping write add-ins; independently creating
components from scratch is "not one of the Fusion MCP server's best use cases",
and sketch-heavy shapes are mostly out of reach unless they can be described as
primitives (its workaround: have the model draw an SVG and import it as a sketch).

Field reports agree on the edges. Well-specified basic geometry works; organic
and surface work is weak; sketches drawn with absolute coordinates rather than
constraints break on the first edit; solver errors come back as opaque strings;
and an open command dialog blocks screenshots and API-documentation reads.
These are vendor-adjacent blogs and a forum post, not benchmarks.

That matches this project's split: **bncad builds new parts headless and
verified; Fusion receives, assembles, edits and finishes.**

## Which Fusion MCP server is which

| | Desktop Fusion MCP | Fusion Compute MCP | Fusion Data MCP |
|---|---|---|---|
| Where | inside Fusion on the Mac, `http://127.0.0.1:27182/mcp` (the port moves) | Autodesk cloud, `https://developer.api.autodesk.com/da/v3/mcp/fusion` | Autodesk cloud, `https://developer.api.autodesk.com/fusion/mcp` |
| Status | shipping | **public beta** | shipping |
| Auth | none, local only | Autodesk sign-in (OAuth 2.1), Fusion licence, Fusion Team hub | Autodesk sign-in |
| Does | live modelling in the open session; Python scripts; screenshots | **headless** Fusion: parametric modelling, assemblies and joints, CAM, documents in Fusion Team, STEP/STL export | hubs, projects, folders, manufacturing data model - no modelling |
| Scripts | Python, `def run(_context: str):` | TypeScript via `MCP.ExecuteTypeScript`, or native CRUD tools | - |
| Limits | needs the app open, signed in, a design active | 2 sessions per user, 15 min idle stop, export links expire in 15 min | - |
| From here | `.mcp.json` → `bridge/fusion_mcp_proxy.py` | a claude.ai custom connector | a claude.ai custom connector |

Fusion Compute changes one line of `../CLAUDE.md`: "Headless: **no**, none
exists" was true of desktop Fusion and is no longer true of Fusion. It does not
change the architecture yet - it is a beta, it needs the network and an Autodesk
entitlement, and its cost and quotas are unknown - but it is the obvious
candidate for the unattended Fusion step the mini was never going to manage.

## What was applied

| Finding | Where it lives now |
|---|---|
| Kernel evidence before and after every edit (1, 3) | `bn_snapshot` - `bridge/fusion_snapshot.py`, exposed by the proxy; `snapshot.ts` for Fusion Compute |
| Small steps, predict then measure (3, 7) | skill §2: the loop |
| Look the API up (4) | skill §3; proxy instructions |
| Screenshots as a second signal (5) | skill §2 step 5 |
| Modal dialogs and closing documents block the API | proxy guards, refused before Fusion sees them (and this repo's Memory.md, 2026-08-26) |
| Timeouts do not mean "did not run" (10) | proxy never resends a write that got no reply; it reconnects only when the request provably never arrived |
| The port moves; relaunches drop sessions | proxy rediscovers via `fusion_port.discover()` and re-handshakes |
| Provenance for every change | proxy logs each execute to `bridge/logs/mcp/` |
| Assemblies are mates, not placement (8) | skill §4: components, occurrences, joints, interference |
| Units explicit (7) | skill §3: `ValueInput.createByString("18 in")` |

## Proposed bncad experiments - not applied

bncad's loop is tuned by benchmark, and nothing here can run a model (the cloud
container's network policy blocks the model download). Each of these is a
hypothesis for `bncad bench --repeat` on the mini, not a change to make blind.

1. **Repair from the best attempt, not the last.** When an attempt regresses
   (more failed checks than the best so far), the next prompt shows the best
   script and its errors rather than the regression. Evolutionary CAD
   generation keeps its elite for the same reason. Measure attempts-to-pass and
   pass rate on C-02-U and P06, the marginal parts.
2. **Best-of-N on attempt 1.** Sample three candidates at a higher temperature,
   keep the one with the fewest failed checks; break ties by geometric consensus
   (finding 9). Costs 3x the first call; worth it only if it beats extra repair
   rounds.
3. **A blueprint before code.** Ask for a JSON member/feature table, check its
   arithmetic deterministically (members span the bbox, volumes add up), and only
   then ask for CadQuery. The FEA study's agent has a pre-CAD blueprint stage;
   bncad's prompt already says "ARITHMETIC IS YOUR JOB" - this would check it.
4. **Retrieve on error only.** When a traceback names a missing CadQuery
   attribute, inject that method's real signature into the repair prompt, rather
   than lengthening the system prompt for every call (finding 4: selective
   retrieval).
5. **Multi-view review with the local VLM** (`google/gemma-4-e4b`) as a second
   signal after the numeric checks pass, never instead of them.

## Not verified yet

- **Connection: verified on the Mac, 2026-10-17.** `fusion_mcp_proxy.py
  --status` found live Fusion on 127.0.0.1:27182 (server "MCP Server Adapter"
  1.0.0) offering `fusion_mcp_read`, `fusion_mcp_execute`, `fusion_mcp_update`
  and `fusion_mcp_electronics_read`. **Still unverified:** a script round-trip,
  i.e. `bn_snapshot` on `BN-M01.f3d` through Claude Code in this repo. Its
  `BN-M01-build.json` records 24.0016 × 20.0016 × 18.0016 in and 143
  components, one body each; the snapshot's envelope and `bodies.count` should
  agree (its `design.components` also counts the root, so reads 144).
- The exact argument names of the desktop server's API-documentation query.
  Read the live schema.
- `snapshot.ts` has never run on Fusion Compute; no public Fusion TypeScript
  typings exist to type-check it against, so only its syntax is checked.
- Fusion Compute's pricing, quotas and how it treats Conor's licence.

## Sources

Autodesk, first-party:
- Autodesk Fusion MCP Server; Connecting to the Autodesk Fusion MCP Server; Autodesk Fusion Compute MCP Server; Connecting to…, Tools, Troubleshooting; Autodesk Fusion Data MCP Server - Autodesk product help (ADSKMCP), read through the Autodesk Product Help connector, 2026-10-17
- Fusion API reference: `ValueInput.createByString`, `Design.analyzeInterference`, `Component.allJoints`, `allAsBuiltJoints`, `allRigidGroups`, `JointTypes`, `Sketch.modelToSketchSpace`, "Programming for Design Intent" - same connector
- [FusionMCPSample: "Unlocking the Power of Fusion MCP" (tips.md)](https://github.com/AutodeskFusion360/FusionMCPSample/blob/main/Fusion%20MCP%20Addin/tips.md) and its [README](https://github.com/AutodeskFusion360/FusionMCPSample)
- [Autodesk Fusion connector for Claude](https://claude.com/connectors/autodesk-fusion)
- ["Joint between subcomponent and top level component fails in Fusion"](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Joint-between-subcomponent-and-top-level-component-fails-in-Fusion.html)

Research:
- [Generating CAD Code with Vision-Language Models for 3D Designs (CADCodeVerify), ICLR 2025](https://arxiv.org/abs/2410.05340)
- [Self-Improving CAD Generation Agents with Finite Element Analysis as Feedback, arXiv 2605.17448](https://arxiv.org/abs/2605.17448) *(abstract and summary)*
- [ReliCAD: From Uncertain LLM Generation to Reliable Parametric CAD Modeling, arXiv 2609.22325](https://arxiv.org/abs/2609.22325) *(abstract)*
- [Embodied CAD: Solver-Grounded LLM Agents for Parametric B-Rep Assembly Modeling, arXiv 2606.31252](https://arxiv.org/abs/2606.31252) *(abstract)*
- [ASSEMCAD: Production-Ready CAD Assembly Generation from Natural Language, arXiv 2607.05123](https://arxiv.org/pdf/2607.05123) *(abstract)*
- [Test-Time Scaling for CAD Generation via Verifier-Free Consensus Selection, arXiv 2608.09706](https://arxiv.org/pdf/2608.09706) *(abstract and table summary)*
- [EvoCAD: Evolutionary CAD Code Generation with Vision Language Models, arXiv 2510.11631](https://arxiv.org/pdf/2510.11631) *(abstract)*
- [CADIR: A Cross-Backend Editable Intermediate Representation for Agentic CAD Generation, arXiv 2608.00891](https://arxiv.org/pdf/2608.00891) *(abstract)*
- [On Mitigating Code LLM Hallucinations with API Documentation, arXiv 2407.09726](https://arxiv.org/abs/2407.09726)

Practitioner and community:
- [hitsmaxft/fusion-mcp-client](https://github.com/hitsmaxft/fusion-mcp-client) - client for the official desktop server; its skill and `fusion-operations.md` (MIT)
- [rahayesj/ClaudeFusion360MCP](https://github.com/rahayesj/ClaudeFusion360MCP) - `SPATIAL_AWARENESS.md`, `KNOWN_ISSUES.md`
- [Fusion MCP feedback: dialog visibility limitation (Autodesk forum)](https://forums.autodesk.com/t5/fusion-api-and-scripts-forum/fusion-mcp-feedback-dialog-visibility-limitation-with-claude/td-p/14120453)
- [Leo AI: Claude + Autodesk Fusion review](https://www.getleo.ai/blog/claude-autodesk-fusion-3d-models-review) - a competitor's assessment
- [Colab Software: Autodesk Fusion MCP, Faster CAD, Same Bottleneck](https://www.colabsoftware.com/post/autodesk-fusion-mcp-faster-cad-same-bottleneck)
