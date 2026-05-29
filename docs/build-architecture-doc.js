// Generate hermes-bhavcopy-architecture.docx
// Run: node build-architecture-doc.js

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, PageOrientation, LevelFormat, HeadingLevel,
  BorderStyle, WidthType, ShadingType, PageBreak, TableOfContents,
  Header, Footer, PageNumber
} = require("docx");

// --- Helpers ----------------------------------------------------------------

const FONT = "Calibri";
const PAGE_WIDTH = 12240;       // US Letter, DXA
const PAGE_HEIGHT = 15840;
const MARGIN = 1080;            // 0.75 inch
const CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN; // 10080

const border = { style: BorderStyle.SINGLE, size: 4, color: "B4B4B4" };
const borders = { top: border, bottom: border, left: border, right: border };

function P(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 120 },
    alignment: opts.alignment,
    children: Array.isArray(text)
      ? text
      : [new TextRun({ text, font: FONT, size: opts.size ?? 22, bold: !!opts.bold, italics: !!opts.italics, color: opts.color })],
  });
}

function H1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    spacing: { before: 320, after: 200 },
    children: [new TextRun({ text, font: FONT, size: 36, bold: true, color: "0F3057" })],
  });
}

function H2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 260, after: 140 },
    children: [new TextRun({ text, font: FONT, size: 28, bold: true, color: "0F3057" })],
  });
}

function H3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, font: FONT, size: 24, bold: true, color: "1F4E79" })],
  });
}

function Code(lines) {
  // Render as a monospaced single-cell table for visual separation
  const text = Array.isArray(lines) ? lines : [lines];
  return new Table({
    width: { size: CONTENT_WIDTH, type: WidthType.DXA },
    columnWidths: [CONTENT_WIDTH],
    rows: [new TableRow({
      children: [new TableCell({
        borders,
        width: { size: CONTENT_WIDTH, type: WidthType.DXA },
        shading: { fill: "F4F4F4", type: ShadingType.CLEAR },
        margins: { top: 120, bottom: 120, left: 160, right: 160 },
        children: text.map(line => new Paragraph({
          spacing: { after: 0 },
          children: [new TextRun({ text: line, font: "Consolas", size: 18 })],
        })),
      })],
    })],
  });
}

function Bullet(text) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}

function BulletRich(runs) {
  return new Paragraph({
    numbering: { reference: "bullets", level: 0 },
    spacing: { after: 80 },
    children: runs,
  });
}

function Numbered(text) {
  return new Paragraph({
    numbering: { reference: "numbers", level: 0 },
    spacing: { after: 80 },
    children: [new TextRun({ text, font: FONT, size: 22 })],
  });
}

function rich(text, opts = {}) {
  return new TextRun({ text, font: FONT, size: 22, bold: !!opts.bold, italics: !!opts.italics, color: opts.color });
}

function cellPara(text, opts = {}) {
  return new Paragraph({
    spacing: { after: 0 },
    alignment: opts.alignment,
    children: [new TextRun({ text, font: FONT, size: 20, bold: !!opts.bold, color: opts.color })],
  });
}

function tableHeaderCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: { fill: "D5E8F0", type: ShadingType.CLEAR },
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [cellPara(text, { bold: true })],
  });
}

function tableCell(text, width, opts = {}) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
    margins: { top: 80, bottom: 80, left: 120, right: 120 },
    children: [cellPara(text, opts)],
  });
}

function makeTable(cols, rows) {
  // cols: array of {label, width}; rows: array of arrays of strings (or {text, opts})
  const totalWidth = cols.reduce((s, c) => s + c.width, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: cols.map(c => c.width),
    rows: [
      new TableRow({
        tableHeader: true,
        children: cols.map(c => tableHeaderCell(c.label, c.width)),
      }),
      ...rows.map(r => new TableRow({
        children: r.map((cell, i) => {
          if (typeof cell === "string") return tableCell(cell, cols[i].width);
          return tableCell(cell.text, cols[i].width, cell.opts || {});
        }),
      })),
    ],
  });
}

const blank = P("");

// --- Content ---------------------------------------------------------------

const titleSection = [
  new Paragraph({
    spacing: { before: 1200, after: 200 },
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Hermes", font: FONT, size: 72, bold: true, color: "0F3057" })],
  }),
  new Paragraph({
    spacing: { after: 800 },
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Bhav Copy Architecture & Delivery Signal Methodology", font: FONT, size: 36, color: "1F4E79" })],
  }),
  new Paragraph({
    spacing: { after: 200 },
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Personal AI Agent on Hostinger VPS (Mumbai)", font: FONT, size: 24, italics: true, color: "555555" })],
  }),
  new Paragraph({
    spacing: { after: 4800 },
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Version 1.0 — Architecture Reference", font: FONT, size: 22, color: "555555" })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
];

const tocSection = [
  H1("Table of Contents"),
  new Paragraph({
    children: [new TextRun({ text: "(Right-click and select \"Update Field\" in Word to populate)", font: FONT, size: 20, italics: true, color: "777777" })],
    spacing: { after: 120 },
  }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-3" }),
  new Paragraph({ children: [new PageBreak()] }),
];

// --- 1. Overview ----------------------------------------------------------

const sec1 = [
  H1("1. Overview"),

  P("Hermes is a personal AI agent running on a Hostinger KVM4 VPS in Mumbai. One of its core responsibilities is daily ingestion of NSE end-of-day equity data, organisation of that data on the VPS, and computation of derived signals that reveal institutional activity in Indian stocks."),

  P("This document captures the architecture of the bhav copy ingestion pipeline and the delivery-value-based signal model used to detect institutional accumulation patterns. The system is designed to:"),

  Bullet("Operate entirely on the user's own VPS — no third-party data hosting"),
  Bullet("Use only free public data sources (NSE archives)"),
  Bullet("Be fully portable — the entire dataset is a single SQLite file plus a folder of raw CSV archives"),
  Bullet("Maintain corporate-action invariance by relying on value-based metrics (rupees) rather than quantity-based metrics (shares)"),
  Bullet("Pre-compute rolling signals nightly so query-time operations are instant and reproducible"),
  Bullet("Cost essentially nothing to operate — no LLM calls in the ingestion or scoring path"),

  blank,
  H2("1.1 Design Goals"),

  P("The pipeline must satisfy five non-negotiable goals:"),

  Numbered("Completeness — capture every column NSE publishes, not just the ones we currently use, so future strategies can leverage the same dataset without re-ingesting."),
  Numbered("Portability — data must be backupable to the user's local hard drive with one command, fully self-contained."),
  Numbered("Idempotency — re-running ingestion must be safe; already-ingested dates are skipped automatically."),
  Numbered("Corporate-action neutrality — comparisons across split and bonus dates must remain meaningful without retrospective adjustment of historical rows."),
  Numbered("Signal precedence — derived signals (rolling averages, power deliveries) must be pre-computed and stored, not computed at query time."),
];

// --- 2. Data Sources ------------------------------------------------------

const sec2 = [
  H1("2. Data Sources"),

  P("NSE publishes equity end-of-day data in multiple formats that have evolved over time. The ingestion pipeline tries them in priority order per trading date and records which source produced each row."),

  H2("2.1 Primary source: sec_bhavdata_full"),

  P("The sec_bhavdata_full CSV is the richest free file NSE publishes. It contains OHLC plus the columns essential for the delivery-value-per-trade signal model:"),

  Code([
    "URL pattern:",
    "  https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_DDMMYYYY.csv",
    "",
    "Sample filename:",
    "  sec_bhavdata_full_28052026.csv",
  ]),

  blank,
  makeTable(
    [{ label: "Column", width: 3000 }, { label: "Meaning", width: 7080 }],
    [
      ["SYMBOL", "NSE ticker symbol"],
      ["SERIES", "EQ, BE, BL, etc. — equity series classification"],
      ["DATE1", "Trade date (DD-MMM-YYYY)"],
      ["PREV_CLOSE / OPEN / HIGH / LOW / CLOSE / LAST / AVG_PRICE", "Price block"],
      ["TTL_TRD_QNTY", "Total traded quantity (volume)"],
      ["TURNOVER_LACS", "Total value traded in lakhs of rupees"],
      ["NO_OF_TRADES", "Number of trade executions for the day"],
      [{ text: "DELIV_QTY", opts: { bold: true } }, { text: "Delivery quantity (key input for institutional signal)", opts: { bold: true } }],
      [{ text: "DELIV_PER", opts: { bold: true } }, { text: "Delivery percentage of total volume", opts: { bold: true } }],
    ]
  ),

  blank,
  H2("2.2 Fallback: UDIFF format (post-July 2024)"),

  P("Around July 2024 NSE migrated to a unified data interchange format (UDIFF). For some dates, sec_bhavdata_full may not be available; the UDIFF bhav copy is then used as a fallback. UDIFF contains OHLC but does not expose DELIV_QTY or DELIV_PER, so rows ingested via this fallback have those columns set to NULL."),

  Code([
    "URL pattern:",
    "  https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip",
  ]),

  blank,
  H2("2.3 Fallback: Legacy bhav copy (pre-July 2024)"),

  P("Older dates fall back to NSE's legacy bhav copy zip. Same shape as UDIFF — OHLC and volume, no delivery columns."),

  Code([
    "URL pattern:",
    "  https://nsearchives.nseindia.com/content/historical/EQUITIES/YYYY/MMM/cmDDMMMYYYYbhav.csv.zip",
    "",
    "Sample filename:",
    "  cm08JAN2024bhav.csv.zip",
  ]),

  blank,
  H2("2.4 Corporate actions"),

  P("Corporate actions (splits, bonuses, dividends, rights) are pulled from separate NSE archive CSVs and stored in their own table. These are used for audit and downstream volume-adjustment logic; signal computation itself uses value-based metrics that are naturally invariant to corporate actions."),

  makeTable(
    [{ label: "Action type", width: 2520 }, { label: "Source URL", width: 7560 }],
    [
      ["BONUS", "https://nsearchives.nseindia.com/content/equities/Bonus_Issue.csv"],
      ["SPLIT", "https://nsearchives.nseindia.com/content/equities/Stock_Split.csv"],
      ["RIGHTS", "https://nsearchives.nseindia.com/content/equities/Rights_Issue.csv"],
      ["DIVIDEND", "https://nsearchives.nseindia.com/content/equities/Dividend.csv"],
    ]
  ),
];

// --- 3. Storage Layout ----------------------------------------------------

const sec3 = [
  H1("3. Storage Layout on the VPS"),

  P("All Hermes data lives in a single root folder. Both the raw NSE files and the parsed SQLite database are kept inside this folder so the entire dataset can be backed up with one command."),

  H2("3.1 Folder structure"),

  Code([
    "/opt/hermes/data/",
    "├── hermes.db                                    ← single SQLite database (all parsed data)",
    "│",
    "└── bhavcopy/                                    ← raw archive (exact bytes from NSE)",
    "    ├── 2022/",
    "    │   ├── JAN/",
    "    │   │   ├── sec_bhavdata_full_03012022.csv",
    "    │   │   ├── sec_bhavdata_full_04012022.csv",
    "    │   │   └── ...",
    "    │   ├── FEB/",
    "    │   └── ...",
    "    ├── 2023/",
    "    ├── 2024/",
    "    ├── 2025/",
    "    └── 2026/",
    "        └── MAY/",
    "            ├── sec_bhavdata_full_27052026.csv",
    "            └── sec_bhavdata_full_28052026.csv",
  ]),

  blank,
  H2("3.2 Why two storage layers"),

  P("The raw archive and the SQLite database serve different roles:"),

  BulletRich([
    rich("Raw archive (CSV / ZIP files): ", { bold: true }),
    rich("an immutable audit trail. If parsing logic changes — for example we choose to extract a column we previously ignored — we can re-parse from the raw archive without re-downloading from NSE."),
  ]),
  BulletRich([
    rich("SQLite database: ", { bold: true }),
    rich("structured, indexed, queryable. The day-to-day signal computation and downstream scoring read from here."),
  ]),

  blank,
  H2("3.3 Disk footprint at 5 years of history"),

  makeTable(
    [{ label: "Component", width: 4200 }, { label: "Size", width: 1800 }, { label: "% of 200 GB VPS disk", width: 4080 }],
    [
      ["Raw CSV archive (5 years × ~250 days/year)", "~900 MB", "~0.45 %"],
      ["bhavcopy_rows table + indexes", "~400 MB", "~0.20 %"],
      ["stock_signals table + indexes", "~280 MB", "~0.14 %"],
      ["corporate_actions table", "<10 MB", "<0.01 %"],
      [{ text: "Total Hermes footprint", opts: { bold: true } }, { text: "~1.6 GB", opts: { bold: true } }, { text: "~0.8 %", opts: { bold: true } }],
    ]
  ),

  blank,
  H2("3.4 Portability — one command takes everything home"),

  P("From the user's Windows laptop the entire Hermes dataset can be backed up to a local folder via SCP:"),

  Code([
    "scp -r root@187.127.173.149:/opt/hermes/data/ D:\\Hermes-data-backup\\",
  ]),

  P("A double-clickable Windows batch file at scripts/download-from-vps.bat performs this download into a date-stamped folder so successive backups are preserved separately."),
];

// --- 4. Database Schema ---------------------------------------------------

const sec4 = [
  H1("4. Database Schema"),

  P("All structured data lives in a single SQLite database at /opt/hermes/data/hermes.db. Four tables and one view form the bhav copy subsystem."),

  H2("4.1 Table: bhavcopy_rows"),

  P("The wide bhav copy storage table. Every column NSE publishes is captured. Columns that are absent in a given source format are stored as NULL. The raw original row is always preserved as a JSON blob for absolute completeness."),

  makeTable(
    [{ label: "Column", width: 3000 }, { label: "Type", width: 1500 }, { label: "Notes", width: 5580 }],
    [
      ["id", "INTEGER PK", "Auto-increment"],
      ["symbol", "TEXT", "NSE ticker"],
      ["trade_date", "TEXT", "ISO YYYY-MM-DD"],
      ["series", "TEXT", "EQ / BE / BL / etc."],
      ["instrument_type, segment", "TEXT", "Used by UDIFF format for derivatives separation"],
      ["open / high / low / close", "REAL", "Daily OHLC"],
      ["last_price / prev_close / avg_price", "REAL", "Additional price points"],
      ["volume, value, num_trades", "INTEGER/REAL", "Total traded quantity, value in rupees, trade count"],
      [{ text: "deliv_qty, deliv_per", opts: { bold: true } }, { text: "INTEGER/REAL", opts: { bold: true } }, { text: "Delivery quantity and percentage (NULL for fallback sources)", opts: { bold: true } }],
      ["isin", "TEXT", "Where available"],
      ["format_version", "TEXT", "sec_bhavdata_full / udiff / legacy"],
      ["raw_json", "TEXT", "Original CSV row as JSON — fallback for any column"],
    ]
  ),

  P("Unique constraint: (symbol, trade_date, series, instrument_type) — prevents duplicate insertion on idempotent re-runs."),
  P("Indexes: (symbol, trade_date), (trade_date), (series) for typical query patterns."),

  blank,
  H2("4.2 Table: corporate_actions"),

  P("Captured for cross-period interpretation. The signal layer itself uses value-based metrics that don't need adjustment, but this table is essential for any future strategy that touches volume comparisons across action dates."),

  makeTable(
    [{ label: "Column", width: 2640 }, { label: "Notes", width: 7440 }],
    [
      ["symbol", "NSE ticker"],
      ["action_type", "BONUS / SPLIT / RIGHTS / DIVIDEND / MERGER"],
      ["ex_date / record_date", "Effective and record dates"],
      ["ratio_from / ratio_to", "Parsed ratio where possible — e.g. SPLIT 10→1 means each ₹10 face-value share became ten ₹1 shares"],
      ["details", "Original NSE purpose text"],
      ["source", "Which NSE CSV the action was sourced from"],
    ]
  ),

  blank,
  H2("4.3 Table: stock_signals"),

  P("Pre-computed nightly. One row per (symbol, trade_date). Contains today's delivery-value-per-trade plus all rolling baselines and ratios. Queries become instant lookups."),

  makeTable(
    [{ label: "Column group", width: 3600 }, { label: "Contents", width: 6480 }],
    [
      ["Today's values", "delivery_value_today, total_value_today, delivery_value_per_trade"],
      ["Flat rolling averages (excl. today)", "avg_dvpt_5d, _10d, _30d, _60d, _90d, _180d, _365d"],
      ["Power deliveries (top-N within window)", "power_dvpt_1m, _2m, _3m, _6m"],
      ["Ratio signals (today vs baseline)", "ratio_today_vs_avg_30d, ratio_today_vs_power_1m, ratio_today_vs_power_3m"],
      ["Metadata", "data_points_used, computed_at"],
    ]
  ),

  P("Primary key: (symbol, trade_date). Indexes on trade_date and on (trade_date, ratio_today_vs_power_1m DESC) for fast top-N queries."),

  blank,
  H2("4.4 Table: bhavcopy_dates"),

  P("One row per ingested trading date. Records the format version used (sec_bhavdata_full / udiff / legacy), the row count, and whether delivery data was captured. Used by the puller to skip dates already done — making the entire backfill idempotent and resumable."),

  blank,
  H2("4.5 View: prices_eq"),

  P("A convenience view of bhavcopy_rows filtered to equity cash market only, exposing the columns most strategies actually use. Lets downstream code query a clean equity feed without re-stating the filters."),

  Code([
    "CREATE VIEW prices_eq AS",
    "SELECT symbol, trade_date, open, high, low, close, prev_close,",
    "       avg_price, volume, value, num_trades, deliv_qty, deliv_per, isin",
    "FROM bhavcopy_rows",
    "WHERE series = 'EQ' AND (segment = 'CM' OR segment IS NULL);",
  ]),
];

// --- 5. Delivery Value Per Trade -----------------------------------------

const sec5 = [
  H1("5. Delivery Value Per Trade — The Core Metric"),

  H2("5.1 Definition"),

  P("Delivery Value Per Trade (DVPT) for a stock on a given trading date is computed as:"),

  Code([
    "DVPT_today = (DELIV_QTY_today × CLOSE_today) ÷ NO_OF_TRADES_today",
    "           = average rupees of delivery flowing through each trade",
  ]),

  P("DVPT is denominated in rupees per trade. The interpretation is: when delivery activity is concentrated in fewer, larger trades, DVPT rises — which is the fingerprint of an institutional participant taking a position. When delivery activity is fragmented across many small trades, DVPT falls — which is consistent with retail participation."),

  blank,
  H2("5.2 Why per-trade matters more than total delivery"),

  P("Total delivery value alone is misleading. A high delivery value can result from:"),

  Bullet("A small number of large institutional trades — a strong positioning signal"),
  Bullet("A large number of small retail trades — distribution noise rather than positioning"),

  P("These two scenarios produce the same total delivery value but tell completely different stories about who is on each side of the trades. Per-trade delivery value separates them."),

  blank,
  H2("5.3 Worked example"),

  P("Consider two stocks reporting identical end-of-day delivery values of ₹8 lakhs each:"),

  makeTable(
    [{ label: "Metric", width: 3360 }, { label: "Stock A (retail churn)", width: 3360 }, { label: "Stock B (institutional)", width: 3360 }],
    [
      ["Total delivery value", "₹8,00,000", "₹8,00,000"],
      ["Number of trades", "1,000", "50"],
      [{ text: "DVPT (per-trade delivery value)", opts: { bold: true } }, { text: "₹800", opts: { bold: true } }, { text: "₹16,000", opts: { bold: true } }],
    ]
  ),

  P("Same total delivery, but Stock B's delivery is flowing through trades that are 20× larger. Stock B reflects a small number of large participants taking delivery — a much more meaningful signal than Stock A's retail churn."),

  blank,
  H2("5.4 Important caveat: trade count is for all trades"),

  P("NSE does not separately publish the number of delivery-only trades. NO_OF_TRADES is the count of all executions on the day, including intraday trades that did not result in delivery. The DVPT formula therefore uses this combined count as the denominator."),

  P("In practice this approximation captures the user's intended signal well. When delivery rises and trade count remains the same or falls — that combination signals institutional activity, regardless of whether intraday trades inflated the denominator."),
];

// --- 6. Signal Methodology -----------------------------------------------

const sec6 = [
  H1("6. Signal Methodology — Power Deliveries and Flat Baselines"),

  P("DVPT for a single day is noisy. The signal layer therefore compares today's DVPT to two kinds of baseline computed from the stock's own recent history."),

  H2("6.1 Flat rolling averages — the regular baseline"),

  P("A plain mean of DVPT over each of these trailing windows, excluding today:"),

  Bullet("5 trading days (~1 week)"),
  Bullet("10 trading days (~2 weeks)"),
  Bullet("30 trading days (~1 month)"),
  Bullet("60, 90, 180, 365 trading days"),

  P("These give the user's required overall picture of where a stock has been operating in terms of delivery intensity. They are easy to reason about but tend to be diluted by the many noise days that sit between genuine institutional events."),

  blank,
  H2("6.2 Power deliveries — the high-conviction baseline"),

  P("The user's insight: institutional buying does not happen evenly. A few exceptional days dominate. A flat average masks them. To preserve the signal, the system computes the average of the top-N DVPT values within each window:"),

  makeTable(
    [{ label: "Window", width: 2520 }, { label: "Trading days", width: 1920 }, { label: "Top-N", width: 1440 }, { label: "Effective percentile", width: 4200 }],
    [
      ["1 month", "22", "5", "≈ 77th percentile"],
      ["2 months", "44", "10", "≈ 77th percentile"],
      ["3 months", "66", "15", "≈ 77th percentile"],
      ["6 months", "132", "40", "≈ 70th percentile"],
    ]
  ),

  P("The 1m / 2m / 3m windows preserve a consistent ~P77 sampling rate. The 6m window relaxes slightly to ~P70 because over a longer span you want a fuller set of institutional events captured, not just the rarest peaks."),

  blank,
  H2("6.3 Ratio signals — what we actually act on"),

  P("Three ratios are pre-computed per (symbol, trade_date) to give an immediate read on today's activity:"),

  makeTable(
    [{ label: "Ratio", width: 4080 }, { label: "Numerator / Denominator", width: 6000 }],
    [
      ["ratio_today_vs_avg_30d", "DVPT_today ÷ avg_dvpt_30d (today vs. the regular 30-day baseline)"],
      ["ratio_today_vs_power_1m", "DVPT_today ÷ power_dvpt_1m (today vs. the recent institutional baseline)"],
      ["ratio_today_vs_power_3m", "DVPT_today ÷ power_dvpt_3m (today vs. the slower institutional baseline)"],
    ]
  ),

  blank,
  H2("6.4 Interpretation guide for ratio_today_vs_power_1m"),

  makeTable(
    [{ label: "Reading", width: 2400 }, { label: "Interpretation", width: 7680 }],
    [
      [{ text: "< 0.30", opts: { color: "888888" } }, "Today's per-trade delivery is well below recent institutional levels — quiet"],
      [{ text: "0.30 – 0.70", opts: { color: "888888" } }, "Normal day"],
      [{ text: "0.70 – 1.00", opts: { color: "888888" } }, "Approaching institutional intensity"],
      [{ text: "> 1.00", opts: { bold: true, color: "0A6E2E" } }, { text: "Today equals or exceeds the average of the recent month's institutional buying days — high-conviction signal", opts: { bold: true } }],
      [{ text: "> 1.50", opts: { bold: true, color: "0A6E2E" } }, { text: "Today exceeds even the recent peak institutional buying days — exceptional", opts: { bold: true } }],
    ]
  ),
];

// --- 7. Corporate-action invariance --------------------------------------

const sec7 = [
  H1("7. Corporate-Action Invariance"),

  P("A central design choice: raw bhav copy data is stored unadjusted. Historical rows are never modified after ingestion. Corporate actions are stored separately. All signal-layer metrics use rupee values, not share quantities, so corporate actions become invisible to the signal calculation."),

  H2("7.1 Why value-based metrics are invariant"),

  P("Consider a 1:5 stock split that happens on day N. After the split:"),

  Bullet("Share count multiplies by 5"),
  Bullet("Closing price divides by 5"),
  Bullet("DELIV_QTY (a quantity) increases by a factor that depends on the split timing — distorted across day N"),
  Bullet("DELIV_QTY × CLOSE (a rupee value) stays the same — invariant"),

  P("Because DVPT is built from (DELIV_QTY × CLOSE), the metric naturally stays comparable across the split date. The same property holds for bonuses and other quantity-altering actions."),

  blank,
  H2("7.2 What this lets us avoid"),

  P("Most retail platforms store \"adjusted close\" and back-adjust historical quantities. That approach has two problems:"),

  Bullet("History is mutable — yesterday's reported metric changes whenever a new corporate action lands. Reproducibility is broken."),
  Bullet("Adjustment factors compound silently over multiple actions, introducing rounding drift in long backtests."),

  P("By keeping raw data immutable and choosing metrics that are inherently corporate-action neutral, we sidestep both issues. The corporate_actions table is still maintained, but is consulted only for the rare strategy that explicitly needs quantity comparisons."),
];

// --- 8. Nightly compute flow ---------------------------------------------

const sec8 = [
  H1("8. Nightly Compute Flow"),

  P("Each weekday after the market closes, four jobs run in sequence. All four are managed by systemd timers on the VPS and can be invoked manually for one-off runs."),

  H2("8.1 The sequence"),

  Numbered("Bhav copy ingestion (≈ 5:30 PM IST) — pulls today's sec_bhavdata_full CSV from NSE, archives the raw file under /opt/hermes/data/bhavcopy/YYYY/MMM/, parses every column, and inserts into bhavcopy_rows. Idempotent — running again the same day is a no-op."),
  Numbered("Corporate actions refresh — fetches the current Bonus_Issue, Stock_Split, Rights_Issue and Dividend CSVs from NSE archives. Upserts into corporate_actions. Cheap (≈ 30 seconds)."),
  Numbered("Signal computation — for each stock that traded today, reads the last 365 trading days of (deliv_qty, close, no_of_trades), computes today's DVPT plus all rolling averages, power deliveries and ratios, and writes one row into stock_signals. Historical rows in stock_signals are never recomputed — they remain frozen as originally calculated."),
  Numbered("Digest (optional, twice daily) — reads pending stock_signals rows where the ratio_today_vs_power_1m exceeds a threshold and posts a structured Telegram message to the user's analysis group."),

  blank,
  H2("8.2 Why pre-compute rather than compute at query time"),

  makeTable(
    [{ label: "Aspect", width: 2880 }, { label: "Pre-computed (chosen)", width: 3600 }, { label: "Computed at query time", width: 3600 }],
    [
      ["Per-query latency", "~10 ms (single SELECT)", "~2 s (per-stock window scan)"],
      ["Reproducibility", "Yesterday's reading is fixed forever", "Result depends on what is in the table when queried"],
      ["Storage cost", "~280 MB for 5 years × 2,000 stocks", "0"],
      ["Compute cost", "~5–10 min per night, once", "Repeated on every query"],
      ["Suitability for scoring batch", "Excellent", "Slows everything down"],
    ]
  ),

  blank,
  H2("8.3 The 5-year initial backfill"),

  P("On first install, a one-shot backfill walks every weekday in the last ~1,830 calendar days. Each request to NSE is followed by a 1.5 second pause to be polite and stay below any rate-limit threshold. Total runtime is approximately:"),

  makeTable(
    [{ label: "Phase", width: 4200 }, { label: "Estimated time", width: 2940 }, { label: "Bandwidth", width: 2940 }],
    [
      ["Bhav copy backfill (~1,250 trading days)", "30 – 40 min", "~900 MB inbound"],
      ["Corporate actions fetch", "~30 sec", "<5 MB inbound"],
      ["Signal computation across full history", "10 – 15 min", "0 (local compute)"],
      [{ text: "Total", opts: { bold: true } }, { text: "~45 – 60 min", opts: { bold: true } }, { text: "~900 MB", opts: { bold: true } }],
    ]
  ),

  P("The backfill is invoked via scripts/full-backfill.sh and can be run in the background — the user may disconnect from SSH and let it complete on its own. Progress is tailable through /var/log/hermes-backfill.log."),
];

// --- 9. Operational reference --------------------------------------------

const sec9 = [
  H1("9. Operational Reference"),

  H2("9.1 Key commands on the VPS"),

  makeTable(
    [{ label: "Purpose", width: 3600 }, { label: "Command", width: 6480 }],
    [
      ["Most recent bhav copy", "python -m src.automation.bhavcopy"],
      ["Backfill 5 years", "python -m src.automation.bhavcopy --backfill 1830"],
      ["Ingest a specific date", "python -m src.automation.bhavcopy --date 2024-01-08"],
      ["Pull all corporate actions", "python -m src.automation.corp_actions"],
      ["Compute today's signals", "python -m src.automation.signals"],
      ["Backfill all historical signals", "python -m src.automation.signals --backfill"],
      ["Full backfill orchestration", "bash /opt/hermes/scripts/full-backfill.sh"],
    ]
  ),

  blank,
  H2("9.2 Useful SQL queries"),

  P("Top institutional candidates today (ratio > 1.5×):"),
  Code([
    "SELECT symbol,",
    "       ROUND(delivery_value_per_trade) AS dvpt_today,",
    "       ROUND(power_dvpt_1m) AS power_1m,",
    "       ROUND(ratio_today_vs_power_1m, 2) AS ratio",
    "FROM stock_signals",
    "WHERE trade_date = (SELECT MAX(trade_date) FROM stock_signals)",
    "  AND ratio_today_vs_power_1m > 1.5",
    "ORDER BY ratio DESC",
    "LIMIT 20;",
  ]),

  blank,
  P("Signal history for a specific stock:"),
  Code([
    "SELECT trade_date,",
    "       ROUND(delivery_value_per_trade) AS dvpt,",
    "       ROUND(ratio_today_vs_power_1m, 2) AS ratio_1m",
    "FROM stock_signals WHERE symbol = 'RELIANCE'",
    "ORDER BY trade_date DESC LIMIT 30;",
  ]),

  blank,
  P("Corporate action history for a stock:"),
  Code([
    "SELECT action_type, ex_date, ratio_from, ratio_to, details",
    "FROM corporate_actions WHERE symbol = 'TATAMOTORS'",
    "ORDER BY ex_date DESC;",
  ]),

  blank,
  H2("9.3 Backup to local hard drive"),

  P("From the user's Windows laptop:"),
  Code([
    "scp -r root@187.127.173.149:/opt/hermes/data/ D:\\Hermes-data-backup\\",
  ]),

  P("Or use the prepared batch file at D:\\Hermes\\scripts\\download-from-vps.bat which creates a timestamped subfolder for each backup."),

  blank,
  H2("9.4 Inspecting the data locally"),

  P("The downloaded hermes.db file is a single SQLite database. Three convenient ways to open it:"),

  BulletRich([rich("DB Browser for SQLite — ", { bold: true }), rich("free GUI at https://sqlitebrowser.org/. Point-and-click queries; CSV / Excel export.")]),
  BulletRich([rich("Python with pandas — ", { bold: true }), rich("pd.read_sql('SELECT * FROM stock_signals WHERE symbol=\"RELIANCE\"', sqlite3.connect('hermes.db'))")]),
  BulletRich([rich("Excel via DB Browser export — ", { bold: true }), rich("any table or query result can be exported to CSV and opened directly in Excel.")]),
];

// --- 10. Closing notes ----------------------------------------------------

const sec10 = [
  H1("10. Operating Philosophy"),

  P("Three principles guide the system's design and should be preserved as the architecture evolves:"),

  Numbered("Free public data only. The pipeline relies entirely on NSE's free archive. If a future strategy requires paid data, that is an explicit, separate decision with explicit, separate cost."),
  Numbered("Pre-computation over recomputation. Anything that can be computed once and stored should be. This keeps query-time work negligible and makes results historically reproducible."),
  Numbered("Value over quantity. Wherever a choice exists between a quantity-based metric and a value-based metric, the value-based one is chosen. This eliminates corporate-action adjustment as a class of bug."),

  blank,
  P("The bhav copy subsystem is foundational: it produces a clean, complete, locally-owned record of Indian equity end-of-day activity and a small set of derived signals that capture institutional positioning. Everything else the user might build — fundamental scoring, multi-strategy backtests, alert rules, dashboards — sits on top of this layer."),
];

// --- Assemble document ----------------------------------------------------

const doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 36, bold: true, color: "0F3057" },
        paragraph: { spacing: { before: 320, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 28, bold: true, color: "0F3057" },
        paragraph: { spacing: { before: 260, after: 140 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 24, bold: true, color: "1F4E79" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_WIDTH, height: PAGE_HEIGHT },
        margin: { top: MARGIN, right: MARGIN, bottom: MARGIN, left: MARGIN },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "Hermes — Bhav Copy Architecture v1.0", font: FONT, size: 18, color: "888888" })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Page ", font: FONT, size: 18, color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 18, color: "888888" }),
            new TextRun({ text: " of ", font: FONT, size: 18, color: "888888" }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 18, color: "888888" }),
          ],
        })],
      }),
    },
    children: [
      ...titleSection,
      ...tocSection,
      ...sec1, new Paragraph({ children: [new PageBreak()] }),
      ...sec2, new Paragraph({ children: [new PageBreak()] }),
      ...sec3, new Paragraph({ children: [new PageBreak()] }),
      ...sec4, new Paragraph({ children: [new PageBreak()] }),
      ...sec5, new Paragraph({ children: [new PageBreak()] }),
      ...sec6, new Paragraph({ children: [new PageBreak()] }),
      ...sec7, new Paragraph({ children: [new PageBreak()] }),
      ...sec8, new Paragraph({ children: [new PageBreak()] }),
      ...sec9, new Paragraph({ children: [new PageBreak()] }),
      ...sec10,
    ],
  }],
});

const out = path.join(__dirname, "hermes-bhavcopy-architecture.docx");
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(out, buf);
  console.log("wrote " + out + " (" + buf.length + " bytes)");
}).catch(err => {
  console.error("docx generation failed:", err);
  process.exit(1);
});
