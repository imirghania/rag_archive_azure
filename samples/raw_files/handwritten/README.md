# Handwritten test pack

Seventeen sheets of official-looking paper, filled in with handwriting and scanned, an answer key and test questions. You group the scans into dossiers, upload them and ask the questions.

**Real handwriting needs the Azure deployment.** The local runtime has canned fixtures instead of OCR and cannot read these scans. All names, numbers and organisations here are invented.

## What is in this folder

| Path | What it is | Upload it? |
| --- | --- | --- |
| `dossiers/<ID>/` | One folder per dossier (5), holding copies of its sheets. Select all the files of a folder when you upload | **Yes** |
| `sheets/HWnn_<design>.pdf` | The 17 filled and scanned sheets, one page each, the originals. Each has its own printed title and `Ref:` number | Upload the copies in `dossiers/` instead |
| `answer_key.md` | The intended text of every sheet, with an "As written" note on what the sheet really says | **No** |
| `questions.md` | Test questions per dossier, with expected answers | **No** |

Never upload the answer key, the questions or any `dossier.json`.

The blank paper (`paper/`), the texts to copy (`TEXTS_TO_WRITE`) and the simulated previews (`preview_filled/`) are not in this folder any more. The scripts in `samples/test_pack/tools/handwritten/` produce them (see the last section).

## State of the scans

All 17 sheets are portrait A4 pages with the letterhead, the printed title, the `Ref:` line and the footer, which the system uses to cut a dossier into documents.

Nine sheets (HW03, HW04, HW06, HW10, HW11, HW12, HW13, HW16, HW17) were first scanned as landscape pages that hid the top and bottom of the sheet. On 2026-11-08 they were re-wrapped as A4 portrait pages from the full image embedded in each file (same handwriting, nothing redrawn). Their resolution is 150 dpi; the other eight are 300 dpi. The original landscape files are not kept in the repository.

**Observation, to be verified:** looking at the scans, the text of HW03, HW04, HW06, HW16 and HW17 looks typed (regular letter shapes, even spacing), and HW10 and HW13 look like a slanted handwriting-style font. HW01, HW02, HW05, HW07, HW08, HW09, HW14 and HW15 look like real pen handwriting. If the typed look is right, OCR over those sheets is a printed-text test.

**Content differences.** The sheets are not word for word what the key intended. The ones that change an answer: HW08 gives two totals (the boxed amount and the words say 1,275.50, the body says 1,275.00), HW09's date box says 7 November 2026 (the key says 9), and HW13's "Arabic-Indic digits" line is written in Western digits. Everything else is in the "As written" notes of `answer_key.md`.

## Group the scans into dossiers

Each dossier has a folder in `dossiers/`. The folder name is the dossier ID (format `<DEPT>-C<2 digits>-S<1 digit>-F<4 digits>`, checked against `src/docai/contracts/keys.py`). The loose PDFs in `sheets/` are the originals and the `dossiers/` folders hold copies grouped for upload. If you re-scan a sheet, copy it into its dossier folder again (`cp -p`).

| Dossier folder | Department | Sheets (in this order) | Theme |
| --- | --- | --- | --- |
| `FIN-C95-S1-F0001` | Finance | HW02, HW03, HW04, HW16 | Letters and requests, English and Arabic |
| `FIN-C95-S1-F0002` | Finance | HW06, HW08, HW12, HW13 | Mixed notes, voucher, bank transfer, digits |
| `FIN-C96-S1-F0001` | Finance | HW09, HW10, HW14 | Minutes, clause, crossed-out correction |
| `HR-C95-S1-F0001` | HR | HW01, HW05, HW11 | Resignation, leave request, employment letter |
| `HR-C96-S1-F0001` | HR | HW07, HW15, HW17 | Onboarding note, margin note, Arabic minutes |

Optional manifest:

```bash
uv run python samples/test_pack/tools/handwritten/dossier_json.py samples/test_pack/handwritten/dossiers/FIN-C95-S1-F0001
```

It writes `dossier.json` (name, bytes, sha256, pages of each scan) into the folder. It is for your records. The web app makes its own manifest, so never select `dossier.json` when uploading.

## Upload

Use the deployed web app (Azure, Entra sign-in). The local dev server only shows the screens: your own scans fail there with `no OCR fixture`.

1. Open the web app. Sign in as **sara** (Expert, Finance) for the three `FIN-...` dossiers, or as **huda** (Expert, HR) for the two `HR-...` dossiers.
2. Click **Upload**. Choose **Department** `FIN` or `HR` to match the dossier, mode `By dossier`.
3. Type the dossier ID (the folder name). Open that folder in `dossiers/` and select all its files. Click **Check files**, then **Confirm and upload**.
4. Wait until the dossier shows `completed` (a minute or more on Azure). Lines where the two readers disagree become review tasks under **Review**: for Sara in Finance, for Huda in HR.
5. Uploading needs the Expert role and the department's expert group. Sara holds the Finance expert group and Huda the HR expert group (created by deploy steps 41, 42 and 60), so each can upload for their own department only. Rana is the steward for both departments: she settles escalated HR review tasks and approves HR hints.
6. Ask the questions of `questions.md` as a reader (`layla` for Finance, `huda` for HR) and compare with the expected answers and `answer_key.md`.

Cost: one OCR call per page and one vision call per handwritten line. Start with one dossier.

## Background: how the sheets were meant to be made

Each sheet was printed on A4 at 100% (never "Fit to page"), filled with a dark pen in natural handwriting, leaving the printed title and `Ref:` alone, and scanned at 300 dpi in grayscale, one page per scan, all four corners visible, as a **portrait A4 page**. HW14 has one deliberate crossed-out correction (`28` struck through, `29` written above) and HW15 a margin note in the printed margin column.

## Making the blank paper and texts again

The scripts in `samples/test_pack/tools/handwritten/` (`make_all.py`, `make_paper.py`, `make_texts.py`, `make_preview.py`) write to this folder, and the output path is fixed in each script. **Running them here overwrites `sheets/` (your scans), `answer_key.md` and `questions.md`**, and creates `paper/`, `TEXTS_TO_WRITE.*` and `preview_filled/`.

To regenerate without touching this folder, copy `tools/` somewhere else first and run the copy. The output goes to a `handwritten/` folder next to the copied `tools/` (this should work because the path is taken from the script's own location; it has not been tried):

```bash
mkdir /tmp/hwgen && cp -r samples/test_pack/tools /tmp/hwgen/tools
uv run python /tmp/hwgen/tools/handwritten/make_all.py      # about 40 s, writes /tmp/hwgen/handwritten/
```

`tools/handwritten/texts_data.py` still holds the earlier dossier groups and questions. The groups and questions above were edited by hand in this folder and are not in that file.
