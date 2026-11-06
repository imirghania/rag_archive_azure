# Handwriting templates

Print these pages. Write on them by hand. Scan them. Upload the scans as a dossier.

The pages are built so that every feature of the pipeline gets real handwriting to work on: the second reader, digit disagreements, margin notes, Arabic, mixed text and a free letter.

## Read this first: what works where

- **The local runtime cannot read real handwriting.** Its OCR and its second reader are fixtures: canned JSON files, not models. If you upload your own scan to the local server, the pages fail with `no OCR fixture`.
- **Real handwriting needs the Azure deployment.** There, Document Intelligence reads the page and the vision model reads each handwritten line.
- **The `filled/` dossier works locally.** It has simulated handwriting and matching fixtures. Use it to see what the system does with these templates before you spend money on Azure.

## What is in this folder

| File | What it is | Upload it? |
| --- | --- | --- |
| `00_instructions.pdf` | One page: how to print, write, scan and upload | **No** |
| `t1_memo_with_margin_note.pdf` | A printed memo. Write a note, your initials and the date in the right margin. Sign at the bottom | Yes |
| `t2_invoice_amounts.pdf` | A printed invoice with empty boxes for quantities, prices and totals. The digit test | Yes |
| `t3_english_and_arabic_notes.pdf` | Three writing areas: English, Arabic (right to left), and a mixed line | Yes |
| `t4_free_handwriting.pdf` | A page of 26 ruled lines for a whole handwritten letter | Yes |
| `answer_key_sheet.pdf` | A table to write down what you wrote, so you can compare it with what the system read | **No** |
| `zones.json` | Every writing zone: ID, page, position in pixels at 300 dpi, language, purpose | No |
| `filled/FIN-C99-S1-F0001/` | Ready-to-upload example: `scan_001.tif` (t1, t2, t3 with simulated handwriting) and `dossier.json` | Only for the local test below |

Each page has its own capital-letter title and its own `Ref:` line. The system uses them to cut a dossier into documents, so t1 to t4 become four documents.

Small grey labels `Z1`, `Z2`, ... mark the zones. The answer key lists them in the same order. There are 27: t1 has 4, t2 has 18, t3 has 3 and t4 has 2.

## 1. Print

1. Print `t1` to `t4` on A4 paper. One page each.
2. In the print dialog choose **Actual size** or **100%**. Do not choose "Fit to page". The zones are sized for 300 dpi at real size.
3. Black and white is fine. Print `answer_key_sheet.pdf` too if you want to compare afterwards.

## 2. Write

1. Use a black or dark blue ballpoint or gel pen. No pencil. No highlighter.
2. Write the way you normally write. That is the point.
3. Write inside the boxes and on the ruled lines. Do not write over printed text.
4. Things to try:
   - t1, margin: `Approved, pay 1,750 by 15/3`, your initials, a date such as `15/3/2008`.
   - t2: any numbers. Write some 7s, 1s, 5s, 6s and 0s. These are the digits that two readers confuse. For example `1,750` and `39,000`.
   - t2, "Paid on": `3/4/2008`.
   - t3, Arabic: `يرجى المتابعة` or `تمت الموافقة`. Write from right to left.
   - t3, English: `Paid 12,500 on 3/4/2008`.
   - t3, mixed: one English phrase and one Arabic phrase on the same line.
   - t4: a letter of a few paragraphs.
5. Do not write real personal data (names, ID numbers, bank details). Use made-up data. The scans go to cloud services.
6. After you write, fill the first column of the answer key sheet: "What I actually wrote".

## 3. Scan

- **Flatbed scanner:** 300 dpi, grayscale (or black and white), save as TIFF or PDF.
- **Phone:** use a scanner app (not the plain camera). Choose grayscale or black and white and a flat, cropped PDF. Hold the phone square to the page. Make sure the light is even and all four corners are in view.
- Keep each page straight. A page that is rotated or curved is harder to read.

## 4. Name and combine the files

- Put the pages **in order** (t1, t2, t3, t4) in **one** file: one multi-page TIFF or one multi-page PDF. Example: `scan_001.tif` or `scan_001.pdf`.
- One file is the safest choice: the page order is then certain.
- Do not upload `00_instructions.pdf` or `answer_key_sheet.pdf`.
- Never select a file called `dossier.json`. The server refuses that name.
- Pick a dossier ID of your own, for example `FIN-C98-S1-F0001`. The rule: two or three capital letters for the department (`FIN` or `HR`), then `-C` and two digits, `-S` and one digit, `-F` and four digits.

## 5. Upload

### (a) The local dev server

Start the server as in [`docs/running-locally.md`](../../docs/running-locally.md), section 6.1.

```bash
uv run python -m docai.devtools.localdev
```

Then follow section 6.3 (a) of the same guide, but with your own files:

1. Open `http://localhost:8000` and sign in as **sara**.
2. Click **Upload**. Leave **Department** as `FIN` and **Mode** as `By dossier`.
3. Type your dossier ID. Choose your scan file. Click **Check files**, then **Confirm and upload**.

Remember: locally, only the `filled/` example can be processed. See the next section.

### The local test that does work: the filled example

1. Generate the fixtures. This also writes them for the filled example:

   ```bash
   uv run python -m docai.devtools.templates --out samples/templates --fixtures samples/out/fixtures
   ```

2. Start the server. Sign in as **sara**.
3. Upload `samples/templates/filled/FIN-C99-S1-F0001/scan_001.tif` with dossier ID `FIN-C99-S1-F0001`. The ID must be exactly this one, because the fixtures are named after it.

### (b) Azure

Deploy as in [`docs/running-on-azure.md`](../../docs/running-on-azure.md). Then use the same Upload page of the deployed web app (section 8.2 of that guide describes the screens). Sign in through Entra as a user with the Expert role for Finance. Use your own scans and your own dossier ID. This is where real handwriting is read.

## 6. What you should see

Wait a few seconds locally, a minute or more on Azure. Then open the dossier. It should show `completed`.

- **Every handwritten line goes to the second reader.** That is a vision model that sees only a crop of the line.
- **Where the two readings agree**, the line is verified (`handwritten_dual_agreed`).
- **Where they differ**, the line is `unverified` and a review task appears for Sara under **Review**. Digits are the usual cause. Lines that OCR is unsure of (confidence under 0.6) also become tasks.
- **The margin note on t1 is attached to the paragraph beside it.** Your note, initials and date sit to the right of the printed text. The page text shows them under the third body paragraph. (The system counts the title and the header block as paragraphs too, so it says "beside paragraph 5".)
- **t1 to t4 become four documents**, one per page.

In the filled example you should see three review tasks for Sara:

| Page | Line | Why |
| --- | --- | --- |
| t2 | Row 1 unit price: OCR `1,150`, second reader `1,750` | readers disagree (7 read as 1) |
| t2 | Row 3 total: OCR `39,006`, second reader `39,000` | readers disagree (0 read as 6) |
| t3 | Arabic line `يُرجى المتابعة`: OCR confidence 0.52 | OCR too unsure to vote |

Everything else in the filled example agrees and is verified.

### Compare with the answer key

1. Open the dossier and each page's text. Copy what the system read for each zone into the last column of the answer key.
2. Compare it with what you wrote. Differences show where the readers struggle. A line that the readers disagree on should be in the review queue.
3. `zones.json` gives each zone's position, if you want to compare in code.

## Cost

One OCR call per page and one vision call per handwritten line. A full set (t1 to t4) can be 50 to 60 vision calls if you fill every zone. That is small money, but it is not free. Start with t1 and t2.

## Privacy

Do not write real personal data on test pages. The scans go to Azure services.

## Regenerate the templates

```bash
uv run python -m docai.devtools.templates --out samples/templates --fixtures samples/out/fixtures
```

It takes about two seconds. The seed is fixed, so the page images, `scan_001.tif`, the manifest and `zones.json` are identical on every run. The PDF files contain timestamps, so their bytes change. The `--fixtures` part is only for the local runtime; `samples/out/` is not in git.
