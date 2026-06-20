// Monte-Carlo replication of the Tier 2 / Tier 3 voting outcomes.
//
// The on-chain run (runSimulation.js) is expensive, so it is executed once with
// a fixed seed for gas/routing and a single correctness sample. The contract's
// finalizeVote merely tallies committed votes, so the *statistical* behaviour of
// jury/expert correctness is fully determined by the off-chain honesty draws.
// This script reproduces that voting process in pure JS across many independent
// replications to report a mean +/- 95% confidence interval, and compares it to
// the closed-form binomial majority probability.
//
// This is what justifies the correctness numbers statistically; the blockchain
// adds no randomness beyond the votes generated here. Configure with env vars:
//   REPS (default 1000), SAMPLES_PER_REP (default 1000), SEED (default 7).

function mulberry32(seed) {
    let a = seed >>> 0;
    return function () {
        a |= 0;
        a = (a + 0x6d2b79f5) | 0;
        let t = Math.imul(a ^ (a >>> 15), 1 | a);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

function choose(n, k) {
    let r = 1;
    for (let i = 0; i < k; i++) r = (r * (n - i)) / (i + 1);
    return r;
}
function majorityCorrect(n, p) {
    let prob = 0;
    for (let k = Math.floor(n / 2) + 1; k <= n; k++) {
        prob += choose(n, k) * Math.pow(p, k) * Math.pow(1 - p, n - k);
    }
    return prob;
}

// One panel: `size` voters each correct w.p. p; majority decides. Returns 1/0.
function panelCorrect(rng, size, p) {
    let correct = 0;
    for (let i = 0; i < size; i++) if (rng() < p) correct++;
    return correct > size / 2 ? 1 : 0;
}

function run(label, size, p, reps, samples, rng) {
    const repRates = [];
    for (let r = 0; r < reps; r++) {
        let c = 0;
        for (let s = 0; s < samples; s++) c += panelCorrect(rng, size, p);
        repRates.push(c / samples);
    }
    const mean = repRates.reduce((a, b) => a + b, 0) / reps;
    const variance = repRates.reduce((a, b) => a + (b - mean) ** 2, 0) / (reps - 1);
    const sd = Math.sqrt(variance);
    const se = sd / Math.sqrt(reps);
    const ci = [mean - 1.96 * se, mean + 1.96 * se];
    const theoretical = majorityCorrect(size, p);

    console.log(`\n${label} (${size} voters, p_honest=${p})`);
    console.log(`  replications:        ${reps} x ${samples} samples`);
    console.log(`  observed mean:       ${(mean * 100).toFixed(2)}%`);
    console.log(`  95% CI across reps:  [${(ci[0] * 100).toFixed(2)}%, ${(ci[1] * 100).toFixed(2)}%]`);
    console.log(`  theoretical (binom): ${(theoretical * 100).toFixed(2)}%`);
    const inside = theoretical >= ci[0] && theoretical <= ci[1];
    console.log(`  theoretical in CI:   ${inside ? "yes (simulation matches theory)" : "NO - investigate"}`);

    return {
        label, size, pHonest: p, reps, samplesPerRep: samples,
        observedMean: +(mean * 100).toFixed(2),
        ci95: [+(ci[0] * 100).toFixed(2), +(ci[1] * 100).toFixed(2)],
        theoretical: +(theoretical * 100).toFixed(2),
        theoreticalInsideCI: inside,
    };
}

function main() {
    const REPS = parseInt(process.env.REPS || "1000", 10);
    const SAMPLES = parseInt(process.env.SAMPLES_PER_REP || "1000", 10);
    const SEED = parseInt(process.env.SEED || "7", 10);
    const P_ARB = parseFloat(process.env.P_ARB_HONEST || "0.8");
    const P_EXP = parseFloat(process.env.P_EXP_HONEST || "0.9");
    const rng = mulberry32(SEED);

    console.log(`Monte-Carlo CI for jury/expert correctness  (SEED=${SEED}, REPS=${REPS}, SAMPLES/REP=${SAMPLES})`);
    const out = {
        seed: SEED, reps: REPS, samplesPerRep: SAMPLES,
        tier2Jury: run("Tier 2 jury", 3, P_ARB, REPS, SAMPLES, rng),
        tier3Expert: run("Tier 3 expert panel", 5, P_EXP, REPS, SAMPLES, rng),
    };

    const fs = require("fs");
    if (!fs.existsSync("results")) fs.mkdirSync("results");
    fs.writeFileSync("results/replication.json", JSON.stringify(out, null, 2));
    console.log("\nresults/replication.json written");
}

main();
