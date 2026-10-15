#!/usr/bin/env python3
"""Builds the report with correct page numbers in the TOC, List of Figures and List of Tables.

1. node build_report.js            -> draft .docx (page numbers 00)
2. LibreOffice renders it to PDF   -> find the page of every heading and caption
3. node build_report.js pages.json -> final .docx, rendered again to check

The TOC and lists are real Word fields, so after editing in Word they can be
refreshed with right-click > Update Field > Update entire table.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
FULL = os.path.exists(os.path.join(HERE, "..", "chapter5", "chapter5.json"))
OUT = os.path.join(HERE, "ISproject_Esborn_Kihiu_Ch1-6.docx" if FULL else "ISproject_Esborn_Kihiu_Ch1-4.docx")
PAGES = os.path.join(HERE, "pages.json")

INSTR = {
    "TOC": ' TOC \\o "1-3" \\h \\z \\u ',
    "LOF": ' TOC \\h \\z \\t "Figure Caption,1" ',
    "LOT": ' TOC \\h \\z \\t "Table Caption,1" ',
}
RUN = r'<w:r>(?:<w:rPr>(?:(?!</w:rPr>).)*</w:rPr>)?<w:t(?: [^>]*)?>@@{}@@</w:t></w:r>'


def add_fields(path):
    """Replace the @@FB_x@@ / @@FE@@ marker runs with Word field characters."""
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                xml = data.decode("utf-8")
                for kind, instr in INSTR.items():
                    begin = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                             f'<w:r><w:instrText xml:space="preserve">{instr}</w:instrText></w:r>'
                             '<w:r><w:fldChar w:fldCharType="separate"/></w:r>')
                    xml, n = re.subn(RUN.format("FB_" + kind), lambda m: begin, xml, count=1, flags=re.S)
                    assert n == 1, kind
                xml, n = re.subn(RUN.format("FE"), '<w:r><w:fldChar w:fldCharType="end"/></w:r>', xml, flags=re.S)
                assert n == 3, n
                data = xml.encode("utf-8")
            zout.writestr(item, data)
    os.replace(tmp, path)


def build(pages_json=None):
    args = ["node", os.path.join(HERE, "build_report.js")]
    args += [pages_json or "-", OUT]
    subprocess.run(args, check=True)
    add_fields(OUT)


def render():
    d = tempfile.mkdtemp()
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", d, OUT],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pdf = os.path.join(d, os.path.basename(OUT).replace(".docx", ".pdf"))
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    pages = []
    for i in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(i), "-l", str(i), pdf, "-"],
                           capture_output=True, text=True).stdout
        pages.append([re.sub(r"\s+", " ", l).strip() for l in t.splitlines()])
    return pdf, pages


def roman(n):
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    s = ""
    for v, r in vals:
        while n >= v:
            s += r
            n -= v
    return s


def find_pages(pages):
    keys = json.load(open(os.path.join(HERE, "toc_keys.json")))
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    # chapter 1 starts the arabic numbering
    ch1 = next(i for i, p in enumerate(pages) if "Chapter 1: Introduction" in p)
    label = lambda i: roman(i + 1) if i < ch1 else str(i - ch1 + 1)
    result, missing = {}, []
    pos = 1
    for t in keys["toc"]:
        hit = next((i for i in range(pos, len(pages)) if norm(t) in pages[i]), None)
        if hit is None:
            missing.append(t)
            continue
        result["toc:" + t] = label(hit)
        pos = hit
    start = ch1
    for c in keys["figs"] + keys["tabs"]:
        hit = next((i for i in range(start, len(pages)) if norm(c) in pages[i] or norm(c) in " ".join(pages[i])), None)
        if hit is None:
            missing.append(c)
            continue
        result["cap:" + c] = label(hit)
    return result, missing


def main():
    build()
    prev = None
    for attempt in range(3):
        pdf, pages = render()
        found, missing = find_pages(pages)
        if missing:
            print("NOT FOUND:", *missing, sep="\n  ")
        if found == prev:
            break
        json.dump(found, open(PAGES, "w"), indent=1)
        build(PAGES)
        prev = found
    pdf, pages = render()
    shutil.copy(pdf, OUT.replace(".docx", ".pdf"))
    print("pages:", len(pages), "->", OUT.replace(".docx", ".pdf"))


if __name__ == "__main__":
    main()
