Semantic Diffraction in Conceptual Graphs -» A Structural Approach to Equilibrium and Synthesis Detection

Semantic graph auditor based on Personalized PageRank (PPR) for IA_m and general semantic graphs.

This repository implements a structural auditing framework for semantic graphs.
Given a pair of conceptual poles, the auditor determines whether an apparent equilibrium or synthesis is structurally coherent, stable, and axis-consistent, or merely an artifact of semantic proximity (e.g. embeddings or global popularity).
The system is designed as a quality-control and diagnostic layer for IA_m, but can be applied to any directed semantic graph enriched with axis / role metadata.

🧩 The Problem It Solves
Large semantic graphs (LLM-generated, hybrid symbolic–embedding systems, knowledge graphs, etc.) systematically suffer from:
- False equilibria: Nodes appear “central” because they are globally popular hubs, not because they structurally mediate two concepts.
- Semantic drift:  Meta-concepts (e.g. definition, synthesis, concept) dominate rankings and contaminate domain-specific reasoning.
- Missing structure: A relationship feels correct semantically, but the graph lacks explicit intermediate concepts or axes.
- No stability criteria: Most systems rank nodes, but do not answer the key question:
  Is this equilibrium robust, or accidental?

IA_m Diffraction Auditor addresses these problems explicitly.

🧠 Core Idea
The auditor treats a pair of concepts as interfering sources in a semantic field.

Instead of asking:
“What is close to A and B?”

it asks:
“What node structurally balances A and B under controlled propagation and axis constraints?”

This is achieved through:
- Personalized PageRank (PPR) propagation
- Axis / role-based filtering (conceptual dimensions)
- Balance and dominance metrics
- A second-pass refinement guided by the candidate equilibrium itself

⚙️ Formal Core: Semantic Diffraction Score
Given a directed graph 𝐺 = (𝑉,𝐸)  and two conceptual poles A and B:
1. Compute two independent Personalized PageRank fields:
    𝑃𝐴(𝑛) : PPR centered on A
    𝑃𝐵(𝑛) : PPR centered on B

Define the semantic diffraction score:
S(n)=(PA(n)+PB(n))−λ⋅∣PA(n)−PB(n)∣

Where:
- 𝑃𝐴,𝑃𝐵 represent structural intensity from each pole
- The sum favors shared influence
- The absolute difference penalizes asymmetry
- λ≥0 controls stability strictness

Nodes maximizing 
S(n) under structural constraints are equilibrium candidates.
This formulation favors true mediators, not global hubs.


⚙️ How It Works
1️⃣ Controlled Propagation
The graph is rebuilt in one of three modes:
- structure — only explicit structural edges
- mixed — structure + capped embeddings
- all — full graph (exploratory / diagnostic)
PPR is computed independently from pole A and pole B.

2️⃣ Interference Scoring (Equilibrium Detection)
Each candidate node is scored using the diffraction formula above:
score = (pa + pb) − λ · |pa − pb|
This directly penalizes imbalance and suppresses hub dominance.

3️⃣ Axis / Role Filtering
Candidates can be restricted to:
- axes shared by A and B
- a specific axis (--axis_only)
- no axis filtering at all (stress test)
This allows both strict geometric audits and controlled free exploration.

4️⃣ Stability Analysis
An equilibrium is considered stable only if:
- it dominates the runner-up (ratio test)
- it is sufficiently balanced between poles
This answers explicitly:
Is this equilibrium robust, or ambiguous?

5️⃣ Axis-Guided Refine Pass (v5)
If the top equilibrium is unstable, a second pass is triggered:
- Extract axes from the provisional equilibrium
- Re-run propagation constrained to those axes
This often recovers latent structure when poles do not initially share axes.

6️⃣ Drift Diagnostics
The auditor explicitly reports drift suspects:
- nodes with no shared axes with the poles
- non-structural or meta-concept attractors
Contamination is made visible, not silent.

7️⃣ Optional Synthesis Detection
Given:
- pole A
- pole B
- final equilibrium EQ
The auditor can search for a higher-order synthesis using triple-source PPR and balance constraints.
False syntheses (e.g. poles of dualities) can be rejected automatically.

✅ What This Tool Is Good For
- Auditing semantic graph health
- Detecting missing intermediate concepts
- Validating conceptual axes (e.g. time–space, hot–cold)
- Preventing meta-concept contamination
- Comparing structure vs embedding intuition
- Post-training QA for autonomous graph expansion systems

❌ What This Tool Is Not
- Not a general-purpose recommender
- Not a replacement for embeddings
- Not a learning algorithm
It is an auditor, not a generator.

🔬 Typical Use Cases
- Knowledge graph validation
- Research prototypes combining symbolic + neural representations
- Conceptual geometry / philosophy of AI experiments
- Structural sanity checks after long autonomous expansions

🔁 Reproducibility
This repository includes two curated datasets allowing direct verification under controlled conditions.

Demo Graph (minimal, canonical)
python3 audit.py --json red_fractal_demo.json --a "frío" --b "calor" --sintesis --modo estructura
Expected behavior:
- frío / calor → equilibrium tibio
- synthesis → temperatura

python3 audit.py --json red_fractal_demo.json --a "espacio" --b "tiempo" --modo estructura
Expected behavior:
- stable equilibrium → relatividad

Sample Graph (stress test, realistic structure)
python3 audit.py --json red_fractal_sample.json --a "frío" --b "calor" --sintesis --modo estructura
Expected behavior:
- stable equilibrium → tibio
- synthesis → temperatura
- axis-constrained behavior
- no meta-concept drift

python3 audit.py --json red_fractal_sample.json --a "espacio" --b "tiempo" --modo estructura
Expected behavior:
- stable equilibrium → relatividad
- Adversarial / Non-Auditable Cases

python3 audit.py --json red_fractal_sample.json --a "espacio" --b "calor" --refine --modo estructura
Expected result:
- A ∩ B = ∅
- Result marked UNCONSTRAINED
- Confidence: LOW

python3 audit.py --strict_axis --json red_fractal_sample.json --a "espacio" --b "calor"
Expected result:
- Execution aborts with NO AUDITABLE (exit code 2)

🧪 Notes on Reproducibility
- All examples use structure-only propagation (--modo estructura)
- Axis / role metadata is essential
- If A ∩ B is empty, results are reported as UNCONSTRAINED (LOW confidence)
- --strict_axis enforces formal auditability
The example datasets are currently in Spanish, as they originate from an evolving IA_m graph.
The method itself is language-agnostic.

🚫 Exclusion Policy (Important)
By default, only internal/meta nodes are excluded (e.g. ia_m, subconsciente).
Skeleton nodes (spatial directions, temporal primitives, centro focal) are not excluded by default, as they are valid equilibria in canonical axis tests.
To suppress them:
python3 audit.py --exclude_skeleton ...

📦 License
Apache License 2.0
Chosen to encourage open research, reproducibility, and safe industrial adoption while protecting authorship and patent rights.

📌 Terminology Mapping (Paper ↔ Code)
Paperconcept	                              Code
Semantic diffraction score	`               (pa + pb) − λ·
Equilibrium candidate	                      eq
Axis-guided refinement	                    --refine
Structural propagation	                    PPR (non-embedding edges)
Drift	                                      drift_suspects
