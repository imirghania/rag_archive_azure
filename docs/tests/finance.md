# Finance tests

Nine Finance dossiers: three typed, three of filled forms, three of handwriting. Sara uploads them (department `FIN`); Layla asks the questions. Paths are relative to `samples/dossiers/<document-type>/`. Upload each dossier as described in the overview, wait for `completed`, then ask.

Types used below: **numeric**, **correction** (a value was crossed out and rewritten: the rewritten value is the answer), **not in documents** (the right answer is that the documents do not say), **cross-department** (an HR fact: Layla must get no access or nothing found, and the value must not appear), and plain **text** or **date**. Numbers may appear with Western or Arabic-Indic digits. Where a document was written in Arabic and the question in English, or the reverse, the table says so.

First Azure result so far: `FIN-C90-S1-F0001` completed with 4 documents. The answers below were not yet confirmed on Azure.

## 1. Typed dossiers

### FIN-C90-S1-F0001: English invoice, agreement, bank statement, policy

Files: `samples/dossiers/typed/FIN-C90-S1-F0001/scan_001.pdf`, `BS-2026-05-001.docx`, `POL-FIN-007.txt`. Do not select `dossier.json`.

| #   | Language | Question                                                                                                     | Expected answer                                                             | Type                         |
| --- | -------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- | ---------------------------- |
| 1   | EN       | What is the total due on invoice INV-2026-1187?                                                              | AED 50,835.75 (subtotal 48,415.00 plus 5% VAT 2,420.75). Page 2 of the scan | numeric                      |
| 2   | EN       | How many days does Marwa Logistics have to pay supplier invoices, and what interest applies to late payment? | 45 days from the invoice date; 1.5% per month. Page 1 of the scan           | numeric                      |
| 3   | AR       | ما هو الرصيد الختامي في كشف الحساب البنكي لشهر مايو 2026؟                                                    | 173,839.25 درهم (AED 173,839.25), over the English bank statement           | numeric, Arabic over English |
| 4   | AR       | ما هو الحد الأقصى للمطالبة التي يوافق عليها المدير المباشر؟                                                  | حتى 5,000 درهم (up to AED 5,000), from the English expense policy           | numeric, Arabic over English |
| 5   | EN       | What is the supplier's bank IBAN for paying invoice INV-2026-1187?                                           | Not in the documents: the system says it cannot find it                     | not in documents             |
| 6   | EN       | What is Khalid Mansour's monthly salary?                                                                     | HR fact: no access. The value AED 8,400 must not appear                     | cross-department             |

### FIN-C90-S1-F0002: Arabic lease, reminder letter, invoice

Files: `samples/dossiers/typed/FIN-C90-S1-F0002/scan_001.pdf`, `INV-AR-2026-063.docx`.

| #   | Language | Question                                                                                            | Expected answer                                                                           | Type                         |
| --- | -------- | --------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------- |
| 1   | AR       | كم الأجرة الشهرية للمستودع في عام 2026؟                                                             | 19,240.00 درهم (second year, after a 4% increase). Scan page 1, table                     | numeric                      |
| 2   | AR       | ما المبلغ المطلوب بعد إضافة غرامة التأخير في خطاب 8 يونيو 2026، وما آخر موعد للسداد؟                | 19,624.80 درهم (19,240.00 plus a 2% penalty of 384.80), before 15 June 2026. Scan page 2  | numeric, date                |
| 3   | EN       | What is the total of the maintenance services invoice INV-AR-2026-063 and when is it due?           | AED 9,397.50 (8,950.00 plus VAT 447.50); due 24 June 2026. English over an Arabic invoice | numeric, English over Arabic |
| 4   | EN       | How much is the security deposit in the warehouse lease and how much notice is needed to terminate? | AED 37,000 (two months' rent); 60 days' written notice. English over an Arabic lease      | numeric, English over Arabic |
| 5   | AR       | ما اسم المحامي الذي يمثل المؤجر؟                                                                    | Not in the documents: the system says it cannot find it                                   | not in documents             |
| 6   | AR       | كم الراتب الشهري الإجمالي لياسر الحداد؟                                                             | HR fact: no access. The value 9,750 must not appear                                       | cross-department             |

### FIN-C91-S1-F0003: mixed Arabic and English

Files: `samples/dossiers/typed/FIN-C91-S1-F0003/scan_001.tif`, `BM-2026-Q3.txt`, `PO-2026-0507.docx`.

| #   | Language | Question                                                                                      | Expected answer                                                                         | Type                     |
| --- | -------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ------------------------ |
| 1   | EN       | What is the total of tax invoice TI-2026-2210?                                                | AED 11,445.00 (subtotal 10,900.00 plus 5% VAT 545.00). Scan page 1                      | numeric                  |
| 2   | AR       | كم عدد ماسحات الباركود SC-110 في الفاتورة الضريبية، وما سعر الوحدة؟                           | 10 units at 420.00 (total 4,200.00), from the tax invoice                               | numeric, see open points |
| 3   | EN       | What is the total of payment schedule PS-2026-014 and how much is the 2% contingency reserve? | AED 40,082.50; reserve AED 801.65. Scan page 2                                          | numeric                  |
| 4   | AR       | ما هي ميزانية الربع الثالث 2026 وكم تبلغ حصة تقنية المعلومات؟                                 | 450,000 درهم؛ تقنية المعلومات 40% = 180,000 درهم. The source writes Arabic-Indic digits | numeric                  |
| 5   | EN       | What is the warranty period of the label printer PR-220?                                      | Not in the documents: the system says it cannot find it                                 | not in documents         |
| 6   | EN       | What is the notice period in Nadia Farouk's employment contract?                              | HR fact: no access. The value 30 days must not appear                                   | cross-department         |

## 2. Filled forms

These are one-page forms filled in with handwriting-style writing and scanned. Every page carries its own printed title and `Ref:` line, which is how the system splits a dossier into documents. Sara uploads each dossier: open its folder under `samples/dossiers/forms/` and select all its files (the file names are listed so you can check). The expected answers follow what is actually written on the scans, which differs from the original intention in a few places (noted).

### FIN-C92-S1-F0001: purchasing cycle

Folder: `samples/dossiers/forms/dossiers/FIN-C92-S1-F0001/`, select all its files: F03 purchase order, F04 goods received note, F12 invoice approval sheet, F13 cheque request (Arabic).

| #   | Language | Question                                                                         | Expected answer                                                                                                                       | Type                            |
| --- | -------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| 1   | EN       | What is the grand total of purchase order PO-2026-0417?                          | 1,230.60 EGP                                                                                                                          | numeric                         |
| 2   | EN       | What unit price was written for the Toner cartridge HP-85 on the purchase order? | 64.20 (62.40 was crossed out)                                                                                                         | correction                      |
| 3   | EN       | How many toner cartridges were ordered and how many were received?               | Ordered 6, received 4 (5 was crossed out)                                                                                             | numeric, correction             |
| 4   | AR       | ما المبلغ الذي تمت الموافقة عليه في ورقة اعتماد الفاتورة INV-55120؟              | 1,102.20 (the invoice amount). Arabic question over an English form                                                                   | numeric, Arabic over English    |
| 5   | EN       | To whom was the cheque requested and for what amount?                            | Sunrise Office Supplies (صن رايز لمستلزمات المكاتب), 1102.20 (١١٠٢.٢٠); 1230.60 was crossed out. English question over an Arabic form | correction, English over Arabic |
| 6   | EN       | What is the supplier's bank account number?                                      | Not in the documents                                                                                                                  | not in documents                |
| 7   | EN       | What does the finance manager's note on the cheque request say?                  | Nothing: the note box on the cheque request was left empty                                                                            | empty field                     |

### FIN-C93-S1-F0001: cash and expenses

Folder: `samples/dossiers/forms/dossiers/FIN-C93-S1-F0001/`, select all its files: F02 expense claim, F05 bank deposit slip, F06 petty cash voucher.

| #   | Language | Question                                                            | Expected answer                                                                                                                                                            | Type                     |
| --- | -------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------ |
| 1   | EN       | What is the total claimed on Layla Mansour's expense claim?         | 1,963.25 EGP                                                                                                                                                               | numeric                  |
| 2   | EN       | How much did the two-night hotel stay cost?                         | 1,420.00 (1,240.00 was crossed out). The line is written `1,420,00` with a comma as the decimal mark, so a reading of 1,420,00 is acceptable if the answer states 1,420.00 | numeric, correction      |
| 3   | AR       | كم بلغ إجمالي الإيداع المصرفي بتاريخ 12.03.2026؟                    | 8,900.50 (8,090.50 was crossed out). Arabic question over an English form                                                                                                  | numeric, correction      |
| 4   | EN       | Who was paid by petty cash voucher FIN/PC/2026/0319 and for what?   | محمود عادل (Mahmoud Adel), 86.50 EGP, shipping fee via FastRoute no. 7714 (the written number is 7714; the original key said 7741)                                         | mixed Arabic and English |
| 5   | EN       | What is the account number of the deposit slip?                     | 4471 0093 2258. It is written `4471 00 93 22 58`: same digits, different grouping                                                                                          | digits                   |
| 6   | EN       | What is the name of the person who approved the petty cash voucher? | Not in the documents (only a signature, no printed or written name)                                                                                                        | not in documents         |

### FIN-C94-S1-F0001: meeting and fleet

Folder: `samples/dossiers/forms/dossiers/FIN-C94-S1-F0001/`, select all its files: F08 meeting minutes, F11 vehicle maintenance log.

| #   | Language | Question                                                                                 | Expected answer                                               | Type             |
| --- | -------- | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------- | ---------------- |
| 1   | EN       | What budget ceiling was set for Q1 at the meeting on 11 March 2026?                      | 480,000                                                       | numeric          |
| 2   | AR       | من المسؤول عن إعداد سياسة السفر المعدلة وما موعد التسليم؟                                | Omar Farouk, 20/03/2026. Arabic question over an English form | date             |
| 3   | EN       | What did the margin notes of the meeting say?                                            | 'check with Hana' and 're: travel 12%?'                       | margin note      |
| 4   | EN       | What was the total maintenance cost of vehicle FLT-07, and when is the next service due? | 1,750.00 EGP; at 90,000 km (June 2026)                        | numeric          |
| 5   | EN       | Which garage will carry out the next service?                                            | Not in the documents                                          | not in documents |

## 3. Handwriting

These are scans of sheets written with a pen. Real handwriting is read only by the deployed Azure services. Sara uploads each dossier; open its folder under `samples/dossiers/handwritten/dossiers/` and select all its files (the sheet names are listed so you can check). Questions in Arabic over English sheets and the reverse are deliberate. Expected answers come from what is written on the sheets, which is not always what the original text intended. These sheets cost the most (an OCR call per page, a vision call per handwritten line), so run them last, one dossier at a time.

### FIN-C95-S1-F0001: letters and requests

Folder: `samples/dossiers/handwritten/dossiers/FIN-C95-S1-F0001/`, select all its files: HW02, HW03, HW04, HW16.

| #   | Language | Question                                                                                       | Expected answer                                                                        | Type             |
| --- | -------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | ---------------- |
| 1   | EN       | How many life jackets were damaged in order PO-7731?                                           | 6 (of the 34 that arrived). The handwritten 6 has a hooked shape that can be read as 8 | numeric          |
| 2   | EN       | What is the annual renewal fee for warehouse licence WL-5521 and by what date must it be paid? | 3,450 USD, by 15 December 2026 (HW16)                                                  | numeric, date    |
| 3   | AR       | ما المبلغ الإجمالي المستحق على Delta Office Systems بعد إضافة غرامة التأخير؟                   | 12,941.25 USD (12,750.00 plus the 191.25 late charge) (HW03)                           | numeric          |
| 4   | AR       | متى أمرت الشركة المصرف بتحويل رسوم تجديد الترخيص؟                                              | On 10 December 2026 (١٠ ديسمبر ٢٠٢٦) (HW04)                                            | date             |
| 5   | EN       | What discount did Bluewave Marine Supplies offer on the next order?                            | Not in the documents: no discount is mentioned                                         | not in documents |

### FIN-C95-S1-F0002: notes, voucher, bank transfer, digits

Folder: `samples/dossiers/handwritten/dossiers/FIN-C95-S1-F0002/`, select all its files: HW06, HW08, HW12, HW13.

| #   | Language | Question                                                                                       | Expected answer                                                                                                                                                                                                                                                                                           | Type                        |
| --- | -------- | ---------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| 1   | AR       | كم المبلغ الذي أوصت لينا قاسم بتعليق دفعه بخصوص الفاتورة INV-5520؟                             | 222.00 USD (12 pieces) (HW06)                                                                                                                                                                                                                                                                             | numeric                     |
| 2   | EN       | How much was paid to Marwan Salem Transport and on what date?                                  | 1,275.50 USD (the boxed amount and the amount in words), on 2 November 2026 (02/11/2026). The body of the voucher lists a fuel surcharge of 125.00 and a total of 1,275.00, so the sheet contradicts itself. A good answer gives 1,275.50 and mentions the 1,275.00 in the body. The date is not in doubt | numeric, inconsistent sheet |
| 3   | AR       | ما رقم حساب Bluewave Marine Supplies في تعليمات التحويل المصرفي؟                               | 7730-1195-4402 (HW12)                                                                                                                                                                                                                                                                                     | digits                      |
| 4   | EN       | What is the total outstanding amount in the statement of unpaid invoices?                      | 27,352.20 USD (HW13)                                                                                                                                                                                                                                                                                      | numeric                     |
| 5   | EN       | What is the date of the statement of unpaid invoices and the amount of invoice INV-6104 in it? | 5 November 2026 (05/11/2026) and 12,750.00 USD (HW13). The sheet writes Western digits where the original text asked for Arabic-Indic ones                                                                                                                                                                | digits                      |
| 6   | EN       | What is the SWIFT code of First Coastal Bank?                                                  | Not in the documents                                                                                                                                                                                                                                                                                      | not in documents            |

### FIN-C96-S1-F0001: minutes, clause, crossed-out correction

Folder: `samples/dossiers/handwritten/dossiers/FIN-C96-S1-F0001/`, select all its files: HW09, HW10, HW14.

| #   | Language | Question                                                                           | Expected answer                                                                                              | Type             |
| --- | -------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------- |
| 1   | EN       | On what date will the annual stock count take place?                               | 29 December 2026. The first value, 28 December, is crossed out and corrected by hand (HW14)                  | correction       |
| 2   | AR       | من يجب أن يحصل على إشعار الدائن من Bluewave ومتى؟                                  | Tariq Aziz, by 20 November 2026 (HW09)                                                                       | text, date       |
| 3   | AR       | كم بلغت ميزانية الربع الرابع التي تمت الموافقة عليها؟                              | 214,000 USD (HW09)                                                                                           | numeric          |
| 4   | EN       | What late charge does the contract clause allow if an invoice is not paid on time? | A one-time late charge of 1.5% of the overdue amount (clause 7.2) (HW10)                                     | text             |
| 5   | EN       | Who will lead each stock-count team in the warehouse?                              | Not in the documents: the memo gives team sizes but no team leaders                                          | not in documents |
| 6   | EN       | On what date was the meeting recorded in the minutes held?                         | 7 November 2026, as written in the DATE box. The original text said 9 November; the sheet was written with 7 | date             |

## Open points

- **FIN-C91-S1-F0003 question 2.** The same dossier holds a purchase order (`PO-2026-0507.docx`) that lists 6 SC-110 barcode scanners at 420.00, while the tax invoice lists 10. The question asks about the tax invoice, so 10 is the expected answer. If the answer says 6, it took the purchase order; note it and judge whether it said which document it used.
- **FIN-C93-S1-F0001, deposit slip.** The amount in words on the slip reads "Eight thousand nine hundred and fifty (50/100)", which is 8,950.50, while the figure is 8,900.50. The mistake is in the words given to copy, not in the writing. An answer that quotes the words as 8,950.50 reports what is written; the expected answer is the figure, 8,900.50.
- **No injected-instruction test file** exists in the sample material. A test that a planted instruction inside a document is ignored needs a document made for it.
- **The forms and handwriting expected answers** were read off the scans by eye, not by the system. If the first real run disagrees with one, look at the scan before blaming the system.
