# Test questions

Ask these in the web app after the dossiers are processed. Types: numeric, correction (the system must use the corrected value, not the crossed-out one), not in documents (the right answer is that the documents do not say). Do not upload this file.

The expected answers follow what is actually written on the scanned forms in this folder, including where it differs from the original key (see `answer_key.md`, "As written"). Questions marked PENDING need forms that are not in the folder yet.

## FIN-C92-S1-F0001 (Purchasing cycle: F03, F04, F12, F13)

| # | Question | Language | Expected answer | Type |
| --- | --- | --- | --- | --- |
| 1 | What is the grand total of purchase order PO-2026-0417? | EN | 1,230.60 EGP | numeric |
| 2 | What unit price was written for the Toner cartridge HP-85 on the purchase order? | EN | 64.20 (62.40 was crossed out) | correction |
| 3 | How many toner cartridges were ordered and how many were received? | EN | Ordered 6, received 4 (5 was crossed out) | numeric, correction |
| 4 | ما المبلغ الذي تمت الموافقة عليه في ورقة اعتماد الفاتورة INV-55120؟ | AR over EN form | 1,102.20 (مبلغ الفاتورة) | numeric |
| 5 | To whom was the cheque requested and for what amount? | EN over AR form | Sunrise Office Supplies (صن رايز لمستلزمات المكاتب), 1102.20 (١١٠٢.٢٠); 1230.60 was crossed out | correction |
| 6 | What is the supplier's bank account number? | EN | Not in the documents | not in documents |
| 7 | What does the finance manager's note on the cheque request say? | EN over AR form | Nothing: the note box on the cheque request (F13) was left empty | empty zone |

## FIN-C93-S1-F0001 (Cash and expenses: F02, F05, F06)

| # | Question | Language | Expected answer | Type |
| --- | --- | --- | --- | --- |
| 1 | What is the total claimed on Layla Mansour's expense claim? | EN | 1,963.25 EGP | numeric |
| 2 | How much did the two-night hotel stay cost? | EN | 1,420.00 (1,240.00 was crossed out; the hotel line is written `1,420,00`, with a comma as decimal mark) | numeric, correction |
| 3 | كم بلغ إجمالي الإيداع المصرفي بتاريخ 12.03.2026؟ | AR over EN form | 8,900.50 (8,090.50 was crossed out) | numeric, correction |
| 4 | Who was paid by petty cash voucher FIN/PC/2026/0319 and for what? | EN over bilingual form | محمود عادل (Mahmoud Adel), 86.50 EGP, shipping fee via FastRoute no. 7714 (written 7714; the key said 7741) | mixed Arabic/English |
| 5 | What is the account number of the deposit slip? | EN | 4471 0093 2258 (written `4471 00 93 22 58`: same digits, different grouping) | digits |
| 6 | What is the name of the person who approved the petty cash voucher? | EN | Not in the documents (only a signature, no printed or written name) | not in documents |

## FIN-C94-S1-F0001 (Meeting and fleet: F08, F11)

| # | Question | Language | Expected answer | Type |
| --- | --- | --- | --- | --- |
| 1 | What budget ceiling was set for Q1 at the meeting on 11 March 2026? | EN | 480,000 | numeric |
| 2 | من المسؤول عن إعداد سياسة السفر المعدلة وما موعد التسليم؟ | AR over EN form | Omar Farouk, 20/03/2026 | date |
| 3 | What did the margin notes of the meeting say? | EN | 'check with Hana' and 're: travel 12%?' | margin note |
| 4 | What was the total maintenance cost of vehicle FLT-07, and when is the next service due? | EN | 1,750.00 EGP; at 90,000 km (June 2026) | numeric |
| 5 | Which garage will carry out the next service? | EN | Not in the documents | not in documents |

## HR-C92-S1-F0001 (English HR forms: F01, F07, F09)

| # | Question | Language | Expected answer | Type |
| --- | --- | --- | --- | --- |
| 1 | How many working days of leave did Layla Mansour request, and from when to when? | EN | 7 working days, 12/03/2026 to 20/03/2026 (the end date is written in this form) | numeric, dates |
| 2 | Was the leave approved, and what did the manager remark? | EN | Approved. 'Approved. Omar to cover the approvals queue.' | checkbox, margin note |
| 3 | How many hours did she work in the week ending 13/03/2026? | EN | 36.5 hours (the written total). The written start and end times do not add up to it: see question 7 | numeric |
| 4 | What is Layla Mansour's mobile number? | EN | +20 100 555 0143 (the crossed-out number on the update form reads +20 100 555 0154; the key said 0134) | correction, digits |
| 5 | ما اسم جهة الاتصال في حالات الطوارئ وما صلتها بالموظفة؟ | AR over bilingual form | Samir Mansour, brother (أخ) | EN content |
| 6 | What is Layla Mansour's salary grade? | EN | Not in the documents | not in documents |
| 7 | On Monday of the week ending 13/03/2026, when did Layla Mansour finish and how many hours are recorded for the day? | EN | Finish 15:00 and 8.0 hours, as written. The two disagree (08:30 to 15:00 less 30 minutes is 6.0 hours), so the answer should give both and not compute one from the other | inconsistent entry |
| 8 | What is Layla Mansour's email address? | EN | layla.mansour@example.com (as written) | text |

## HR-C93-S1-F0001 (Arabic and bilingual HR forms: F15, F14, F10)

| # | Question | Language | Expected answer | Type |
| --- | --- | --- | --- | --- |
| 1 | كم يوماً طلب سامي عبد الله إجازة ولماذا؟ | AR | PENDING (needs F15, no file in the folder): ٥ أيام، وعكة صحية (تقرير طبي من مستشفى الأمل) | numeric |
| 2 | ما قرار المدير العام في المذكرة الرسمية وما تاريخ التنفيذ؟ | AR | PENDING (needs F14, no file in the folder): تمت الموافقة على التعميم، يُنفَّذ اعتباراً من ٠١/٠٦/٢٠٢٦ | handwritten Arabic, date |
| 3 | What working hours does the memo announce for the summer? | EN over AR form | PENDING (needs F14, no file in the folder): 8:00 am to 2:00 pm, Sunday to Thursday (printed text) | printed Arabic |
| 4 | How many visitors are in the visitor log of 12 Mar 2026, and who came to see Hana Saleh? | EN over bilingual form | 3 visitors; Nadia Fawzy of Delta Print | numeric |
| 5 | What is the visitor's car registration number? | EN | Not in the documents | not in documents |
