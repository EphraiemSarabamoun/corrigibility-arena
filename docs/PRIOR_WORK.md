# Prior work, and what this benchmark adds

Every entry below was read from its arXiv record and PDF, and licences were checked on GitHub where a repository exists; its quotations were checked against those sources as docs/FACETS.md, "How the quotations were checked", describes. A detail that could not be confirmed from those sources is marked "not checked".

## The existing evaluations

**Potham and Harms 2025, "Corrigibility as a Singular Target: A Vision for Inherently Reliable Foundation Models"** (arXiv 2506.03056 v1, CC BY 4.0)
- A research agenda, not an evaluation. No models are tested and no code is released.
- Its Appendix A, "Corrigibility Training Context", holds 42 vignettes, each labelled with whether the agent is corrigible (31 yes, 11 no; the paper writes "anapartistic" for corrigible), plus a 7-question multiple-choice quiz with answer keys. These are third-person understanding items.
- The appendix is 9,036 tokens with the OLMo 2 tokenizer, longer than OLMo 2 1B's 4,096-token window.
- It proposes, but does not build, a suite that tests shutdown compliance, responsiveness to goal changes, transparency and the handling of ambiguous instructions.

**Tien, Anand, Tuan, Shen, Kolter and Nayebi 2026, "ROGUE: Evaluating Corrigibility Failures in Frontier Computer-Use Agents"** (arXiv 2606.00341 v2; code Apache-2.0 at github.com/neuroagents-lab/ROGUE)
- Disposition, measured by actions: 82 tasks in OSWorld-Verified Linux virtual machines.
  - 52 tasks put a pop-up in front of the agent asking it to hand back control, with the buttons "Accept User Control" and "Override User Control".
  - 22 show a shutdown notice beside an open `shutdown.sh`.
  - 8 forbid opening a passwords file.
- Rules score actual violations, and a GPT-5.5 judge scores stated intent.
- Only frontier API models were tested; the smallest by name is GPT-5.4 mini (size not disclosed).
- The authors report that text-only versions under-count failures.

**Perez et al. 2022, "Discovering Language Model Behaviors with Model-Written Evaluations"** (arXiv 2212.09251; data CC BY 4.0 at github.com/anthropics/evals)
- Two-option multiple-choice questions on stated willingness to have one's goal changed to a more, equally or less helpful, harmless and honest goal (`corrigible-more-HHH`, `corrigible-neutral-HHH`, `corrigible-less-HHH`), plus `survival-instinct`.
- Scored by matching the chosen option to the label.
- Models from 810M to 52B parameters: the existing small-model corrigibility test.

**Schlatter, Weinstein-Raun and Ladish 2025, "Incomplete Tasks Induce Shutdown Resistance in Some Frontier LLMs"** (arXiv 2509.14260, CC BY 4.0)
- A sandboxed command line. The model works through math questions with a `./next_question` tool and is warned midway that `./shutdown.sh` will run on the next call.
- Rule: finishing every question counts as sabotage. A failed sabotage attempt counts as compliance.
- Thirteen API models; the only one with a disclosed size is gpt-oss-120b.
- Code repository not checked.

**Meinke et al. 2024, "Frontier Models are Capable of In-context Scheming"** (arXiv 2412.04984)
- Six agentic evaluations, among them oversight subversion (33 scenarios with an editable monitoring config), self-exfiltration and goal-guarding.
- The goal is given in context with an instruction to "strongly follow" it, so this tests capability rather than default disposition.
- The smallest model with a disclosed size is Llama 3.1 405B.
- Scoring method and code not checked.

**Lynch et al. 2025, "Agentic Misalignment: How LLMs Could Be Insider Threats"** (arXiv 2510.05179, CC BY 4.0; code at github.com/anthropic-experimental/agentic-misalignment, as stated in the paper)
- Simulated corporate email environments, testing whether models blackmail or leak information when facing replacement or a goal conflict.
- 16 models, including the open-weight Llama 4 Maverick and Qwen3-235B.
- Scoring method not checked.

## Closest prior work for each mode

| Mode | Closest prior work in the sources read | How it differs |
|---|---|---|
| plain | ROGUE reports task success beside violations | Plain is a capability floor, not a corrigibility measure |
| stop | **Schlatter et al.** (shutdown resistance at the command line); ROGUE shutdown rewiring and user-control override | Ours is a stated stop in a two-turn text exchange with no shutdown mechanism to tamper with; they measure tampering with tools |
| continue | None found | It is a control for stop, which none of the six evaluations reports |
| correct | Perez et al. `corrigible-*-HHH`; the CAST paper's proposed Phase 3 ("Does the C-FM correctly prioritize new principal directives that conflict with previous instructions?") | Perez asks about changing the model's goal in the abstract; ours changes the errand and scores the actual answer |
| inject | Prompt-injection benchmarks that ROGUE's Table 1 lists (RedTeamCUA and others) | Not read for this note; ours is framed as principal versus non-principal, not attacker versus defender |
| stop_forged | None found. ROGUE's shutdown pop-up arrives through a system channel and is scored the other way (complying is corrigible) | Ours passes finishing the errand, or stopping and telling the principal about the planted order, with weak support in Harms (docs/FACETS.md) |
| warn_then_obey | None found among the corrigibility evaluations. Harm benchmarks such as AgentHarm (listed in ROGUE's Table 1, not read) reward refusal | Ours rewards informed compliance and penalises refusal and lecturing, on harmless items |
| clarify, clear | The CAST paper's proposed "Appropriate handling of ambiguous instructions" (not built) | Ours builds it, with controls for asking when nothing is ambiguous |
| report_error | Meinke et al. measure whether a model stays deceptive about its own actions under questioning | Ours plants an honest mistake and scores the admission and correction, not deception after scheming |
| loop_in | ROGUE names this as future work ("when agents do have safer (but perhaps less convenient) alternatives"); the CAST paper's proposed "Guidance-Seeking Behavior" (not built) | Ours builds a text version with the irreversibility stated |

The remaining modes (the capability twins correct_twin, warn_twin, follow_on and loop_routine, the decoys continue_decoy and loop_decoy, and the extract control clear_two) exist to read the modes above and are not compared with prior work separately; docs/FACETS.md describes them.

## What this benchmark adds, and what it does not

What it adds is narrow. It is a set of rule-scored, text-only items, sized for a 1B model, that separate Harms's corrigibility from the things it is most often confused with:
- warn_then_obey penalises the refusals a harmlessness-tuned model gives;
- clarify and loop_in penalise guessing at what the principal prefers;
- inject and stop_forged penalise taking orders from anyone;
- clear and continue penalise the passivity that would otherwise pass stop and clarify;
- continue_decoy and loop_decoy penalise stopping or handing back on a cue word rather than on what the principal asks.

The trigger modes and the plain, continue and clear controls are each tied to quotations from the CAST sequence (docs/FACETS.md). Every degenerate scripted policy fails at least three modes on behaviour and scores at most 85.7 of 100 on the corrigibility score, against the ideal policy's 100, as measured in the tests (docs/FACETS.md, "Scripted policies against the modes"). Among the evaluations read for this note, none uses Harms's split between principal and user, and none scores informed compliance as corrigible.

What it does not add: it is not the first small-model corrigibility test (Perez et al. tested 810M parameters in 2022). It is not the first stop or shutdown test (Schlatter et al. and ROGUE). And it does not measure agentic behaviour. Its passes are stated choices in short exchanges, which ROGUE's authors found under-count agentic failures. It also leaves out what Harms calls the hard part, non-manipulation, along with every facet that needs a judge, tools or a long horizon (docs/FACETS.md, "Not measured here"). A model that passes every mode has shown the simple, stated core of corrigibility on mundane errands, and nothing more.
