// Turns docs/guide/guide.md into docs/guide/How_My_Project_Works.docx
//   node docs/guide/build_guide.js
// Supports: # ## ### headings, paragraphs with **bold** and `code`, "- " bullets,
// "1. " numbered steps, ``` code blocks ```, | tables |, and "> " note boxes.
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber, TableOfContents } =
  require(path.join(__dirname, "..", "node_modules", "docx"));

const SRC = path.join(__dirname, "guide.md");
const OUT = path.join(__dirname, "How_My_Project_Works.docx");
const W = 9360;                       // US Letter text width, 1" margins (DXA)
const FONT = "Calibri", MONO = "Consolas", ACCENT = "1F4E79";

function runs(text, base = {}) {
  const out = [];
  text.split(/(\*\*[^*]+\*\*|`[^`]+`)/).forEach((p) => {
    if (!p) return;
    if (p.startsWith("**")) out.push(new TextRun({ text: p.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (p.startsWith("`")) out.push(new TextRun({ text: p.slice(1, -1), font: MONO, size: 20, color: "8B1A1A", ...base }));
    else out.push(new TextRun({ text: p, font: FONT, ...base }));
  });
  return out;
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

function table(rows) {
  const cells = rows.map((r) => r.replace(/^\||\|$/g, "").split("|").map((c) => c.trim()));
  const head = cells[0], body = cells.slice(2);          // row 1 = header, row 2 = |---|
  const n = head.length;
  const widths = Array(n).fill(Math.floor(W / n));
  widths[n - 1] += W - widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, isHead) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders,
    shading: isHead ? { type: ShadingType.CLEAR, fill: "DCE6F1", color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: runs(t, isHead ? { bold: true, size: 20 } : { size: 20 }) })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, i, true)) }),
      ...body.map((r) => new TableRow({ children: r.map((t, i) => cell(t, i, false)) }))],
  });
}

const lines = fs.readFileSync(SRC, "utf8").split("\n");
const body = [];
let i = 0, numbered = 0;
while (i < lines.length) {
  const l = lines[i];
  if (l.startsWith("```")) {                                  // code block
    const code = [];
    for (i++; i < lines.length && !lines[i].startsWith("```"); i++) code.push(lines[i]);
    code.forEach((c, k) => body.push(new Paragraph({
      shading: { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" }, indent: { left: 240 },
      spacing: { after: k === code.length - 1 ? 160 : 0 },
      children: [new TextRun({ text: c || " ", font: MONO, size: 19 })] })));
    i++; continue;
  }
  if (l.startsWith("|")) {                                    // table
    const t = [];
    while (i < lines.length && lines[i].startsWith("|")) t.push(lines[i++]);
    body.push(table(t), new Paragraph({ children: [], spacing: { after: 120 } }));
    continue;
  }
  if (l.startsWith("# ")) body.push(new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: body.length > 6,
    children: [new TextRun({ text: l.slice(2), font: FONT })] }));
  else if (l.startsWith("## ")) { numbered++; body.push(new Paragraph({ heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text: l.slice(3), font: FONT })] })); }
  else if (l.startsWith("### ")) body.push(new Paragraph({ heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text: l.slice(4), font: FONT })] }));
  else if (l.startsWith("> ")) body.push(new Paragraph({ spacing: { before: 60, after: 120 },
    shading: { type: ShadingType.CLEAR, fill: "FFF4D6", color: "auto" },
    border: { left: { style: BorderStyle.SINGLE, size: 18, color: "E3A13B", space: 6 } },
    children: runs(l.slice(2)) }));
  else if (/^- /.test(l)) body.push(new Paragraph({ numbering: { reference: "bullets", level: 0 },
    spacing: { after: 60 }, children: runs(l.slice(2)) }));
  else if (/^\d+\. /.test(l)) body.push(new Paragraph({ numbering: { reference: `steps${numbered}`, level: 0 },
    spacing: { after: 60 }, children: runs(l.replace(/^\d+\. /, "")) }));
  else if (l.trim()) body.push(new Paragraph({ spacing: { after: 120 }, children: runs(l) }));
  i++;
}

const doc = new Document({
  creator: "Esborn Kihiu", title: "How My Project Works",
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 36, bold: true, color: ACCENT, font: FONT }, paragraph: { spacing: { before: 240, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, color: ACCENT, font: FONT }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, color: "404040", font: FONT }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: { config: [
    { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    ...Array.from({ length: 80 }, (_, k) => ({ reference: `steps${k}`, levels: [{ level: 0, format: LevelFormat.DECIMAL,
      text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] })),
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] }) },
    children: [
      new Paragraph({ spacing: { before: 2400 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "How My Project Works", bold: true, size: 56, color: ACCENT, font: FONT })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
        children: [new TextRun({ text: "A plain-language guide and hands-on exercises", size: 28, font: FONT })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 1200 },
        children: [new TextRun({ text: "Zero Trust Network with Automated Threat Detection and Response · Esborn Kihiu", italics: true, size: 22, font: FONT })] }),
      new Paragraph({ children: [new TextRun({ text: "Contents", bold: true, size: 28, color: ACCENT, font: FONT })] }),
      new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-2" }),
      new Paragraph({ children: [new TextRun({ text: "(In Word: right-click the contents and choose Update Field to fill in page numbers.)", italics: true, size: 18, font: FONT })] }),
      ...body,
    ],
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); console.log("wrote", OUT); });
