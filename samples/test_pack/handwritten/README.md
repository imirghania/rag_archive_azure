# Handwritten test pack

Official-looking blank paper, texts to copy by hand, an answer key and test questions. You write the texts on the paper, scan the pages, upload them as dossiers and ask the questions.

**Real handwriting needs the Azure deployment.** The local runtime has canned fixtures instead of OCR and cannot read your handwriting (see `samples/templates/README.md`, "Read this first"). All names, numbers and organisations here are invented.

## What is in this folder

| Path | What it is | Upload it? |
| --- | --- | --- |
| `sheets/HWnn_<design>.pdf` and `.png` | 17 prepared blank sheets, one per text. Each has its own printed title and `Ref:` number. Print these | **Yes, after you write on them** |
| `paper/blank_<design>.pdf` and `.png` | The 11 generic designs (same paper, generic title and Ref `...-0001`). For printing extra copies or writing your own text | Yes, after writing |
| `TEXTS_TO_WRITE.pdf` / `.md` | The 17 texts to copy (large type, Arabic right to left). Each says which sheet to use | **No** |
| `answer_key.md` | Exact text of every item (ground truth) | **No** |
| `questions.md` | Test questions per dossier, with expected answers | **No** |
| `preview_filled/PREVIEW_*.png` | Simulated handwriting, only to show the intended look | **No** |
| `paper/layout.json` | Machine-readable positions of rules and boxes (used by the preview generator) | **No** |

Never upload a text file, the answer key, a preview, `layout.json` or any `dossier.json`.

## The designs

Letterhead English (`letterhead_en`), Arabic with right-to-left header (`letterhead_ar`), bilingual (`letterhead_bi`); internal memorandum English and mirrored Arabic (`memo_en`, `memo_ar`); government-style correspondence sheet with crest placeholder, outgoing-number and date boxes (`gov`); numbered payment voucher with amount box and signature lines (`voucher`); formal ruled sheet with a right margin column (`formal_ruled`); bordered certificate/statement sheet (`certificate`); meeting-minutes sheet (`minutes`); HR employment letterhead (`hr_employment`). Finance sheets are navy, HR sheets are green.

Every sheet has a printed title in capitals (Arabic sheets also have the Arabic title above it), a printed `Ref:` line, light-grey ruled lines 9.5 mm apart, and a printed footer. No handwriting-like font is used on the paper. The system cuts a dossier into documents with the title and `Ref:`, so leave them alone.

Some sheets have printed boxes (memo TO/FROM/DATE/SUBJECT, government outgoing number and date, voucher date, payee, amount and amount in words, minutes date, time, venue and attendees). `TEXTS_TO_WRITE` lists what to write in them. The three voucher signature lines: sign with an invented squiggle.

## 1. Print

1. Print the sheets you need from `sheets/` on A4. One sheet per page, one sheet per text.
2. In the print dialog choose **Actual size** or **100%**. Never "Fit to page": the rules are sized for 300 dpi at real size.
3. Black and white is fine. Single-sided.

## 2. Write

- Black or dark blue ballpoint or gel pen. No pencil, no highlighter.
- Write naturally, in your usual handwriting. Do not copy neatly. That is the point of the test.
- Leave the printed title and `Ref:` untouched. Write inside the ruled area (and the printed boxes). Do not write over printed text.
- One text per sheet. Every text fits one sheet. The line counts in `TEXTS_TO_WRITE` are estimates.
- Arabic: write right to left, joined letters, as you normally do. Digits as shown in the text (some Arabic texts mix Western and Arabic-Indic digits).
- HW14 has one deliberate crossed-out correction and HW15 a margin note. Follow the instruction printed in the text exactly.
- Do not add real personal data.

## 3. Scan

- Flatbed: 300 dpi, grayscale (or black and white), TIFF or PDF.
- Phone: use a scanner app, grayscale, flat cropped PDF, all four corners visible, even light.
- One page per scan, or one multi-page TIFF/PDF per dossier in page order. A multi-page file keeps the order certain.

## 4. Group the scans into dossiers

Make one folder per dossier. The folder name is the dossier ID (format `<DEPT>-C<2 digits>-S<1 digit>-F<4 digits>`, checked against `src/docai/contracts/keys.py`). Put the scans of its texts in the order listed.

| Dossier folder | Department | Texts (in this order) | Theme |
| --- | --- | --- | --- |
| `FIN-C95-S1-F0001` | Finance | HW02, HW03, HW04, HW16 | Letters and requests, English and Arabic |
| `FIN-C95-S1-F0002` | Finance | HW06, HW08, HW12, HW13 | Mixed notes, receipt, bank transfer, digits |
| `FIN-C96-S1-F0001` | Finance | HW09, HW10, HW14 | Minutes, clause, crossed-out correction |
| `HR-C95-S1-F0001` | HR | HW01, HW05, HW11 | Resignation, leave request, employment letter |
| `HR-C96-S1-F0001` | HR | HW07, HW15, HW17 | Onboarding note, margin note, Arabic minutes |

Optional manifest like the one in `samples/templates/filled/FIN-C99-S1-F0001/`:

```bash
uv run python samples/test_pack/tools/handwritten/dossier_json.py path/to/FIN-C95-S1-F0001
```

It writes `dossier.json` (name, bytes, sha256, pages of each scan) into the folder. It is for your records. The web app makes its own manifest, so never select `dossier.json` when uploading.

## 5. Upload

Use the deployed web app (Azure, Entra sign-in) as in `docs/running-on-azure.md`, or the local dev server if you only want to see the screens (locally your own scans fail with `no OCR fixture`).

1. Open the web app and sign in as **sara** (Expert, Finance). Locally: `http://localhost:8000`, button **sara**.
2. Click **Upload**. Choose **Department** `FIN` for the three `FIN-...` dossiers, mode `By dossier`.
3. Type the dossier ID (the folder name). Choose the scan file(s) of that folder only. Click **Check files**, then **Confirm and upload**.
4. Wait until the dossier shows `completed` (a minute or more on Azure). Lines where the two readers disagree become review tasks for Sara under **Review**.
5. HR dossiers (`HR-...`): choose **Department** `HR`. Sara is documented as a Finance expert only, so the upload may be refused. In that case you need a user with HR upload rights; this was not checked here.
6. Ask the questions of `questions.md` as a reader (`layla` for Finance, `huda` for HR) and compare with the expected answers and `answer_key.md`.

Cost: one OCR call per page and one vision call per handwritten line. Start with one dossier.

## Regenerate

```bash
uv run python samples/test_pack/tools/handwritten/make_all.py      # paper, texts, previews (about 40 s)
uv run python samples/test_pack/tools/handwritten/make_paper.py    # only the paper
```

PNG, Markdown and the preview images are identical on every run; the PDFs carry a timestamp. Texts, questions and dossier groups live in `samples/test_pack/tools/handwritten/texts_data.py`.
