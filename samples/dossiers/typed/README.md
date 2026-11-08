# Typed test pack

Synthetic, typed (no handwriting) documents for the RAG system: 6 dossiers, 21 documents, Finance and HR, English, Arabic and mixed Arabic + English. All organisations, people and numbers are invented and consistent with each other (for example the rent in the lease equals the rent debited in the bank statement, and the payroll total equals the payroll debit).

Regenerate everything (deterministic, seed fixed): `uv run python samples/test_pack/tools/typed/make_typed.py`. The generator rebuilds the dossier folders and this README; `questions.md` is hand-written and is left alone.

Each dossier folder has the layout of `docs/templates/filled/`: the files to upload plus `dossier.json` (the manifest; never select `dossier.json` in the upload dialog, the server refuses that name).

## Files

| File | Dossier | Dept | Language | Format | Document (Ref) | What it contains | Upload as |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `scan_001.pdf` | `FIN-C90-S1-F0001` | FIN | English | scanned PDF, page 1 | Supply Agreement Extract (`SA-2026-0415`) | Supplier contract extract: prices, 45-day payment, 2% early discount, 1.5% late interest, AED 750,000 liability cap | Upload the whole scan file; dossier ID `FIN-C90-S1-F0001` |
| `scan_001.pdf` | `FIN-C90-S1-F0001` | FIN | English | scanned PDF, page 2 | Sales Invoice (`INV-2026-1187`) | Supplier invoice: three lines, VAT 5%, total AED 50,835.75, due 29 May 2026 | Upload the whole scan file; dossier ID `FIN-C90-S1-F0001` |
| `BS-2026-05-001.docx` | `FIN-C90-S1-F0001` | FIN | English | DOCX | Bank Statement (`BS-2026-05-001`) | Bank statement page, May 2026: opening 182,400.00, closing 173,839.25, six transactions | Upload as a Word file; dossier ID `FIN-C90-S1-F0001` |
| `POL-FIN-007.txt` | `FIN-C90-S1-F0001` | FIN | English | TXT | Expense Policy Summary (`POL-FIN-007`) | Plain-text policy: allowances, receipt threshold AED 75, approval limits 5,000 / 25,000 | Upload as a text file; dossier ID `FIN-C90-S1-F0001` |
| `scan_001.pdf` | `FIN-C90-S1-F0002` | FIN | Arabic | scanned PDF, page 1 | Warehouse Lease Agreement (`LS-2025-0092`) | Arabic lease: warehouse 14, 3 years, rent 18,500/month, +4% a year, deposit 37,000, 60-day notice | Upload the whole scan file; dossier ID `FIN-C90-S1-F0002` |
| `scan_001.pdf` | `FIN-C90-S1-F0002` | FIN | Arabic | scanned PDF, page 2 | Payment Reminder Letter (`LT-2026-0231`) | Arabic official letter: June 2026 rent 19,240 unpaid, 2% late fee 384.80, total 19,624.80 by 15 June 2026 | Upload the whole scan file; dossier ID `FIN-C90-S1-F0002` |
| `INV-AR-2026-063.docx` | `FIN-C90-S1-F0002` | FIN | Arabic | DOCX | Maintenance Services Invoice (`INV-AR-2026-063`) | Arabic invoice (DOCX): maintenance services, subtotal 8,950, VAT 447.50, total 9,397.50, due 24 June 2026 | Upload as a Word file; dossier ID `FIN-C90-S1-F0002` |
| `scan_001.tif` | `FIN-C91-S1-F0003` | FIN | Arabic + English | scanned TIF, page 1 | Tax Invoice (`TI-2026-2210`) | Bilingual invoice, English and Arabic on the same lines: total 11,445.00 incl. VAT 5% | Upload the whole scan file; dossier ID `FIN-C91-S1-F0003` |
| `scan_001.tif` | `FIN-C91-S1-F0003` | FIN | Arabic + English | scanned TIF, page 2 | Payment Schedule (`PS-2026-014`) | English table with Arabic payee names: three instalments, total AED 40,082.50, 2% reserve 801.65 | Upload the whole scan file; dossier ID `FIN-C91-S1-F0003` |
| `PO-2026-0507.docx` | `FIN-C91-S1-F0003` | FIN | Arabic + English | DOCX | Purchase Order (`PO-2026-0507`) | Arabic order (DOCX) with English product codes and Western digits: total 5,770.00, 3% discount 173.10 | Upload as a Word file; dossier ID `FIN-C91-S1-F0003` |
| `BM-2026-Q3.txt` | `FIN-C91-S1-F0003` | FIN | Arabic + English | TXT | Budget Memo (`BM-2026-Q3`) | Plain-text Arabic memo with Arabic-Indic digits: Q3 2026 budget 450,000 split 30/40/25/5% | Upload as a text file; dossier ID `FIN-C91-S1-F0003` |
| `scan_001.pdf` | `HR-C90-S1-F0001` | HR | English | scanned PDF, page 1 | Payroll Summary - April 2026 (`PAY-2026-04`) | Payroll summary: 27 daily-paid staff, gross 43,700.00, deductions 5%, net 41,515.00, paid 12 May 2026 | Upload the whole scan file; dossier ID `HR-C90-S1-F0001` |
| `scan_001.pdf` | `HR-C90-S1-F0001` | HR | English | scanned PDF, page 2 | Annual Leave Policy (`HR-POL-012`) | Leave policy: 30 calendar days, carry-over 10 days, 14 days notice, sick leave pay bands, overtime 1.25x / 1.5x | Upload the whole scan file; dossier ID `HR-C90-S1-F0001` |
| `OFR-2026-031.docx` | `HR-C90-S1-F0001` | HR | English | DOCX | Employment Offer Letter (`OFR-2026-031`) | Offer letter (DOCX): Khalid Mansour, Warehouse Supervisor, total AED 8,400/month, starts 1 July 2026 | Upload as a Word file; dossier ID `HR-C90-S1-F0001` |
| `scan_001.pdf` | `HR-C90-S1-F0002` | HR | Arabic | scanned PDF, page 1 | Hr Circular (`HRC-2026-018`) | Arabic circular: summer hours 15 June to 15 September 2026, midday outdoor ban 12:30 to 15:00, overtime 125% | Upload the whole scan file; dossier ID `HR-C90-S1-F0002` |
| `scan_001.pdf` | `HR-C90-S1-F0002` | HR | Arabic | scanned PDF, page 2 | Employment Certificate (`EC-2026-077`) | Arabic employment certificate: Yasser Al Haddad, transport supervisor since 3 March 2019, salary 9,750 | Upload the whole scan file; dossier ID `HR-C90-S1-F0002` |
| `LV-2026-142.docx` | `HR-C90-S1-F0002` | HR | Arabic | DOCX | Leave Approval Notice (`LV-2026-142`) | Arabic leave approval (DOCX): annual leave 6 to 24 July 2026, 19 days, balance 24 before and 5 after | Upload as a Word file; dossier ID `HR-C90-S1-F0002` |
| `TR-2026-009.txt` | `HR-C90-S1-F0002` | HR | Arabic | TXT | Training Notice (`TR-2026-009`) | Plain-text Arabic notice: safety course 21 June 2026, 25 seats, register by 14 June, pass mark 70% | Upload as a text file; dossier ID `HR-C90-S1-F0002` |
| `scan_001.tif` | `HR-C91-S1-F0003` | HR | Arabic + English | scanned TIF, page 1 | Employment Contract Extract (`EMP-2026-044`) | Bilingual contract extract: Nadia Farouk, Accountant, AED 12,500/month, starts 15 August 2026, probation 6 months | Upload the whole scan file; dossier ID `HR-C91-S1-F0003` |
| `scan_001.tif` | `HR-C91-S1-F0003` | HR | Arabic + English | scanned TIF, page 2 | Attendance Summary (`AS-2026-05`) | Arabic report with Arabic-Indic digits: May 2026, 21 working days, overall attendance 95.2%, 31 late, 7 absences | Upload the whole scan file; dossier ID `HR-C91-S1-F0003` |
| `TA-2026-021.docx` | `HR-C91-S1-F0003` | HR | Arabic + English | DOCX | Training Attendance (`TA-2026-021`) | English table with Arabic names (DOCX): safety course 21 June 2026, session 1, pass mark 70, average 78.5 | Upload as a Word file; dossier ID `HR-C91-S1-F0003` |

## How the pages are made

- Every page has a CAPITAL-LETTER title as its first line and a `Ref:` line second, because the system cuts a dossier into documents with those two cues. The title and `Ref:` lines are in Latin letters even on Arabic documents. Each document is one page.
- Scans: A4 at 300 dpi, grey paper tone, mild noise, rotation of 0.3 to 0.8 degrees, light blur. PDF files in the `C90` dossiers, JPEG-compressed TIFF in the `C91` dossiers. One file per dossier (`scan_001.*`) holds the scanned documents in order.
- DOCX: Arial runs, right-to-left paragraphs and tables (`w:bidi`, `w:bidiVisual`) for Arabic.
- TXT: UTF-8, tables as `a | b | c`.
- No digital-born PDF: `soffice` is not installed here, and no PDF library is.
- Arabic is shaped and ordered by Pillow with Raqm (HarfBuzz and FriBiDi).

## How to upload

Web app (local dev server or the Azure deployment):

1. Sign in as **Sara** (Expert, uploads). Open **Upload**.
2. Choose the department that matches the dossier ID prefix (`FIN` or `HR`), mode **By dossier**, type the dossier ID, select all files of that folder except `dossier.json`, **Check files**, **Confirm and upload**.
3. Wait until the dossier shows `completed`.
4. Ask questions as **Layla** (reads Finance: she must see only `FIN-*` dossiers) or **Huda** (reads HR: only `HR-*` dossiers). See `questions.md`.

Note: the local runtime reads pages from canned fixtures, not from a real OCR, so these new files only process end to end on the Azure deployment (or after fixtures are made for them). The DOCX and TXT files need no OCR.
