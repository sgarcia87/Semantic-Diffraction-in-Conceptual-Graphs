# Semantic-Diffraction-in-Conceptual-Graphs
A Structural Approach to Equilibrium and Synthesis Detection. Semantic graph auditor based on Personalized PageRank (PPR) for IA_m. Analyzes concept pairs to detect structural equilibria, stability (ratio/balance), drift, and emergent synthesis using axis-based role filtering, structure/mixed modes, and an axis-guided refine pass.


IA_m – Diffraction Auditor (v5)
IA_m Diffraction Auditor is a structural auditing tool for semantic graphs.
It analyzes pairs of concepts to determine whether their relationship is geometrically and structurally coherent, or merely the result of semantic proximity (embeddings).
The tool is designed as a quality-control and diagnostic layer for IA_m, but it can be applied to any directed semantic graph enriched with roles/axes metadata.

🧩 The Problem It Solves
Large semantic graphs (LLM-generated, hybrid symbolic–embedding systems, knowledge graphs, etc.) tend to suffer from the same issues:
False equilibria
Nodes appear “central” because they are globally popular, not because they structurally mediate two concepts.
Semantic drift
Meta-concepts (e.g. synthesis, thesis, definition) dominate rankings and contaminate domain-specific reasoning.
Missing structure
A relationship feels correct semantically, but the graph lacks explicit intermediate concepts or axes.
No stability criteria

Most systems rank nodes, but do not answer:
Is this equilibrium actually stable, or is it an accident?
IA_m Diffraction Auditor addresses these problems explicitly.

🧠 Core Idea
The auditor treats concept pairs as interfering sources in a semantic field.
Instead of asking “what is close to A and B?”, it asks:
What node structurally balances A and B under controlled propagation and axis constraints?
This is achieved through:
Personalized PageRank (PPR) propagation
Axis-based filtering (roles / conceptual dimensions)
Balance and dominance metrics
A second-pass refinement guided by the candidate equilibrium itself

⚙️ How It Works 
1. Controlled Propagation
The graph is rebuilt in one of three modes:
structure: only explicit structural edges
mixed: structure + capped embeddings
all: full graph (exploratory)
PPR is computed independently from pole A and pole B.

2. Interference Scoring (Equilibrium Detection)
Each candidate node is scored as:
score = (pa + pb) − λ · |pa − pb|
Where:
pa, pb are PPR probabilities from A and B
λ penalizes imbalance
This favors true mediators, not hubs.

3. Axis / Role Filtering
Candidates can be restricted to:
shared axes of A and B
a specific axis (--axis_only)
or no axes at all (stress test)
This allows strict geometric audits or free exploration.

4. Stability Analysis
An equilibrium is considered stable only if:
it dominates the runner-up (ratio test)
it is sufficiently balanced between poles
This answers:
Is this equilibrium robust, or ambiguous?


5. Refine Pass (v5)
If the equilibrium is unstable, a second pass is triggered:
Extract axes from the provisional equilibrium
Re-run the search constrained to those axes
This often recovers latent structure when poles do not initially share axes.

6. Drift Diagnostics
The auditor explicitly reports drift suspects:
nodes with no shared axes with poles
non-structural concepts acting as attractors
This makes contamination visible instead of silent.

7. Optional Synthesis Detection
Given:
pole A
pole B
final equilibrium EQ
The auditor can search for a higher-order synthesis using triple-source PPR and balance constraints.
False syntheses (e.g. poles of dualities) can be rejected automatically.

✅ What This Tool Is Good For
Auditing semantic graph health
Detecting missing intermediate concepts
Validating conceptual axes (e.g. time–space, hot–cold)
Preventing meta-concept contamination
Comparing structure vs embedding intuition
Post-training QA for autonomous graph expansion systems

❌ What This Tool Is Not
Not a general-purpose recommender
Not a replacement for embeddings
Not a learning algorithm
It is an auditor, not a generator.

🔬 Typical Use Cases
Knowledge graph validation
Research prototypes combining symbolic + neural representations
Conceptual geometry / philosophy of AI experiments
Structural sanity checks after long autonomous expansions


#############################################################################
Reproducibility
This repository includes two curated datasets that allow direct verification of the auditor’s behavior under controlled conditions.

Demo graph (minimal, canonical)
The demo graph is a compact, noise-free semantic graph designed to showcase the core capabilities of the auditor: equilibrium detection and synthesis emergence under strict structural constraints.
python3 test5.py --json data/red_fractal_demo.json --a "frío" --b "calor" --sintesis --modo estructura
python3 test5.py --json data/red_fractal_demo.json --a "espacio" --b "tiempo" --modo estructura
Expected behavior:
frío / calor → equilibrium tibio → synthesis temperatura
espacio / tiempo → stable equilibrium relatividad


Sample graph (stress-test, realistic structure)
The sample graph contains multiple interacting axes, mild structural noise, and non-trivial topology. It is intended to validate stability criteria, axis filtering, and robustness beyond the minimal demo.
python3 audit.py --json data/red_fractal_sample.json --a "espacio" --b "tiempo" --modo estructura
python3 audit.py --json data/red_fractal_sample.json --a "frío" --b "calor" --sintesis --modo estructura
Expected behavior:
Stable equilibrium relatividad for espacio / tiempo
Stable equilibrium tibio and synthesis temperatura for frío / calor
Axis-based filtering active
No meta-concept drift under structural mode

Notes on reproducibility
All results are obtained using structure-only propagation (no embeddings).
Axis/role metadata is essential for reproducibility.
Both datasets are automatically extracted from a larger IA_m graph using the same auditing logic provided in this repository.
The example datasets are currently in Spanish, as they originate from an evolving conceptual graph developed in that language. The auditing method itself is language-agnostic, and English datasets will be added in future iterations.
If A∩B is empty, results are reported as UNCONSTRAINED (LOW confidence). Use --strict_axis to enforce auditability.

Reproducibility EXAMPLES
This repository includes two curated datasets (demo and sample) that allow direct verification of the auditor’s behavior.
All commands below are copy–paste reproducible.
Demo graph (minimal, canonical)
python3 audit.py --json data/red_fractal_demo.json --a "frío" --b "calor" --sintesis --modo estructura
Expected result:
Equilibrium: tibio
Synthesis: temperatura
Stability: INDETERMINATE (single candidate, small graph)
python3 audit.py --json data/red_fractal_demo.json --a "espacio" --b "tiempo" --modo estructura
Expected result:
Equilibrium: relatividad
Stability: INDETERMINATE (single candidate, small graph)
Sample graph (stress test, realistic structure)
python3 audit.py --json data/red_fractal_sample.json \
  --a "frío" --b "calor" --sintesis --modo estructura
Expected result:
Equilibrium: tibio
Synthesis: temperatura
Axis-constrained, stable behavior
python3 audit.py --json data/red_fractal_sample.json --a "espacio" --b "tiempo" --modo estructura
Expected result:
Equilibrium: relatividad
Axis-constrained behavior
Adversarial case (no shared axes)
python3 audit.py --json data/red_fractal_sample.json --a "espacio" --b "calor" --refine --modo estructura
Expected result:
Axis scope empty (A ∩ B = ∅)
Result marked as UNCONSTRAINED
Confidence: LOW
Refine pass is automatically skipped (no auto-confirmation)
Strict audit mode (enforced auditability)
python3 audit.py --strict_axis --json data/red_fractal_sample.json --a "espacio" --b "calor" --modo estructura
Expected result:
Execution aborts with NO AUDITABLE (exit code 2)
python3 audit.py --strict_axis --refine --json data/red_fractal_sample.json --a "espacio" --b "calor" --modo estructura
Expected result:
Refine attempted
No valid axis scope recovered
Execution aborts with NO AUDITABLE (exit code 3)
Notes on reproducibility
All results above use structure-only propagation (--modo estructura).
When no shared axes exist, results are explicitly reported as UNCONSTRAINED with LOW confidence.
The --strict_axis flag enforces formal auditability and prevents unconstrained equilibria from being reported as valid.

📦 License
Apache License 2.0
Chosen to encourage open research, reproducibility, and safe industrial adoption while protecting authorship and patent rights.
