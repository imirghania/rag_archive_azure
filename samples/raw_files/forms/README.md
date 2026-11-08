# Handwriting test forms (13 filled forms)

Printed forms that were filled in by hand, scanned, and are ready to upload as dossiers. All data is made up.

## What is in this folder

| File | What it is | Upload it? |
| --- | --- | --- |
| `dossiers/<ID>/` | One folder per dossier (5), holding copies of its forms. Select all the files of a folder when you upload | **Yes** |
| `F01_...pdf` to `F13_...pdf` | The 13 filled forms, one image-only page each: the originals | Upload the copies in `dossiers/` instead |
| `answer_key.md` | What each zone should contain, and under each form how the scan really differs ("As written") | No |
| `questions.md` | Test questions per dossier with the expected answers, matched to what is written | No |

Never upload the two Markdown files.

The forms F14 (official memorandum, Arabic) and F15 (leave request, Arabic) are named in the key and the questions, but there is **no file for either** in this folder. HR-C93 therefore holds only F10, and its questions 1 to 3 are marked PENDING until F14 and F15 are added.

## Scan quality

All 13 files are single-page, image-only PDFs. Two reviewers noticed that the writing looks digitally rendered rather than pen on paper: strokes of even width, a pure white background, no skew or paper noise, identical letter shapes repeating. Check this if the test is meant to exercise real scan noise. The printed title and `Ref:` line are intact on all 13 forms, so cutting the dossier by title and Ref is not at risk.

## Group the forms into dossiers

Each dossier has a folder in `dossiers/`; the folder name is the dossier ID. The loose PDFs in this folder are the originals and the `dossiers/` folders hold copies grouped for upload. If you re-scan a form, copy it into its dossier folder again (`cp -p`).

| Dossier | Dept | Forms | Theme |
| --- | --- | --- | --- |
| `FIN-C92-S1-F0001` | Finance | F03, F04, F12, F13 | Purchasing: order, goods received, invoice approval, cheque request |
| `FIN-C93-S1-F0001` | Finance | F02, F05, F06 | Cash and expenses: expense claim, deposit slip, petty cash voucher |
| `FIN-C94-S1-F0001` | Finance | F08, F11 | Meeting minutes and fleet log |
| `HR-C92-S1-F0001` | HR | F01, F07, F09 | Leave request, timesheet, information update |
| `HR-C93-S1-F0001` | HR | F10 (F14 and F15 when they exist) | Visitor log, Arabic memorandum and leave request |

Upload note: uploading needs the Expert role and the department's expert group. Sara is a Finance expert and uploads the three `FIN-...` dossiers. Huda is the HR expert (HR experts group, live on Azure after deploy steps 41, 42 and 60) and uploads the two `HR-...` dossiers.

## Upload and ask

1. Sign in as **sara** for a `FIN-...` dossier, or as **huda** for an `HR-...` one. Open **Upload**, set the department to `FIN` or `HR` to match (the page pre-fills `FIN`), mode `By dossier`.
2. Type the dossier ID, open its folder in `dossiers/` and select all its files, **Check files**, **Confirm and upload**.
3. Wait for `completed`. Lines where the two readers disagree become review tasks.
4. Sign in as **layla** (Finance) or **huda** (HR) and ask the questions of `questions.md`. Compare with the expected answers.

Real handwriting needs the Azure deployment; the local runtime has canned fixtures and cannot read it.

## Regenerate (careful)

The blank forms, the "what to write" sheets, the zone positions and the preview images come from `samples/test_pack/tools/forms/make_forms.py`. It writes into this folder and cannot be pointed elsewhere. Running it **overwrites the 13 filled PDFs and these three Markdown files** with blank forms and the original texts. Copy this folder first.
