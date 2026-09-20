// Prints a human-readable summary of the latest simulation run.
// Reads results/summary.json (new schema) and results/results.csv.

const fs = require("fs");

function main() {
    if (!fs.existsSync("results/summary.json")) {
        console.error("Run `node scripts/runSimulation.js` first to generate results/summary.json.");
        return;
    }
    const s = JSON.parse(fs.readFileSync("results/summary.json", "utf-8"));

    console.log(`\n=== Run configuration ===`);
    console.log(`Seed: ${s.seed} | N=${s.totalDisputes} | p_arb=${s.params.pArbHonest} | p_exp=${s.params.pExpHonest} | p_appeal=${s.params.pAppeal}`);

    console.log(`\n=== 1. Routing ===`);
    console.log(`Tier 1 (deterministic): ${s.routing.tier1.n} (${s.routing.tier1.rate}%)`);
    console.log(`Tier 2 (jury):          ${s.routing.tier2.n} (${s.routing.tier2.rate}%)`);
    console.log(`Tier 3 (expert appeal): ${s.routing.tier3.n} (${s.routing.tier3.rate}%)`);
    const appeals = s.appeals || {
        nEligible: s.correctness.tier2Jury.n,
        nAppealed: s.routing.tier3.n,
        conditionalRate: s.appealRate,
        overallShare: s.overallAppealShare ?? s.routing.tier3.rate,
    };
    console.log(`Appeals:                ${appeals.nAppealed}/${appeals.nEligible} jury rulings (${appeals.conditionalRate}%)`);
    console.log(`Appealed share overall: ${appeals.overallShare}% of all disputes`);

    console.log(`\n=== 2. Correctness by dispute type ===`);
    for (const [name, c] of Object.entries(s.correctness.byType)) {
        console.log(`${name.padEnd(15)}: ${c.rate}%  (${c.correct}/${c.n}, 95% CI ${c.ci95[0]}-${c.ci95[1]}%)`);
    }
    const t2 = s.correctness.tier2Jury;
    const t3 = s.correctness.tier3Expert;
    console.log(`\nTier 2 jury:   observed ${t2.observedRate}% (95% CI ${t2.ci95[0]}-${t2.ci95[1]}%) vs theoretical ${t2.theoreticalRate}%`);
    console.log(`Tier 3 expert: observed ${t3.observedRate}% (n=${t3.n}) vs theoretical ${t3.theoreticalRate}%`);
    console.log(`Overall: ${s.correctness.overall.rate}% (note: Tier 1 deterministic, not adjudication accuracy)`);

    console.log(`\n=== 3. Gas by tier (total on-chain path, gas units) ===`);
    console.log(`Tier 1: ${s.gasByTier["1"].meanTotalGas} gas (n=${s.gasByTier["1"].n})`);
    console.log(`Tier 2: ${s.gasByTier["2"].meanTotalGas} gas (n=${s.gasByTier["2"].n})`);
    console.log(`Tier 3: ${s.gasByTier["3"].meanTotalGas} gas (n=${s.gasByTier["3"].n})`);
    if (s.gasAccounting) console.log(`Boundary: ${s.gasAccounting.note}`);

    console.log(`\n=== 4. Configured windows (NOT measured latency) ===`);
    console.log(`Tier 1: ${s.configuredWindows.tier1Minutes} min | Tier 2: ${s.configuredWindows.tier2Minutes} min | Tier 3: ${s.configuredWindows.tier3Minutes} min`);

    console.log(`\n=== 5. Slashing ===`);
    console.log(s.slashing.note);
    console.log("");
}

main();
