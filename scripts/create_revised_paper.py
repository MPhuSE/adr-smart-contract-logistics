import csv
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "revised_figures"
OUTPUT_PATH = ROOT / "Smart_Contract_Dispute_Resolution_Paper_Revised_Black_White.docx"

TYPE_NAMES = {
    "0": "Late delivery",
    "1": "Shortage",
    "2": "Damage",
    "3": "Delivery denial",
    "4": "Payment delay",
}

BLUE = "#202020"
LIGHT_BLUE = "#E3E3E3"
GREEN = "#505050"
ORANGE = "#777777"
RED = "#999999"
GRAY = "#666666"
LIGHT_GRAY = "#F0F0F0"
INK = "#111111"


def load_font(size, bold=False):
    candidates = [
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
        if bold
        else "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_results():
    with (RESULTS_DIR / "results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with (RESULTS_DIR / "summary.json").open(encoding="utf-8") as handle:
        summary = json.load(handle)
    with (RESULTS_DIR / "gas-report.csv").open(newline="", encoding="utf-8") as handle:
        gas_rows = list(csv.DictReader(handle))
    return rows, summary, gas_rows


def calculate_stats(rows):
    tier_rows = defaultdict(list)
    type_rows = defaultdict(list)
    for row in rows:
        tier_rows[row["tier"]].append(row)
        type_rows[row["type"]].append(row)

    tiers = {}
    for tier, items in tier_rows.items():
        tiers[tier] = {
            "count": len(items),
            "rate": 100 * len(items) / len(rows),
            "avg_gas": sum(int(x["totalGas"]) for x in items) / len(items),
            "avg_minutes": sum(float(x["configuredWindowMinutes"]) for x in items)
            / len(items),
            "correctness": 100
            * sum(x["correct"] == "Yes" for x in items)
            / len(items),
        }

    types = {}
    for dispute_type, items in type_rows.items():
        types[dispute_type] = {
            "count": len(items),
            "rate": 100 * len(items) / len(rows),
            "correctness": 100
            * sum(x["correct"] == "Yes" for x in items)
            / len(items),
        }

    return {
        "count": len(rows),
        "overall_correctness": 100
        * sum(x["correct"] == "Yes" for x in rows)
        / len(rows),
        "overall_avg_gas": sum(int(x["totalGas"]) for x in rows) / len(rows),
        "overall_avg_minutes": sum(float(x["configuredWindowMinutes"]) for x in rows)
        / len(rows),
        "tiers": tiers,
        "types": types,
    }


def draw_box(draw, box, title, lines, fill, outline=BLUE):
    x1, y1, x2, y2 = box
    draw.rounded_rectangle(box, radius=12, fill=fill, outline=outline, width=3)
    draw.text((x1 + 18, y1 + 14), title, font=load_font(25, True), fill=INK)
    y = y1 + 55
    for line in lines:
        draw.text((x1 + 18, y), line, font=load_font(19), fill=INK)
        y += 28


def arrow(draw, start, end, color=GRAY):
    draw.line([start, end], fill=color, width=5)
    x2, y2 = end
    x1, y1 = start
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        points = [(x2, y2), (x2 - 14 * direction, y2 - 9), (x2 - 14 * direction, y2 + 9)]
    else:
        direction = 1 if y2 > y1 else -1
        points = [(x2, y2), (x2 - 9, y2 - 14 * direction), (x2 + 9, y2 - 14 * direction)]
    draw.polygon(points, fill=color)


def create_architecture_figure(path):
    image = Image.new("RGB", (1600, 900), "white")
    draw = ImageDraw.Draw(image)
    draw.text(
        (800, 38),
        "Prototype architecture implemented in the repository",
        font=load_font(36, True),
        fill=INK,
        anchor="ma",
    )

    draw_box(
        draw,
        (70, 155, 400, 330),
        "External actors",
        ["Buyer / seller", "Oracle role", "Arbitrators / experts"],
        LIGHT_GRAY,
        GRAY,
    )
    draw_box(
        draw,
        (610, 110, 990, 285),
        "SLAContract",
        ["Typed clauses and measured values", "AccessControl for admin/oracle", "Computes penalty amount"],
        LIGHT_BLUE,
    )
    draw_box(
        draw,
        (1110, 110, 1510, 285),
        "EvidenceVault",
        ["Stores CID, supplied hash", "submitter and timestamp", "Verifies stored hash equality"],
        "#ECECEC",
        GREEN,
    )
    draw_box(
        draw,
        (610, 410, 990, 625),
        "DisputeResolution",
        ["Tier 1 deterministic ruling", "Tier 2 commit-reveal jury", "Tier 3 expert appeal", "State-only enforcement event"],
        "#DEDEDE",
        ORANGE,
    )
    draw_box(
        draw,
        (1110, 410, 1510, 625),
        "DisputeRegistry",
        ["1 ETH arbitrator stake", "2 ETH expert stake", "Selection, locking and slashing", "Role-gated resolution calls"],
        "#D0D0D0",
        RED,
    )
    draw_box(
        draw,
        (610, 720, 990, 845),
        "Hardhat simulation",
        ["Synthetic disputes and time travel", "Gas receipts and CSV artifacts"],
        LIGHT_GRAY,
        GRAY,
    )

    arrow(draw, (400, 235), (610, 195))
    arrow(draw, (400, 275), (610, 500))
    arrow(draw, (990, 195), (1110, 195))
    arrow(draw, (800, 285), (800, 410))
    arrow(draw, (990, 515), (1110, 515))
    arrow(draw, (1110, 555), (990, 555))
    arrow(draw, (800, 720), (800, 625))

    draw.text(
        (800, 675),
        "No production oracle, VRF, IPFS upload service, or Ether escrow settlement is implemented.",
        font=load_font(21, True),
        fill=INK,
        anchor="ma",
    )
    image.save(path)


def create_bar_chart(path, title, labels, values, colors, y_label, suffix=""):
    width, height = 1600, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((width / 2, 42), title, font=load_font(38, True), fill=INK, anchor="ma")
    left, top, right, bottom = 150, 150, 1510, 740
    draw.line((left, top, left, bottom), fill=INK, width=3)
    draw.line((left, bottom, right, bottom), fill=INK, width=3)
    max_value = max(values) * 1.15
    step = (right - left) / len(values)
    bar_width = step * 0.58

    for index, (label, value, color) in enumerate(zip(labels, values, colors)):
        x1 = left + step * index + (step - bar_width) / 2
        x2 = x1 + bar_width
        y1 = bottom - (value / max_value) * (bottom - top)
        draw.rectangle((x1, y1, x2, bottom), fill=color, outline=INK, width=2)
        display = f"{value:,.1f}{suffix}" if isinstance(value, float) else f"{value:,}{suffix}"
        draw.text(((x1 + x2) / 2, y1 - 16), display, font=load_font(24, True), fill=INK, anchor="ms")
        wrapped = label.split("\n")
        for line_index, line in enumerate(wrapped):
            draw.text(
                ((x1 + x2) / 2, bottom + 32 + 27 * line_index),
                line,
                font=load_font(22),
                fill=INK,
                anchor="ma",
            )

    label_layer = Image.new("RGBA", (700, 70), (255, 255, 255, 0))
    label_draw = ImageDraw.Draw(label_layer)
    label_draw.text(
        (350, 35),
        y_label,
        font=load_font(27, True),
        fill=INK,
        anchor="mm",
    )
    rotated_label = label_layer.rotate(90, expand=True)
    image.paste(
        rotated_label,
        (22, int((height - rotated_label.height) / 2)),
        rotated_label,
    )
    image.save(path)


def generate_figures(stats, gas_rows):
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    create_architecture_figure(FIGURES_DIR / "architecture.png")

    tier_labels = ["Tier 1\nAuto", "Tier 2\nJury", "Tier 3\nExpert"]
    create_bar_chart(
        FIGURES_DIR / "tier_distribution.png",
        "Synthetic dispute distribution by resolution tier",
        tier_labels,
        [stats["tiers"][str(i)]["rate"] for i in (1, 2, 3)],
        [GREEN, ORANGE, BLUE],
        "Share of 1,000 cases (%)",
        "%",
    )
    create_bar_chart(
        FIGURES_DIR / "tier_gas.png",
        "Recorded gas included in the simulation totalGas field",
        tier_labels,
        [round(stats["tiers"][str(i)]["avg_gas"]) for i in (1, 2, 3)],
        [GREEN, ORANGE, BLUE],
        "Average gas units",
    )

    type_order = ["0", "1", "2", "3", "4"]
    create_bar_chart(
        FIGURES_DIR / "type_correctness.png",
        "Synthetic ruling correctness by dispute type",
        ["Late\ndelivery", "Shortage", "Damage", "Delivery\ndenial", "Payment\ndelay"],
        [stats["types"][key]["correctness"] for key in type_order],
        [BLUE, GREEN, ORANGE, RED, GRAY],
        "Correct rulings (%)",
        "%",
    )

    selected_names = [
        "createSLA",
        "createDispute",
        "submitEvidence",
        "commitVote",
        "revealVote",
        "finalizeVote",
        "resolveTier1",
        "enforce",
    ]
    gas_map = {row["Function"]: int(row["AverageGas"]) for row in gas_rows}
    create_bar_chart(
        FIGURES_DIR / "operation_gas.png",
        "Average gas by measured contract operation",
        [
            "Create\nSLA",
            "Create\ndispute",
            "Submit\nevidence",
            "Commit\nvote",
            "Reveal\nvote",
            "Finalize\nvote",
            "Resolve\nTier 1",
            "Enforce\nstate",
        ],
        [gas_map[name] for name in selected_names],
        [BLUE, BLUE, GREEN, ORANGE, ORANGE, ORANGE, GREEN, GRAY],
        "Average gas units",
    )


def shade_cell(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill.replace("#", ""))
    tc_pr.append(shd)


def set_cell_text(cell, text, bold=False, color=None, size=9):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(str(text))
    run.bold = bold
    run.font.name = "Arial"
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor.from_string(color.replace("#", ""))
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(doc, headers, rows, widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[index], header, bold=True, color="FFFFFF")
        shade_cell(table.rows[0].cells[index], BLUE)
    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        for col_index, value in enumerate(values):
            set_cell_text(cells[col_index], value)
            if row_index % 2:
                shade_cell(cells[col_index], "F2F5F7")
    if widths:
        for row in table.rows:
            for index, width in enumerate(widths):
                row.cells[index].width = Inches(width)
    doc.add_paragraph()
    return table


def add_caption(doc, text):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.italic = True
    run.font.name = "Arial"
    run.font.size = Pt(9)


def add_picture(doc, path, caption):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.add_run().add_picture(str(path), width=Inches(6.45))
    add_caption(doc, caption)


def add_code(doc, code):
    paragraph = doc.add_paragraph()
    paragraph.style = doc.styles["No Spacing"]
    paragraph.paragraph_format.left_indent = Inches(0.25)
    paragraph.paragraph_format.right_indent = Inches(0.25)
    paragraph.paragraph_format.space_before = Pt(4)
    paragraph.paragraph_format.space_after = Pt(6)
    for index, line in enumerate(code.strip("\n").splitlines()):
        run = paragraph.add_run(line)
        run.font.name = "Courier New"
        run.font.size = Pt(8.2)
        if index < len(code.strip("\n").splitlines()) - 1:
            run.add_break()
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "F1F3F5")
    p_pr.append(shd)


def add_bullet(doc, text):
    paragraph = doc.add_paragraph(style="List Bullet")
    paragraph.add_run(text)
    return paragraph


def add_number(doc, text):
    paragraph = doc.add_paragraph(style="List Number")
    paragraph.add_run(text)
    return paragraph


def configure_document(doc):
    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.65)
    section.left_margin = Inches(0.78)
    section.right_margin = Inches(0.78)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.05
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, color in [
        ("Title", 19, INK),
        ("Heading 1", 14, BLUE),
        ("Heading 2", 11.5, INK),
        ("Heading 3", 10.5, INK),
    ]:
        style = styles[name]
        style.font.name = "Arial"
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor.from_string(color.replace("#", ""))
        style.font.bold = True

    header = section.header.paragraphs[0]
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("Automated Multi-Tier Dispute Resolution for Supply-Chain Logistics")
    run.font.name = "Arial"
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(95, 107, 115)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run("Revised manuscript aligned with repository implementation - Page ")
    run.font.name = "Arial"
    run.font.size = Pt(8)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)


def add_title_page(doc):
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(55)
    run = title.add_run(
        "Automated Multi-Tier Dispute Resolution for Supply-Chain Logistics:\n"
        "A Smart-Contract Prototype and Synthetic Hardhat Evaluation"
    )
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(21)
    run.font.color.rgb = RGBColor.from_string(BLUE.replace("#", ""))

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.paragraph_format.space_before = Pt(22)
    run = subtitle.add_run("Revised manuscript aligned with the current source code and generated artifacts")
    run.italic = True
    run.font.name = "Arial"
    run.font.size = Pt(11)

    author = doc.add_paragraph()
    author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    author.paragraph_format.space_before = Pt(34)
    author.add_run("Author information to be inserted before submission").italic = True

    box = doc.add_table(rows=1, cols=1)
    box.alignment = WD_TABLE_ALIGNMENT.CENTER
    box.style = "Table Grid"
    cell = box.cell(0, 0)
    shade_cell(cell, "E8E8E8")
    set_cell_text(
        cell,
        "Artifact scope: Solidity 0.8.20, Hardhat local execution, four contracts, "
        "1,000 synthetic disputes. The prototype does not claim a Sepolia deployment, "
        "production-grade randomness, complete escrow settlement, or a completed third-party audit.",
        size=10,
    )
    doc.add_page_break()


def add_abstract(doc, stats):
    doc.add_heading("Abstract", level=1)
    text = (
        "Disputes in supply-chain logistics combine objectively measurable events, such as late "
        "delivery and payment delay, with subjective claims, such as damaged goods and delivery "
        "denial. This paper presents and evaluates a Solidity prototype that routes these cases "
        "through three resolution tiers. Tier 1 evaluates typed service-level agreement clauses "
        "against oracle-supplied values. Tier 2 assigns three staked arbitrators and applies "
        "commit-reveal voting with slashing for non-reveal or minority votes. Tier 3 permits an "
        "appeal backed by a 0.5 ETH bond and assigns five registered experts. The implementation "
        "contains four contracts: SLAContract, EvidenceVault, DisputeRegistry, and "
        "DisputeResolution. A Hardhat simulation generated "
        f"{stats['count']:,} synthetic disputes. Of these, "
        f"{stats['tiers']['1']['rate']:.1f}% followed Tier 1, "
        f"{stats['tiers']['2']['rate']:.1f}% Tier 2, and "
        f"{stats['tiers']['3']['rate']:.1f}% Tier 3. Under the simulation assumptions, overall "
        f"agreement with the generated ground truth was {stats['overall_correctness']:.1f}%. "
        "The reported gas values are transaction receipts collected from local Hardhat execution; "
        "however, aggregate per-tier totals omit several setup and auxiliary transactions and are "
        "therefore treated as prototype measurements rather than complete production costs. The "
        "study demonstrates executable tier routing and voting behavior while explicitly identifying "
        "remaining requirements for production deployment: secure randomness, decentralized oracle "
        "inputs, access-control hardening, complete escrow settlement, reproducible statistical "
        "experiments, and independent security analysis."
    )
    doc.add_paragraph(text)
    keywords = doc.add_paragraph()
    keywords.add_run("Keywords: ").bold = True
    keywords.add_run(
        "smart contracts; supply-chain logistics; dispute resolution; SLA; commit-reveal voting; "
        "staked arbitration; Hardhat simulation."
    )


def build_document(rows, summary, gas_rows, stats):
    doc = Document()
    configure_document(doc)
    add_title_page(doc)
    add_abstract(doc, stats)

    doc.add_heading("1. Introduction", level=1)
    doc.add_paragraph(
        "Supply-chain agreements coordinate buyers, sellers, carriers, warehouses, and payment "
        "providers across organizational boundaries. When delivery or settlement events do not match "
        "the agreed terms, the parties need a process that can distinguish objective breaches from "
        "claims requiring human judgment. Smart contracts can evaluate deterministic conditions, but "
        "they cannot independently establish the truth of off-chain events. The prototype studied here "
        "therefore combines clause evaluation, evidence anchoring, staked voting, and an expert appeal "
        "tier."
    )
    doc.add_paragraph(
        "This revised paper limits its claims to behavior represented in the repository. The evaluation "
        "is a local Hardhat simulation rather than a public-testnet field deployment. Correctness is "
        "measured against synthetic ground truth generated by the simulation, not against adjudicated "
        "real-world disputes. Likewise, protocol time is derived from configured commit and reveal "
        "windows using EVM time advancement, rather than wall-clock observation."
    )
    doc.add_heading("1.1 Research questions", level=2)
    add_number(doc, "How does the prototype encode five logistics dispute types as typed SLA clauses?")
    add_number(doc, "How are objective and subjective disputes routed through the implemented three-tier state machine?")
    add_number(doc, "What gas, routing, and synthetic correctness outcomes are observed in the current Hardhat experiment?")
    add_number(doc, "Which implementation gaps prevent the prototype from being treated as a production arbitration system?")
    doc.add_heading("1.2 Contributions", level=2)
    add_bullet(doc, "A source-aligned description of four interacting Solidity contracts.")
    add_bullet(doc, "A three-tier state machine with Tier 2 and Tier 3 commit-reveal voting.")
    add_bullet(doc, "A transparent analysis of 1,000 synthetic disputes and transaction gas receipts.")
    add_bullet(doc, "An explicit threat-to-validity and production-readiness assessment.")

    doc.add_heading("2. Related Work", level=1)
    doc.add_paragraph(
        "Blockchain supply-chain research commonly focuses on provenance, traceability, and shared "
        "records across mutually distrusting organizations [3]-[5]. Decentralized arbitration systems "
        "such as Kleros use economically staked jurors and appeal rounds to decide subjective disputes "
        "[6]. Smart-contract SLA research has explored automated monitoring in cloud and IoT contexts "
        "[7], [8]. The present prototype combines these ideas at a smaller experimental scale: objective "
        "logistics clauses are evaluated in code, while subjective claims are routed to staked voters."
    )
    doc.add_paragraph(
        "The boundary between on-chain state and real-world truth remains central. Oracle data, IPFS "
        "availability, identity, legal enforceability, and privacy are external assumptions rather than "
        "properties established by Solidity alone. This paper therefore treats the implementation as a "
        "protocol prototype and avoids claiming that blockchain removes the need for trusted data sources."
    )

    doc.add_heading("3. Dispute Model and SLA Encoding", level=1)
    doc.add_heading("3.1 Implemented dispute taxonomy", level=2)
    add_table(
        doc,
        ["Enum value", "Dispute class", "Prototype route", "Input used"],
        [
            ["0", "Late delivery", "Tier 1", "Measured value > threshold"],
            ["1", "Shortage", "Tier 1", "Measured value < threshold"],
            ["2", "Damage", "Tier 2", "Human judgment over evidence"],
            ["3", "Delivery denial", "Tier 3 in simulation", "Human/expert judgment"],
            ["4", "Payment delay", "Tier 1", "Measured value > threshold"],
        ],
        [0.7, 1.5, 1.1, 2.7],
    )
    doc.add_paragraph(
        "SLAContract defines four comparison operators: GreaterThan, LessThan, Equal, and NotEqual. "
        "Each clause stores a dispute type, operator, threshold, and penalty in basis points. Oracle-role "
        "accounts write measured values. The contract then evaluates the selected operator and computes "
        "a penalty amount from the recorded escrowValue."
    )
    add_code(
        doc,
        """
enum DisputeType {
    LateDelivery, Shortage, Damage, DeliveryDenial, PaymentDelay
}
enum Operator { GreaterThan, LessThan, Equal, NotEqual }

struct Clause {
    DisputeType disputeType;
    Operator operator;
    uint256 threshold;
    uint256 penaltyBps;
}
""",
    )
    add_caption(doc, "Listing 1. Source-aligned clause representation in SLAContract.")
    doc.add_heading("3.2 Evaluation semantics", level=2)
    doc.add_paragraph(
        "The current evaluateClause function returns (false, 0) both when a measured value has not been "
        "provided and when a measured value represents no breach. Resolution code should ideally "
        "distinguish NOT_EVALUABLE from NO_BREACH. The current prototype instead prevents automatic "
        "resolution only for Damage and DeliveryDenial, while the remaining types produce a buyer or "
        "seller ruling."
    )
    add_code(
        doc,
        """
function EvaluateObjectiveClause(slaId, clauseId):
    require SLA is active and clauseId exists
    if no oracle value exists:
        return NOT_EVALUABLE
    breach = compare(measuredValue, operator, threshold)
    penalty = breach ? escrowValue * penaltyBps / 10000 : 0
    return breach ? BREACH : NO_BREACH, penalty
""",
    )
    add_caption(doc, "Algorithm 1. Recommended three-state interpretation of clause evaluation.")

    doc.add_heading("4. Prototype Architecture", level=1)
    add_picture(
        doc,
        FIGURES_DIR / "architecture.png",
        "Figure 1. Implemented contracts and external assumptions. The red note separates implemented behavior from production services.",
    )
    add_table(
        doc,
        ["Contract", "Implemented responsibility", "OpenZeppelin base"],
        [
            ["SLAContract", "Clauses, oracle values, computed penalties", "AccessControl"],
            ["EvidenceVault", "CID, supplied hash, submitter, timestamp", "None"],
            ["DisputeRegistry", "Stake, jury/expert lists, lock, slash, reward counters", "AccessControl, ReentrancyGuard"],
            ["DisputeResolution", "Lifecycle, commit-reveal, appeal and enforcement state", "Ownable, Pausable, ReentrancyGuard"],
        ],
        [1.25, 3.2, 1.6],
    )
    doc.add_heading("4.1 Contract interactions", level=2)
    doc.add_paragraph(
        "DisputeResolution references the other three contracts. It queries SLAContract for clause "
        "evaluation, calls EvidenceVault when an initial CID is supplied, and calls DisputeRegistry to "
        "select, lock, release, slash, or credit voter counters. Registry functions that modify voter "
        "profiles are protected by RESOLUTION_ROLE, which is granted to DisputeResolution by the "
        "deployment script."
    )
    doc.add_heading("4.2 Evidence model", level=2)
    doc.add_paragraph(
        "EvidenceVault stores the CID string and a caller-supplied bytes32 evidenceHash. verifyEvidence "
        "checks equality against a later supplied hash. This provides an immutable record of what was "
        "submitted, but the contract does not upload data to IPFS, validate CID syntax, encrypt evidence, "
        "or verify that evidence content is available. Because CID strings are public blockchain state, "
        "the prototype should not be described as preserving evidence privacy."
    )
    doc.add_heading("4.3 Financial model", level=2)
    doc.add_paragraph(
        "The recorded SLA escrowValue is an accounting input, not Ether held by SLAContract. createSLA is "
        "not payable, and enforcement changes the dispute state and emits an event without transferring "
        "funds. Arbitrator and expert stakes are real contract balances in local execution, and appealToTier3 "
        "receives a 0.5 ETH bond; however, the current implementation does not settle that bond after the "
        "appeal. Complete escrow and bond distribution remain future work."
    )

    doc.add_heading("5. Resolution Protocol", level=1)
    doc.add_heading("5.1 State machine", level=2)
    add_code(
        doc,
        """
Created -> Disputed
Disputed -> Tier1Resolved -> Enforced
Disputed/Tier1Resolved -> Tier2Commit -> Tier2Reveal -> Tier2Resolved
Tier2Resolved -> Tier3Commit -> Tier3Reveal -> Tier3Resolved
Tier2Resolved/Tier3Resolved -> Enforced
""",
    )
    doc.add_paragraph(
        "Tier 1 evaluates all non-subjective types. Damage and DeliveryDenial revert when resolveTier1 "
        "is called, requiring explicit escalation. Tier 2 selects three registered arbitrators. Tier 3 "
        "selects five registered experts after an exact 0.5 ETH appeal bond is posted."
    )
    doc.add_heading("5.2 Commit-reveal voting", level=2)
    add_code(
        doc,
        """
commit = keccak256(abi.encodePacked(uint8(ruling), salt))
commit during 1-day COMMIT_WINDOW
reveal ruling and salt during 1-day REVEAL_WINDOW
after deadline:
    slash each non-revealer by 0.1 ETH
    count BuyerWins and SellerWins reveals
    slash each revealed minority voter by 0.1 ETH
    set final ruling; a tie produces Ruling.None
""",
    )
    doc.add_paragraph(
        "The source uses a fixed 0.1 ETH slash amount rather than a percentage. This equals 10% of the "
        "1 ETH arbitrator stake and 5% of the 2 ETH expert stake. Majority voters receive a correctVotes "
        "counter increment but no monetary reward. Contrary to the original manuscript, ties do not "
        "resolve in favor of the defendant; they produce Ruling.None."
    )
    doc.add_heading("5.3 Selection mechanism", level=2)
    doc.add_paragraph(
        "Selection is deterministic in the prototype. For dispute seed s and position i, the selected "
        "index is (s + i) mod poolLength. This produces consecutive roster members and is not a "
        "Fisher-Yates shuffle, block-hash draw, or verifiable random function. It is adequate for repeatable "
        "tests but unsuitable for adversarial deployment."
    )

    doc.add_heading("6. Implementation and Reproducibility", level=1)
    add_table(
        doc,
        ["Item", "Repository setting"],
        [
            ["Solidity", "Pragma ^0.8.20; Hardhat compiler 0.8.20"],
            ["Optimizer", "Enabled, 200 runs"],
            ["Framework", "Hardhat 2.x with ethers/toolbox"],
            ["Security library", "OpenZeppelin Contracts 5.x"],
            ["Execution environment", "Local Hardhat EVM"],
            ["Simulation size", "1,000 synthetic disputes"],
            ["Artifacts", "results/results.csv, summary.json, gas-report.csv"],
        ],
        [1.8, 4.2],
    )
    doc.add_paragraph("The core artifact can be reproduced with:")
    add_code(
        doc,
        """
npm install
npx hardhat compile
npx hardhat test test/dispute.test.js test/invariant.test.js
npx hardhat run scripts/runSimulation.js
node scripts/analyzeResults.js
""",
    )
    doc.add_paragraph(
        "The repository still contains the default test/Lock.js while Lock.sol has been removed. Running "
        "the unfiltered full test command therefore produces 11 passing project tests and 9 failing "
        "obsolete Lock tests. Reproducibility requires removing that stale test or invoking only the "
        "project-specific files shown above."
    )

    doc.add_heading("7. Experimental Method", level=1)
    doc.add_heading("7.1 Synthetic case generation", level=2)
    doc.add_paragraph(
        "The simulation deploys fresh contracts on a local Hardhat network, creates one reusable SLA, "
        "registers arbitrator and expert accounts, and generates 1,000 disputes with JavaScript "
        "Math.random(). The configured probabilities are 30% LateDelivery, 20% Shortage, 20% Damage, "
        "15% DeliveryDenial, and 15% PaymentDelay. Realized counts vary because no random seed is stored."
    )
    add_table(
        doc,
        ["Type", "Observed cases", "Observed share", "Synthetic behavior"],
        [
            [
                TYPE_NAMES[key],
                stats["types"][key]["count"],
                f"{stats['types'][key]['rate']:.1f}%",
                "Objective oracle rule" if key in {"0", "1", "4"} else ("80% honest jury votes" if key == "2" else "Experts forced to generated truth"),
            ]
            for key in ["0", "1", "2", "3", "4"]
        ],
        [1.5, 1.0, 1.1, 2.7],
    )
    doc.add_heading("7.2 Ground truth and correctness", level=2)
    doc.add_paragraph(
        "For objective cases, the script first samples a winner and then writes a measured value chosen "
        "to produce that winner. For Damage, each of three jurors independently follows the generated "
        "winner with probability 0.8. For DeliveryDenial, the script assigns actualWinner = expectedWinner "
        "before the expert vote, making Tier 3 correctness 100% by construction. Consequently, correctness "
        "measures internal simulation consistency under assumed voter behavior; it is not empirical legal "
        "or factual accuracy."
    )
    doc.add_heading("7.3 Gas accounting", level=2)
    doc.add_paragraph(
        "gas-report.csv records receipt gas for named operations. The per-case totalGas field, however, "
        "adds only createDispute, selected resolution calls, and enforce. It excludes evidence submission, "
        "oracle updates, phase transitions, and multiple Tier 3 commit/reveal receipts. The tier totals are "
        "therefore partial workflow totals. Per-operation measurements remain useful for profiling, while "
        "aggregate USD cost claims require a corrected accounting script."
    )

    doc.add_heading("8. Results", level=1)
    doc.add_heading("8.1 Routing distribution", level=2)
    add_picture(
        doc,
        FIGURES_DIR / "tier_distribution.png",
        "Figure 2. Observed tier distribution in the current 1,000-case CSV artifact.",
    )
    add_table(
        doc,
        ["Tier", "Cases", "Share", "Configured time", "Synthetic correctness"],
        [
            [
                "Tier 1",
                stats["tiers"]["1"]["count"],
                f"{stats['tiers']['1']['rate']:.1f}%",
                "5 min label",
                f"{stats['tiers']['1']['correctness']:.2f}%",
            ],
            [
                "Tier 2",
                stats["tiers"]["2"]["count"],
                f"{stats['tiers']['2']['rate']:.1f}%",
                "2 days",
                f"{stats['tiers']['2']['correctness']:.2f}%",
            ],
            [
                "Tier 3",
                stats["tiers"]["3"]["count"],
                f"{stats['tiers']['3']['rate']:.1f}%",
                "4 days",
                f"{stats['tiers']['3']['correctness']:.2f}%",
            ],
        ],
        [1.0, 0.8, 0.9, 1.4, 1.5],
    )
    doc.add_paragraph(
        f"The weighted average configured resolution time is {stats['overall_avg_minutes']:.2f} minutes "
        f"({stats['overall_avg_minutes'] / 60:.2f} hours). Tier 2 requires both a one-day commit window "
        "and a one-day reveal window. Tier 3 first passes through Tier 2 and then repeats the two windows "
        "for experts, yielding the four-day simulation label."
    )
    doc.add_heading("8.2 Synthetic correctness", level=2)
    add_picture(
        doc,
        FIGURES_DIR / "type_correctness.png",
        "Figure 3. Agreement with generated ground truth. Values reflect simulation assumptions rather than real adjudication accuracy.",
    )
    doc.add_paragraph(
        f"Overall correctness is {stats['overall_correctness']:.1f}%. All errors occur in Damage cases "
        "resolved by the three-person jury. The 90.32% Damage result is compatible with majority voting "
        "under independently sampled 80% honest votes. The 100% figures for objective and expert cases "
        "are expected from how the script constructs their inputs and outcomes."
    )
    doc.add_heading("8.3 Gas measurements", level=2)
    add_picture(
        doc,
        FIGURES_DIR / "operation_gas.png",
        "Figure 4. Mean gas receipts for selected operations in gas-report.csv.",
    )
    add_table(
        doc,
        ["Operation", "Average gas"],
        [[row["Function"], f"{int(row['AverageGas']):,}"] for row in gas_rows],
        [2.6, 1.5],
    )
    add_picture(
        doc,
        FIGURES_DIR / "tier_gas.png",
        "Figure 5. Partial per-tier totals from results.csv. Tier 3 appears below Tier 2 because several Tier 3 receipts are omitted from totalGas.",
    )
    doc.add_paragraph(
        f"The CSV reports an overall partial average of {stats['overall_avg_gas']:,.0f} gas. At the "
        "simulation assumptions of 20 gwei and USD 3,000/ETH, this arithmetic corresponds to "
        f"approximately USD {stats['overall_avg_gas'] * 20e-9 * 3000:.2f}. This is not a complete "
        "end-to-end dispute cost because of the omitted transactions described above, and it excludes "
        "oracle, IPFS, capital-lockup, juror compensation, and public-network variability."
    )

    doc.add_heading("9. Security and Protocol Analysis", level=1)
    doc.add_heading("9.1 Properties exercised by tests", level=2)
    doc.add_paragraph(
        "The project-specific Hardhat tests cover SLA creation and evaluation, evidence hash equality, "
        "Tier 1 routing, one Tier 2 majority scenario with a non-revealer, and entry into Tier 3. Two "
        "additional tests check that a resolved dispute stores one enum ruling and that a direct registry "
        "slash decreases stake. These are useful examples but do not constitute formal verification or a "
        "complete scenario matrix."
    )
    doc.add_heading("9.2 Source-level risks", level=2)
    add_bullet(doc, "Any account can create a dispute for any SLA and clause identifier.")
    add_bullet(doc, "Any account can post the appeal bond; the caller is not restricted to a losing contractual party.")
    add_bullet(doc, "Deterministic roster selection is predictable and vulnerable to targeted registration.")
    add_bullet(doc, "A voter whose stake falls below the original minimum remains registered and selectable.")
    add_bullet(doc, "The appeal bond and slashed balances have no complete distribution policy.")
    add_bullet(doc, "Pausable also blocks enforcement, so an emergency pause can delay final state progression.")
    add_bullet(doc, "Ruling.None can be finalized after a tie or no reveals and can then be marked Enforced.")
    add_bullet(doc, "Evidence integrity depends on caller-supplied hashes and off-chain content availability.")
    doc.add_heading("9.3 Static analysis status", level=2)
    doc.add_paragraph(
        "The repository contains a text file labeled 'Slither Static Analysis Report (Illustrative)'. "
        "Because it is not a captured tool invocation with version, command, and machine-readable output, "
        "this paper does not claim a completed Slither audit. No MythX artifact is present. Production "
        "claims should follow reproducible Slither execution, fuzz/property testing, and independent review."
    )

    doc.add_heading("10. Threats to Validity and Limitations", level=1)
    add_bullet(doc, "Internal validity: Math.random() is unseeded, so the exact experiment is not reproducible.")
    add_bullet(doc, "Construct validity: generated ground truth and assumed voter honesty are not real dispute outcomes.")
    add_bullet(doc, "Measurement validity: partial totalGas omits several transaction classes.")
    add_bullet(doc, "External validity: local Hardhat behavior does not establish Sepolia or mainnet performance.")
    add_bullet(doc, "Economic validity: no equilibrium, bribery, juror opportunity-cost, or liquidity experiment is performed.")
    add_bullet(doc, "Privacy validity: public CID metadata can leak information even when content is stored off-chain.")
    add_bullet(doc, "Legal validity: an on-chain state transition is not automatically an enforceable arbitral award.")
    doc.add_paragraph(
        "The main result should therefore be read as feasibility evidence for executable workflow logic, "
        "not evidence that the prototype is ready for production logistics or that it outperforms courts "
        "and commercial arbitration in deployed practice."
    )

    doc.add_heading("11. Production Roadmap", level=1)
    add_number(doc, "Separate clause evaluation into BREACH, NO_BREACH, and NOT_EVALUABLE outcomes.")
    add_number(doc, "Add participant authorization and validate SLA/clause existence during dispute creation.")
    add_number(doc, "Replace deterministic jury selection with request/fulfillment VRF and snapshot eligible pools.")
    add_number(doc, "Implement a dedicated escrow vault with conservation-of-funds invariants.")
    add_number(doc, "Define appeal-bond, slash, and juror-reward distribution rules.")
    add_number(doc, "Use seeded experiment configurations and include every transaction receipt in workflow totals.")
    add_number(doc, "Run repeated experiments and report confidence intervals and sensitivity to voter honesty.")
    add_number(doc, "Add fuzzing, stateful invariant tests, static analysis, and an independent audit.")
    add_number(doc, "Deploy to a named testnet and publish addresses, transactions, compiler metadata, and commit hash.")

    doc.add_heading("12. Conclusion", level=1)
    doc.add_paragraph(
        "The repository implements a coherent proof of concept for tiered logistics dispute resolution. "
        "It encodes five dispute types, protects oracle updates with role-based access control, records "
        "evidence references, manages staked voter profiles, executes two commit-reveal tiers, and records "
        "a final enforcement state. In the current 1,000-case synthetic artifact, "
        f"{stats['tiers']['1']['rate']:.1f}% of cases follow the automatic tier and overall rulings agree "
        f"with generated ground truth in {stats['overall_correctness']:.1f}% of cases."
    )
    doc.add_paragraph(
        "These results support the narrower conclusion that the workflow is executable under controlled "
        "Hardhat assumptions. They do not yet establish real-world adjudication accuracy, complete financial "
        "settlement, adversarial fairness, public-network cost, or production security. Addressing the "
        "identified architecture and evaluation gaps is the necessary next step toward a deployable system."
    )

    doc.add_heading("Code and Data Availability", level=1)
    doc.add_paragraph(
        "The artifact consists of the four Solidity contracts, Hardhat tests, deployment and simulation "
        "scripts, and CSV/JSON outputs in the project repository. A public repository URL, release tag, "
        "commit hash, license, and archived dataset DOI should be inserted before submission."
    )

    doc.add_heading("References", level=1)
    references = [
        '[1] S. Nakamoto, "Bitcoin: A Peer-to-Peer Electronic Cash System," 2008.',
        '[2] G. Wood, "Ethereum: A Secure Decentralised Generalised Transaction Ledger," Ethereum Yellow Paper, 2014.',
        '[3] S. Saberi, M. Kouhizadeh, J. Sarkis, and L. Shen, "Blockchain technology and its relationships to sustainable supply chain management," International Journal of Production Research, vol. 57, no. 7, pp. 2117-2135, 2019.',
        '[4] N. Kshetri, "Blockchain\'s roles in meeting key supply chain management objectives," International Journal of Information Management, vol. 39, pp. 80-89, 2018.',
        '[5] K. Wuest and A. Gervais, "Do You Need a Blockchain?" Proc. CVCBT, pp. 45-54, 2018.',
        '[6] C. Lesaege, F. Ast, and W. George, "Kleros Short Paper v1.0.7," 2019.',
        '[7] R. B. Uriarte, R. De Nicola, and K. Kritikos, "Towards distributed SLA management with smart contracts and blockchain," Proc. IEEE CloudCom, pp. 266-271, 2018.',
        '[8] H. Zhou et al., "A blockchain based witness model for trustworthy cloud service level agreement enforcement," Proc. IEEE INFOCOM, pp. 1567-1575, 2019.',
        '[9] N. Atzei, M. Bartoletti, and T. Cimoli, "A survey of attacks on Ethereum smart contracts," POST, 2017.',
        '[10] J. Feist, G. Grieco, and A. Groce, "Slither: A static analysis framework for smart contracts," IEEE/ACM WETSEB, 2019.',
        '[11] OpenZeppelin, "OpenZeppelin Contracts," software library, accessed 2026.',
        '[12] J. Benet, "IPFS - Content Addressed, Versioned, P2P File System," arXiv:1407.3561, 2014.',
    ]
    for reference in references:
        paragraph = doc.add_paragraph(reference)
        paragraph.paragraph_format.left_indent = Inches(0.22)
        paragraph.paragraph_format.first_line_indent = Inches(-0.22)
        paragraph.paragraph_format.space_after = Pt(3)

    doc.add_heading("Appendix A. Source-to-Claim Alignment", level=1)
    add_table(
        doc,
        ["Claim", "Status in current repository"],
        [
            ["Five logistics dispute types", "Implemented in SLAContract enum"],
            ["Three resolution tiers", "Implemented in DisputeResolution"],
            ["Commit-reveal voting", "Implemented for Tier 2 and Tier 3"],
            ["Random jury selection", "Not implemented; deterministic consecutive selection"],
            ["IPFS storage", "Not implemented; only CID/hash metadata is stored"],
            ["Escrow release and penalty transfer", "Not implemented; enforcement is state/event only"],
            ["Sepolia deployment", "No network configuration or deployment evidence"],
            ["Slither/MythX audit", "No reproducible completed audit artifact"],
            ["Formal invariant verification", "Not implemented; two example invariant tests exist"],
        ],
        [2.5, 3.7],
    )

    return doc


def main():
    rows, summary, gas_rows = load_results()
    stats = calculate_stats(rows)
    generate_figures(stats, gas_rows)
    document = build_document(rows, summary, gas_rows, stats)
    document.save(OUTPUT_PATH)
    print(f"Created: {OUTPUT_PATH}")
    print(f"Cases: {stats['count']}, correctness: {stats['overall_correctness']:.1f}%")


if __name__ == "__main__":
    main()
