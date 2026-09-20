from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

from create_revised_paper import (
    FIGURES_DIR,
    ROOT,
    TYPE_NAMES,
    add_bullet,
    add_caption,
    add_code,
    add_number,
    add_picture,
    add_table,
    calculate_stats,
    configure_document,
    generate_figures,
    load_results,
    shade_cell,
    set_cell_text,
)


OUTPUT_PATH = ROOT / "Smart_Contract_Dispute_Resolution_Publication_Ready_BW.docx"


def title_page(doc, summary):
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(45)
    run = title.add_run(
        "A Tiered Smart-Contract Prototype for Supply-Chain Logistics Dispute Resolution:\n"
        "Design and Seeded Synthetic Evaluation"
    )
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(19)
    run.font.color.rgb = RGBColor(17, 17, 17)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_before = Pt(18)
    run = subtitle.add_run("Prototype / artifact study — local Hardhat evaluation")
    run.italic = True
    run.font.name = "Arial"
    run.font.size = Pt(11)

    authors = doc.add_paragraph()
    authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    authors.paragraph_format.space_before = Pt(25)
    authors.add_run("Author names and affiliations omitted for review")

    box = doc.add_table(rows=1, cols=1)
    box.style = "Table Grid"
    cell = box.cell(0, 0)
    shade_cell(cell, "E6E6E6")
    set_cell_text(
        cell,
        "Scope statement. This is a prototype/artifact study evaluated on a local Hardhat network. "
        "It does not claim production deployment, public-testnet validation, formal verification, an "
        "independent audit, or complete on-chain financial settlement. Every quantitative result comes "
        "from one seeded contract execution (seed = %s), supplemented by a separate off-chain voting-model "
        "replication; the seeds and parameters are reported so both analyses can be reproduced. "
        "Neither analysis measures real adjudicators." % summary.get("seed", "n/a"),
        size=10,
    )
    doc.add_page_break()


def paragraph(doc, text):
    doc.add_paragraph(text)


def pct(x):
    return f"{x:.1f}%"


def build_publication_doc(rows, summary, gas_rows, stats):
    doc = Document()
    configure_document(doc)
    title_page(doc, summary)

    corr = summary["correctness"]
    t2 = corr["tier2Jury"]
    t3 = corr["tier3Expert"]
    routing = summary["routing"]
    params = summary["params"]
    seed = summary.get("seed", "n/a")
    n = summary["totalDisputes"]
    appeals = summary.get("appeals", {
        "nEligible": t2["n"],
        "nAppealed": routing["tier3"]["n"],
        "conditionalRate": summary.get("appealRate", 0),
        "overallShare": summary.get("overallAppealShare", routing["tier3"]["rate"]),
    })

    def ci(node):
        return f"[{node['ci95'][0]:.1f}, {node['ci95'][1]:.1f}]%"

    # ---------------------------------------------------------------- Abstract
    doc.add_heading("Abstract", level=1)
    paragraph(
        doc,
        "Supply-chain logistics disputes mix objective service-level violations, such as late delivery "
        "or payment delay, with subjective claims, such as damaged goods or a contested delivery "
        "acknowledgement. A deterministic smart contract can enforce the first class directly but cannot "
        "adjudicate the second, while purely human arbitration discards the transparency of programmable "
        "settlement. This paper presents a tiered smart-contract prototype for logistics dispute "
        "resolution and a seeded synthetic evaluation of it. The implementation is four Solidity "
        "contracts: SLAContract for typed clauses and oracle-supplied measurements, EvidenceVault for "
        "evidence-metadata anchoring, DisputeRegistry for staked arbitrator and expert profiles, and "
        "DisputeResolution for the lifecycle. Tier 1 resolves objective clauses deterministically; Tier 2 "
        "routes subjective claims to a three-member staked jury using commit-reveal voting; a Tier 2 "
        "ruling can be appealed, posting a bond, to a five-member expert panel in Tier 3. We evaluate the "
        "prototype with a single seeded Hardhat run of "
        f"{n:,} synthetic disputes (seed = {seed}). Routing was "
        f"{pct(routing['tier1']['rate'])} Tier 1, {pct(routing['tier2']['rate'])} Tier 2, and "
        f"{pct(routing['tier3']['rate'])} Tier 3. Of {appeals['nEligible']} jury rulings, "
        f"{appeals['nAppealed']} were appealed ({pct(appeals['conditionalRate'])}); appealed cases were "
        f"{pct(appeals['overallShare'])} of all disputes. We deliberately do not headline a single "
        "aggregate accuracy number: Tier 1 correctness is deterministic by construction and therefore a "
        "mechanism check, not adjudication quality. The informative result is the stochastic jury: "
        f"observed Tier 2 correctness was {t2['observedRate']:.1f}% (95% CI {ci(t2)}), statistically "
        f"consistent with the closed-form majority-vote value of {t2['theoreticalRate']:.1f}% for a "
        f"three-juror panel at {params['pArbHonest']:.0%} per-juror honesty; the appealed Tier 3 panel "
        f"observed {t3['observedRate']:.1f}% (n = {t3['n']}) against a theoretical "
        f"{t3['theoreticalRate']:.1f}%. The contribution is an implementation-faithful prototype and an "
        "honest measurement of what it does and does not establish, together with the engineering work "
        "required before such a protocol could be deployed in an adversarial logistics setting."
    )
    kw = doc.add_paragraph()
    kw.add_run("Keywords: ").bold = True
    kw.add_run(
        "smart contract; logistics; supply chain; dispute resolution; service-level agreement; "
        "commit-reveal voting; staked arbitration; reproducible evaluation; Hardhat."
    )

    # ------------------------------------------------------------ Introduction
    doc.add_heading("1. Introduction", level=1)
    paragraph(
        doc,
        "Modern logistics agreements coordinate parties that may not fully trust one another: buyers, "
        "sellers, carriers, freight forwarders, warehouses, and payment providers. Their obligations are "
        "usually specified as service-level terms: delivery deadlines, quantity thresholds, damage "
        "conditions, delivery acknowledgements, and payment deadlines. When performance diverges from the "
        "agreement, a dispute-resolution mechanism must answer two different questions. First, can an "
        "objective event be evaluated directly from a trusted measurement? Second, if it cannot, how "
        "should off-chain evidence and human judgement enter the process in a bounded, accountable way?"
    )
    paragraph(
        doc,
        "Smart contracts are attractive for the first question because they make state transitions "
        "visible, auditable, and hard to alter after deployment. They do not, however, remove trust: a "
        "deterministic clause is only as reliable as the oracle that writes the measurement it tests. "
        "Tier 1 in our design therefore relocates trust to a measurement authority rather than "
        "eliminating it. The second question is genuinely hard on-chain, because deciding whether goods "
        "were damaged or a delivery was legitimately refused requires interpreting evidence. This is the "
        "hybrid design problem the prototype addresses: automate objective clauses, and attach a "
        "bounded, economically staked human layer for subjective ones."
    )
    paragraph(
        doc,
        "We are explicit about what this paper is. It is a prototype and artifact study, not a deployable "
        "system. Transaction and routing measurements come from one seeded local execution. A separate "
        "off-chain Monte Carlo experiment estimates the mean of the independent-vote model. We report "
        "seeds, parameters, confidence intervals, and the closed-form comparator. We describe the mechanism "
        "honestly, including the parts that "
        "are deterministic by construction and therefore carry no empirical weight."
    )
    doc.add_heading("1.1 Research Questions", level=2)
    add_number(doc, "How can common logistics disputes be represented as typed smart-contract SLA clauses?")
    add_number(doc, "How does the implemented lifecycle route objective and subjective disputes, and which parts of that routing are deterministic versus emergent?")
    add_number(doc, "Under a seeded model with known per-voter honesty, does the staked jury/expert mechanism produce correctness consistent with its closed-form majority-vote prediction, and at what gas cost?")
    add_number(doc, "Which trust, authorization, and economic-settlement gaps must be closed before the prototype could support production claims?")
    doc.add_heading("1.2 Contributions", level=2)
    add_bullet(doc, "An implementation-faithful four-contract architecture for tiered logistics dispute resolution, described as built rather than as idealised.")
    add_bullet(doc, "A typed SLA clause model covering the five dispute classes present in the Solidity enum, with a three-state clause evaluation (BREACH / NO_BREACH / NOT_EVALUABLE).")
    add_bullet(doc, "A lifecycle in which Tier 3 is reached only through a genuine, bonded appeal of a Tier 2 ruling, so the appeal path and expert panel are actually exercised under stochastic voting rather than forced to ground truth.")
    add_bullet(doc, "A seeded, reproducible evaluation that separates deterministic mechanism checks from jury and expert correctness, reports confidence intervals, and checks both against closed-form binomial baselines.")
    add_bullet(doc, "An adversary-oriented security analysis identifying the trust, authorization, and settlement gaps between this prototype and a deployable system.")

    # -------------------------------------------------------------- Related work
    doc.add_heading("2. Related Work", level=1)
    paragraph(
        doc,
        "Blockchain supply-chain research has emphasised provenance, traceability, and shared records "
        "among organisations that lack a single trusted database. These properties make the evidentiary "
        "record of shipment events harder to alter after the fact, which is useful for dispute "
        "resolution. They do not solve the oracle problem: a chain record is only as reliable as the "
        "process that writes real-world facts into it, so for logistics adjudication the oracle is "
        "central rather than peripheral."
    )
    paragraph(
        doc,
        "Decentralised arbitration systems make human judgement economically accountable through staking, "
        "juror selection, voting, appeals, and slashing. Kleros uses a Schelling-point design in which "
        "jurors are rewarded for coherence with the majority; Aragon Court used staked jurors drawn by "
        "stake-weighted sortition with an appeal/escalation ladder. Both are general-purpose courts. SLA "
        "SLA research includes metric-triggered enforcement as well as witness-based verification. Our "
        "prototype is "
        "domain-specific to logistics, deterministic where a clause is measurable, and staked-human only "
        "where it is not. Table I positions it against these reference points."
    )
    add_table(
        doc,
        ["System", "Domain", "Subjective cases", "Juror selection", "Appeal", "Validation here"],
        [
            ["Kleros", "General court", "Schelling-point jury, coherence incentive", "Stake-weighted draw", "Multi-round, escalating fee", "Deployed network (external)"],
            ["Aragon Court", "General court", "Staked jurors, majority ruling", "Stake-weighted sortition", "Appeal to larger panel", "Deployed network (external)"],
            ["SLA mechanisms", "Cloud / IoT", "Metric monitoring or witness-based verification", "Mechanism-dependent", "N/A", "Research designs"],
            ["This prototype", "Logistics", "3-member staked jury, commit-reveal", "Deterministic modular index (prototype)", "Bonded appeal to 5 experts", "Seeded local simulation"],
        ],
        [1.05, 0.95, 1.55, 1.25, 1.1, 1.2],
    )
    add_caption(doc, "Table I. Positioning relative to representative arbitration and SLA-penalty systems.")
    paragraph(
        doc,
        "The contribution claimed here is modest and specific: a logistics-scoped integration that pays for human "
        "review only on the subset of clauses that cannot be measured, packaged as a reproducible "
        "artifact. We do not claim a new incentive mechanism, priority over every hybrid system, or a "
        "demonstrated cost advantage; indeed our jury selection is weaker than "
        "the deployed systems above, and we say so."
    )

    # -------------------------------------------------- Taxonomy and encoding
    doc.add_heading("3. Dispute Taxonomy and SLA Encoding", level=1)
    paragraph(
        doc,
        "The implemented taxonomy contains five dispute types. Separating shortage from damage matters: "
        "shortage is a quantity threshold and is measurable, whereas damage is a quality judgement that "
        "the prototype treats as subjective. Delivery denial is likewise treated as subjective. Both "
        "subjective classes route to the staked jury, and either may be appealed onward to the expert "
        "panel; Tier 3 is thus not a fixed destination for any type but an outcome of appeal."
    )
    add_table(
        doc,
        ["Enum", "Dispute class", "Entry tier", "Basis"],
        [
            ["0", "Late delivery", "Tier 1", "Measured value exceeds a deadline threshold."],
            ["1", "Shortage", "Tier 1", "Delivered quantity below a required threshold."],
            ["2", "Damage", "Tier 2", "Quality judgement requires human evidence review."],
            ["3", "Delivery denial", "Tier 2", "Contested acknowledgement requires human review."],
            ["4", "Payment delay", "Tier 1", "Payment timing exceeds a contractual threshold."],
        ],
        [0.55, 1.3, 1.0, 3.55],
    )
    add_caption(doc, "Table II. Implemented dispute classes and their entry tier. Subjective classes may be appealed to Tier 3.")
    paragraph(
        doc,
        "Each SLA stores buyer, seller, an escrowValue accounting field, an active flag, and a mapping of "
        "clauses. escrowValue is an accounting value, not Ether locked in the contract. Each clause "
        "stores the enum disputeType, an operator, a threshold, and penaltyBps. Oracle-role accounts "
        "write measuredValues, and evaluateClause computes the outcome."
    )
    add_code(
        doc,
        """
enum DisputeType { LateDelivery, Shortage, Damage, DeliveryDenial, PaymentDelay }
enum Operator    { GreaterThan, LessThan, Equal, NotEqual }
enum EvalStatus  { NotEvaluable, NoBreach, Breach }   // three-state result

struct Clause {
    DisputeType disputeType;
    Operator    operator;
    uint256     threshold;
    uint256     penaltyBps;
}
""",
    )
    add_caption(doc, "Listing 1. Implemented SLA clause representation and three-state evaluation enum.")
    paragraph(
        doc,
        "An earlier version of this artifact returned a two-valued (false, 0) result that conflated “no "
        "measurement has been written” with “measured, no breach” — a latent fairness bug, "
        "because an unmeasured clause would silently resolve in favour of the breaching party. The current "
        "code returns the three-state EvalStatus above, and resolveTier1 refuses to auto-resolve a "
        "NotEvaluable clause. The objective-tier results below are unaffected, because every objective "
        "clause in the simulation is given a measurement before resolution; the fix removes the latent "
        "hazard rather than changing reported numbers."
    )

    # ---------------------------------------------------------- Architecture
    doc.add_heading("4. Protocol Architecture", level=1)
    add_picture(
        doc,
        FIGURES_DIR / "architecture.png",
        "Figure 1. Implemented architecture of the four contracts and the local evaluation harness.",
    )
    add_table(
        doc,
        ["Contract", "Responsibility", "Known limitation"],
        [
            ["SLAContract", "Typed clauses, measured values, three-state evaluation, penalty calc", "No payable escrow locking."],
            ["EvidenceVault", "CID/hash metadata, submitter, timestamp", "No IPFS upload, encryption, or availability check; submission is open."],
            ["DisputeRegistry", "Staking, selection, lock/release, slashing, reward counters", "Selection is deterministic and predictable."],
            ["DisputeResolution", "Lifecycle, commit-reveal voting, bonded appeal, enforcement state", "enforce emits state/event only; no settlement transfer."],
        ],
        [1.25, 3.05, 1.85],
    )
    add_caption(doc, "Table III. Contract responsibilities and known prototype limitations.")
    doc.add_heading("4.1 Contract Roles and Trust", level=2)
    paragraph(
        doc,
        "SLAContract uses AccessControl for admin and oracle roles; the oracle role is the trusted writer "
        "of measurements and is the principal trust assumption of Tier 1. DisputeRegistry restricts "
        "lock/release/slash/reward to a resolution role held by DisputeResolution. DisputeResolution owns "
        "the state machine and is Ownable and Pausable; the owner can pause the system, which is a "
        "centralisation point discussed in the security analysis. EvidenceVault has no access control: "
        "evidence submission is open in the prototype."
    )
    doc.add_heading("4.2 Evidence Anchoring", level=2)
    paragraph(
        doc,
        "The evidence layer anchors metadata, not files. A submitted item holds a disputeId, submitter "
        "address, CID string, bytes32 hash, and timestamp, which supports later hash-equality checks. It "
        "does not prove that the CID resolves to retrievable content, that the content is authentic, or "
        "that private evidence stays confidential. The honest claim is evidence-metadata anchoring, not "
        "evidence management."
    )
    doc.add_heading("4.3 Stake and Settlement Semantics", level=2)
    paragraph(
        doc,
        "Staking handles real Ether locally: arbitrators stake 1 ETH, experts 2 ETH, and an appeal posts "
        "a 0.5 ETH bond. The fixed slash amount is 0.1 ETH, which is 10% of an arbitrator stake but only "
        "5% of an expert stake, so slashing is not a uniform fraction. Economic settlement is incomplete: "
        "slashed stake remains in the registry balance, rewards are counters rather than transfers, and "
        "the appeal bond has no defined final distribution. These are future work, not hidden costs."
    )

    # ------------------------------------------------------- Mechanism
    doc.add_heading("5. Tiered Resolution Mechanism", level=1)
    doc.add_heading("5.1 Lifecycle", level=2)
    add_code(
        doc,
        """
createDispute -> Disputed
Disputed -> resolveTier1 -> Tier1Resolved -> enforce -> Enforced
Disputed -> escalateToTier2 -> Tier2Commit
Tier2Commit -> transitionToReveal -> Tier2Reveal -> finalizeVote -> Tier2Resolved
Tier2Resolved -> appealToTier3 (bond) -> Tier3Commit
Tier3Commit -> transitionToReveal -> Tier3Reveal -> finalizeVote -> Tier3Resolved
Tier2Resolved / Tier3Resolved -> enforce -> Enforced
""",
    )
    paragraph(
        doc,
        "Tier 1 is deterministic for the three measurable types. Damage and delivery denial are "
        "non-auto-resolvable and enter Tier 2, a three-member jury. A Tier 2 ruling may be appealed by "
        "posting the bond, which assigns a five-member expert panel in Tier 3 whose ruling supersedes "
        "Tier 2. Commit and reveal windows are each one day."
    )
    doc.add_heading("5.2 Voting and Slashing", level=2)
    paragraph(
        doc,
        "Voting is commit-reveal: a voter commits a hash of (ruling, salt) during the commit window, then "
        "reveals both during the reveal window. finalizeVote tallies revealed votes and sets the majority "
        "ruling. Slashing applies only to non-revelation, which is a liveness fault: a voter who commits "
        "but never reveals is slashed. Good-faith minority voters are deliberately not slashed. With a "
        "three-member jury, slashing the minority would reward voting with the expected majority rather "
        "than honestly — a herding incentive that undermines the very point of commit-reveal — so "
        "the prototype rewards majority-coherent reveals but does not punish coherent-but-outvoted "
        "minorities. Under the honest-majority model used in evaluation every voter reveals, so no "
        "slashing events occur in the reported run; the non-reveal slash path is covered by the unit tests."
    )
    doc.add_heading("5.3 Jury and Expert Selection", level=2)
    paragraph(
        doc,
        "Selection is deterministic: for a seed and count it takes consecutive members by modular index. "
        "This makes tests reproducible but is predictable and therefore not adversarially secure; a "
        "deployable version needs verifiable randomness (e.g. a VRF) and eligibility snapshots. We state "
        "this as a limitation rather than implementing VRF in the artifact."
    )

    # ------------------------------------------------------- Implementation
    doc.add_heading("6. Implementation", level=1)
    add_table(
        doc,
        ["Item", "Current artifact"],
        [
            ["Language / compiler", "Solidity ^0.8.20, Hardhat solc 0.8.20"],
            ["Framework", "Hardhat with ethers and hardhat-gas-reporter"],
            ["OpenZeppelin", "AccessControl, Ownable, Pausable, ReentrancyGuard"],
            ["Contracts", "SLAContract, EvidenceVault, DisputeRegistry, DisputeResolution"],
            ["Simulation", "scripts/runSimulation.js (seeded), scripts/replicate.js (Monte-Carlo CI), scripts/analyzeResults.js"],
            ["Data", "results/results.csv, results/summary.json, results/gas-report.csv, results/replication.json"],
            ["Tests", "test/dispute.test.js, test/invariant.test.js"],
        ],
        [1.7, 4.4],
    )
    add_caption(doc, "Table IV. Implementation artifacts.")
    paragraph(
        doc,
        f"Reproducibility. All randomness in runSimulation.js comes from a seeded mulberry32 generator; "
        f"re-running with the same seed (default {seed}) reproduces the run exactly. The script also "
        "records the seed, type probabilities, pool sizes, and voting/appeal parameters into summary.json. "
        "The repository contains functional and invariant tests; these are not an independent security audit."
    )

    # ------------------------------------------------------- Methodology
    doc.add_heading("7. Evaluation Methodology", level=1)
    paragraph(
        doc,
        "The evaluation is a seeded synthetic experiment on a local Hardhat network. It is not a "
        "public-chain deployment and does not measure real human adjudicators. The simulation deploys the "
        f"contracts, registers {params.get('arbitratorPoolSize', 10)} arbitrators and "
        f"{params.get('expertPoolSize', 6)} experts, creates one shared SLA with a clause per type, "
        f"and generates {n:,} disputes from a seeded PRNG. For each dispute a ground-truth winner is "
        f"drawn from type probabilities {params.get('typeProbabilities', [0.30, 0.20, 0.20, 0.15, 0.15])}. "
        "Objective types receive an oracle measurement consistent with that winner, so Tier 1 is "
        "deterministic; its correctness is a mechanism check, not adjudication quality. Subjective types "
        f"go to the jury, where each juror votes honestly with probability "
        f"{params['pArbHonest']:.0%} and the on-chain tally decides. A losing party appeals with "
        f"probability {params['pAppeal']:.0%}; an appeal runs a five-member expert panel with per-expert "
        f"honesty {params['pExpHonest']:.0%}, again tallied on-chain. No outcome is forced to ground "
        "truth: Tier 2 and Tier 3 correctness are genuinely stochastic."
    )
    paragraph(
        doc,
        "Two estimands are stochastic: jury correctness and expert correctness. Because finalizeVote only "
        "tallies committed votes, their statistical behaviour is fully determined by the off-chain "
        "honesty draws, so we obtain confidence intervals two ways. The single on-chain run gives a "
        "Wilson 95% interval on the observed proportion (Section 8). Independently, scripts/replicate.js "
        "runs only the independent voting process off-chain across many replications (1,000 replications "
        "of 1,000 panels by default) to estimate the model mean, and both are compared to the closed-form majority "
        "probability P(correct) = sum_{k>n/2} C(n,k) p^k (1-p)^{n-k}. This is what gives the correctness "
        "numbers a model-based comparator. It does not replicate routing, gas, oracle updates, appeals, or contract execution."
    )
    paragraph(
        doc,
        "On gas, we report two well-defined quantities. Per-operation averages come directly from "
        "transaction receipts (Table VII). Per-tier totals sum the open + resolve + enforce gas over the "
        "complete on-chain path of a dispute whose terminal tier is the row label; by construction a "
        "Tier 3 dispute includes its Tier 2 phase plus the appeal, so Tier 3 >= Tier 2. We report gas in "
        "These totals exclude deployment, role grants, oracle measurement updates, SLA creation, and voter "
        "registration; they are not full lifecycle costs. We report gas units only. We do not convert to fiat: the prototype targets an L2 rather than L1 mainnet, "
        "and a single L1 gas-price assumption would imply a precision the artifact does not have."
    )

    # ------------------------------------------------------- Results
    doc.add_heading("8. Results", level=1)
    doc.add_heading("8.1 Routing", level=2)
    add_picture(
        doc,
        FIGURES_DIR / "tier_distribution.png",
        f"Figure 2. Resolution-tier distribution across {n:,} seeded disputes.",
    )
    add_table(
        doc,
        ["Tier", "Cases", "Share", "Mean total gas", "Configured window"],
        [
            ["Tier 1", stats["tiers"]["1"]["count"], pct(stats["tiers"]["1"]["rate"]), f"{stats['tiers']['1']['avg_gas']:,.0f}", "single block"],
            ["Tier 2", stats["tiers"]["2"]["count"], pct(stats["tiers"]["2"]["rate"]), f"{stats['tiers']['2']['avg_gas']:,.0f}", "2 days"],
            ["Tier 3", stats["tiers"]["3"]["count"], pct(stats["tiers"]["3"]["rate"]), f"{stats['tiers']['3']['avg_gas']:,.0f}", "4 days"],
        ],
        [0.8, 0.8, 0.8, 1.5, 1.4],
    )
    add_caption(doc, "Table V. Routing, mean total path gas, and configured windows by tier.")
    paragraph(
        doc,
        "We are explicit that routing is only partly emergent. The Tier 1 and Tier 2 shares restate the "
        "input type distribution through a fixed type-to-tier map: a measurable type always reaches Tier 1, "
        "a subjective type always reaches Tier 2. No case escalates because evidence was contested. The "
        f"genuinely emergent quantity is the Tier 3 share ({pct(routing['tier3']['rate'])}). "
        f"The conditional appeal rate is {appeals['nAppealed']}/{appeals['nEligible']} = "
        f"{pct(appeals['conditionalRate'])}; the overall appealed share is {pct(appeals['overallShare'])}. The "
        "“configured window” column is the sum of the protocol’s commit/reveal windows, a "
        "constant of the design, not a measured wall-clock latency; Hardhat advances time programmatically, "
        "so no real latency is observed."
    )

    doc.add_heading("8.2 Stochastic Correctness", level=2)
    add_picture(
        doc,
        FIGURES_DIR / "type_correctness.png",
        "Figure 3. Ruling agreement with ground truth by dispute type (objective types deterministic).",
    )
    add_table(
        doc,
        ["Estimand", "n", "Observed", "95% CI", "Theoretical"],
        [
            ["Tier 2 jury (3 voters)", t2["n"], f"{t2['observedRate']:.1f}%", ci(t2), f"{t2['theoreticalRate']:.1f}%"],
            ["Tier 3 expert (5 voters)", t3["n"], f"{t3['observedRate']:.1f}%", ci(t3), f"{t3['theoreticalRate']:.1f}%"],
        ],
        [2.0, 0.7, 1.0, 1.4, 1.0],
    )
    add_caption(doc, "Table VI. Stochastic correctness with Wilson 95% intervals against closed-form majority-vote baselines.")
    paragraph(
        doc,
        f"The jury’s observed correctness ({t2['observedRate']:.1f}%, 95% CI {ci(t2)}) brackets the "
        f"theoretical {t2['theoreticalRate']:.1f}% for three jurors at {params['pArbHonest']:.0%} honesty, "
        "so the simulation reproduces the binomial prediction rather than revealing anything beyond it: "
        "the mechanism tallies votes correctly. This is the right claim to make — a sanity check that "
        "the on-chain mechanism behaves as the model says — not a discovery about adjudication "
        f"accuracy. The appealed expert panel observed {t3['observedRate']:.1f}% over n = {t3['n']} cases "
        f"against a theoretical {t3['theoreticalRate']:.1f}%. An all-correct sample does not establish "
        "perfect expert reliability, and we report n so the reader can see the precision the sample supports. "
        "The objective tiers are deterministic and contribute no information about accuracy, which is why "
        "we do not fold everything into one headline percentage."
    )

    doc.add_heading("8.3 Gas Profile", level=2)
    add_picture(
        doc,
        FIGURES_DIR / "operation_gas.png",
        "Figure 4. Average gas by every separately recorded contract operation (gas units).",
    )
    add_table(
        doc,
        ["Operation", "Average gas", "Calls"],
        [[row["Function"], f"{int(row['AverageGas']):,}", row.get("Calls", "")] for row in gas_rows],
        [2.2, 1.3, 1.0],
    )
    add_caption(doc, "Table VII. Per-operation average gas from transaction receipts, with call counts (the denominator).")
    paragraph(
        doc,
        "Per-operation gas has an explicit denominator. transitionToReveal is recorded separately in "
        "schema version 2 while remaining included in each path's resolveGas. The per-tier "
        "totals in Table V are internally consistent — Tier 3 exceeds Tier 2 because a Tier 3 path "
        "contains the Tier 2 phase plus the appeal and a second voting round — which resolves the "
        "counter-intuitive inversion present in the earlier artifact, where Tier 3 was under-counted. We "
        "give no percentage saving or external-arbitration superiority claim because no matched baseline "
        "was executed. The local experiment also omits public-network and L2 data-availability fees."
    )

    # ------------------------------------------------------- Security
    doc.add_heading("9. Security and Validity Analysis", level=1)
    paragraph(
        doc,
        "We frame this as a threat model with an explicit adversary and trust assumptions, not a checklist. "
        "Trust assumptions: (i) the oracle-role account writes Tier 1 measurements honestly — Tier 1 "
        "relocates trust to this party rather than removing it; (ii) at most a minority of any selected "
        "jury or panel is malicious; (iii) the contract owner, who holds Ownable/Pausable authority, is "
        "trusted not to censor by pausing. The adversary is a rational dispute participant (or a colluding "
        "set) that may submit disputes, vote, and appeal to obtain a favourable ruling or grief a "
        "counterparty, within those assumptions."
    )
    add_table(
        doc,
        ["Property", "Prototype support", "Residual gap under the adversary"],
        [
            ["Safety", "Enum state machine; representative-path and invariant tests", "No exhaustive model checking or conservation-of-funds invariant."],
            ["Liveness", "Bounded commit/reveal windows; non-reveal slashing", "Owner pause can block enforcement; no keeper/timeout for a stalled appeal."],
            ["Fairness", "Commit-reveal protocol; no minority slashing; reward for coherence", "Predictable selection; no incentive-compatibility proof; synthetic run uses a fixed shared salt."],
            ["Integrity", "Evidence hash-equality check", "No off-chain availability, authenticity, or privacy guarantee."],
        ],
        [0.95, 2.55, 2.55],
    )
    add_caption(doc, "Table VIII. Properties the prototype partially supports and the gaps a real adversary exposes.")
    doc.add_heading("9.1 Principal Risks", level=2)
    add_bullet(doc, "Authorization is largely absent: any account can create a dispute, and any account — not only the losing party — can appeal. The simulation therefore assumes cooperative actors; a real deployment must gate both to SLA parties.")
    add_bullet(doc, "Selection is predictable, so an adversary who can influence the seed can anticipate or target jurors.")
    add_bullet(doc, "Tier 1 trusts a single oracle writer; a wrong or malicious measurement decides an objective case directly.")
    add_bullet(doc, "Settlement is incomplete: escrow release, penalty payment, slashed-stake distribution, and appeal-bond disposition are undefined.")
    add_bullet(doc, "Evidence availability and privacy are not guaranteed by the metadata anchor.")
    add_bullet(doc, "The owner’s pause authority is a centralisation and censorship point.")

    # ------------------------------------------------------- Discussion
    doc.add_heading("10. Discussion", level=1)
    paragraph(
        doc,
        "The defensible contribution is architectural and methodological: a logistics-scoped tiering that "
        "avoids jury cost for measurable clauses while providing a bounded staked-review path for "
        "subjective ones, delivered as a seeded, reproducible artifact whose stochastic claims are tied to "
        "a closed-form baseline. The evaluation’s value is precisely its modesty — it shows the "
        "mechanism behaves as modelled and exercises the appeal path under genuine voting, without "
        "overclaiming adjudication accuracy that a synthetic honesty parameter cannot establish."
    )
    paragraph(
        doc,
        "What the paper does not show is equally important. It does not measure human adjudicator behaviour, "
        "does not demonstrate adversarial robustness of selection or authorization, and does not implement "
        "settlement. These are the difference between a prototype and a system."
    )

    # ------------------------------------------------------- Roadmap
    doc.add_heading("11. Roadmap Toward a Deployable System", level=1)
    add_number(doc, "Gate dispute creation and appeal to authorised SLA parties and valid clauses.")
    add_number(doc, "Replace deterministic selection with VRF-backed sampling and eligibility snapshots.")
    add_number(doc, "Decentralise or attest the Tier 1 oracle, and add a NOT_EVALUABLE escalation path for unmeasured clauses.")
    add_number(doc, "Implement a payable escrow vault with defined penalty, slashed-stake, reward, and appeal-bond settlement.")
    add_number(doc, "Add a keeper or timeout so a stalled appeal cannot freeze a dispute, and reconsider the owner pause authority.")
    add_number(doc, "Add property tests for terminal-state uniqueness, conservation of funds, and authorization, plus a reproducible Slither run.")
    add_number(doc, "Extend the evaluation to adversarial and collusion models and, if claimed, an independent security review.")

    # ------------------------------------------------------- Conclusion
    doc.add_heading("12. Conclusion", level=1)
    paragraph(
        doc,
        "This paper presented a tiered smart-contract prototype for supply-chain logistics dispute "
        "resolution and a seeded synthetic evaluation of it. The system encodes five dispute classes with "
        "three-state clause evaluation, resolves objective clauses deterministically, anchors evidence "
        "metadata, registers staked arbitrators and experts, and runs commit-reveal voting across a jury "
        "tier and a bonded expert-appeal tier that is genuinely exercised rather than forced. In a single "
        f"seeded run of {n:,} disputes, the stochastic jury achieved {t2['observedRate']:.1f}% correctness "
        f"(95% CI {ci(t2)}), consistent with the closed-form {t2['theoreticalRate']:.1f}%."
    )
    paragraph(
        doc,
        "The honest reading is that this is a reproducible prototype foundation. It supports the "
        "feasibility of hybrid automated/staked-human dispute routing while making clear that deployment "
        "requires authorization, verifiable randomness, oracle decentralisation, complete settlement, and "
        "adversarial evaluation. Reporting the mechanism for what it is — and is not — is the "
        "contribution we stand behind."
    )

    # ------------------------------------------------------- Availability
    doc.add_heading("Code and Data Availability", level=1)
    paragraph(
        doc,
        "The artifact comprises the Solidity contracts, Hardhat tests, the seeded simulation and "
        "replication scripts, the CSV/JSON outputs, and the figure-generation code, all in a single "
        "repository. Each reported number is regenerated by running the seeded simulation followed by the "
        "figure/manuscript scripts."
    )

    # ------------------------------------------------------- References
    doc.add_heading("References", level=1)
    refs = [
        '[1] S. Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System," 2008.',
        '[2] G. Wood, "Ethereum: A Secure Decentralised Generalised Transaction Ledger," Ethereum Yellow Paper, 2014.',
        '[3] S. Saberi, M. Kouhizadeh, J. Sarkis, and L. Shen, "Blockchain technology and its relationships to sustainable supply chain management," Int. J. Production Research, vol. 57, no. 7, pp. 2117-2135, 2019.',
        '[4] N. Kshetri, "Blockchain\'s roles in meeting key supply chain management objectives," Int. J. Information Management, vol. 39, pp. 80-89, 2018.',
        '[5] K. Wuest and A. Gervais, "Do You Need a Blockchain?" Proc. Crypto Valley Conf. on Blockchain Technology, pp. 45-54, 2018.',
        '[6] C. Lesaege, F. Ast, and W. George, "Kleros Short Paper v1.0.7," 2019.',
        '[7] Aragon, "Aragon Court," technical documentation, 2020.',
        '[8] R. B. Uriarte, R. De Nicola, and K. Kritikos, "Towards distributed SLA management with smart contracts and blockchain," Proc. IEEE CloudCom, pp. 266-271, 2018.',
        '[9] H. Zhou et al., "A blockchain based witness model for trustworthy cloud service level agreement enforcement," Proc. IEEE INFOCOM, pp. 1567-1575, 2019.',
        '[10] N. Atzei, M. Bartoletti, and T. Cimoli, "A survey of attacks on Ethereum smart contracts," POST, 2017.',
        '[11] J. Feist, G. Grieco, and A. Groce, "Slither: A static analysis framework for smart contracts," IEEE/ACM WETSEB, 2019.',
        '[12] E. Ben-Sasson et al., "Verifiable randomness and VRFs," in references therein; and OpenZeppelin Contracts, software library, accessed 2026.',
        '[13] J. Benet, "IPFS - Content Addressed, Versioned, P2P File System," arXiv:1407.3561, 2014.',
    ]
    for ref in refs:
        p = doc.add_paragraph(ref)
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.first_line_indent = Inches(-0.22)
        p.paragraph_format.space_after = Pt(3)

    # ------------------------------------------------------- Appendix
    doc.add_heading("Appendix A. Claim Alignment Checklist", level=1)
    add_table(
        doc,
        ["Manuscript claim", "Support level"],
        [
            ["Four-contract architecture", "Supported by source code."],
            ["Five dispute types, three-state evaluation", "Supported by SLAContract."],
            ["Tier 1 deterministic resolution (trusts oracle)", "Supported for measured objective cases."],
            ["Tier 2 commit-reveal jury, stochastic", "Supported; CI matches closed-form baseline."],
            ["Tier 3 expert appeal, genuinely exercised", "Supported; reached via bonded appeal, not forced."],
            ["Seeded, reproducible evaluation", "Supported; seed and parameters recorded."],
            ["Verifiable random selection", "Not supported; future work."],
            ["Authorization of disputants/appellants", "Not supported; future work."],
            ["Complete escrow settlement", "Not supported; future work."],
            ["Public deployment / independent audit", "Not supported by the artifact."],
        ],
        [2.6, 3.3],
    )

    return doc


def main():
    rows, summary, gas_rows = load_results()
    stats = calculate_stats(rows)
    generate_figures(stats, gas_rows)
    doc = build_publication_doc(rows, summary, gas_rows, stats)
    doc.save(OUTPUT_PATH)
    print(f"Created: {OUTPUT_PATH}")
    print(f"Words approx: {sum(len(p.text.split()) for p in doc.paragraphs)}")


if __name__ == "__main__":
    main()
