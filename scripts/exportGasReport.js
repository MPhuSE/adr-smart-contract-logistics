const fs = require("fs");

function main() {
    console.log("Exporting Gas Report...");
    
    if (!fs.existsSync("results/gas-report.csv")) {
        console.error("No gas-report.csv found! Please run 'npx hardhat run scripts/runSimulation.js' first.");
        return;
    }

    const report = fs.readFileSync("results/gas-report.csv", "utf-8");
    console.log("\n=== Average Gas Used per Function ===");
    console.log(report);
    console.log("Gas report is saved in results/gas-report.csv. This file can be imported into your paper for the evaluation section.");
}

main();
