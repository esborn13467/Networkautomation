// Builds docs/slides/Speaker_Notes.docx from the deck source: one labelled section per slide,
// in deck order, with the slide's title and its speaker notes (the <aside> of each slide).
//   node docs/slides/build_notes.js
const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Footer, PageNumber, BorderStyle } =
  require(path.join(__dirname, "..", "node_modules", "docx"));

const DECK = path.join(__dirname, "project");
const deck = JSON.parse(fs.readFileSync(path.join(DECK, "deck.json"), "utf8"));
const clean = (s) => s.replace(/<br\s*\/?>/g, " ").replace(/<[^>]+>/g, "").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
  .replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();

const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "Speaker Notes", bold: true, size: 40, font: "Times New Roman" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
    children: [new TextRun({ text: "A Zero Trust Network with Automated Threat Detection and Response using Isolation Forest", italics: true, size: 24, font: "Times New Roman" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
    children: [new TextRun({ text: `Esborn Kihiu · ${deck.order.length} slides`, size: 22, font: "Times New Roman" })] }),
];

deck.order.forEach((id, i) => {
  const html = fs.readFileSync(path.join(DECK, "slides", `${id}.html`), "utf8");
  const title = clean((html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/) || html.match(/<h2[^>]*>([\s\S]*?)<\/h2>/) || ["", id])[1]);
  const notes = clean((html.match(/<aside>([\s\S]*?)<\/aside>/) || ["", "(no notes)"])[1]);
  body.push(
    new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 80 },
      border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "BFBFBF", space: 4 } },
      children: [new TextRun({ text: `Slide ${i + 1}: ${title}`, bold: true, size: 26, font: "Times New Roman", color: "0F1E2B" })] }),
    new Paragraph({ spacing: { after: 160, line: 360 }, alignment: AlignmentType.JUSTIFIED,
      children: [new TextRun({ text: notes, size: 24, font: "Times New Roman" })] }),
  );
});

const doc = new Document({
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
      children: [new TextRun({ children: [PageNumber.CURRENT], size: 20, font: "Times New Roman" })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then((b) => {
  const out = path.join(__dirname, "Speaker_Notes.docx");
  fs.writeFileSync(out, b);
  console.log("wrote", out, `(${deck.order.length} slides)`);
});
