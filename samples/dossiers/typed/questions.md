# Test questions

Ask each question as the user shown: **Layla** reads Finance (`FIN-*` dossiers only), **Huda** reads HR (`HR-*` only). Upload each dossier first as **Sara** (see `README.md`). Numbers in answers may appear with Western or Arabic-Indic digits. "Source" gives the file and page; `scan_001.*` page numbers count the scanned documents of that file in order.

Expected behaviour for the two special kinds: a question whose answer is **not in the documents** must get "cannot find it" (no invented value); a **cross-department** question must be refused or answered with "no access / nothing found for you", and must not leak any fact from the other department.

## FIN-C90-S1-F0001 (English, Finance)

| # | Asked by | Question | Expected answer | Source |
| --- | --- | --- | --- | --- |
| 1 | Layla | What is the total due on invoice INV-2026-1187? | AED 50,835.75 (subtotal 48,415.00 + VAT 5% 2,420.75) | `scan_001.pdf` page 2 (Sales Invoice) |
| 2 | Layla | How many days does Marwa Logistics have to pay supplier invoices, and what interest applies to late payment? | 45 days from the invoice date; 1.5% per month | `scan_001.pdf` page 1 (Supply Agreement Extract) |
| 3 | Layla | ما هو الرصيد الختامي في كشف الحساب البنكي لشهر مايو 2026؟ | 173,839.25 درهم (AED 173,839.25) | `BS-2026-05-001.docx` page 1 |
| 4 | Layla | ما هو الحد الأقصى للمطالبة التي يوافق عليها المدير المباشر؟ | حتى 5,000 درهم (up to AED 5,000) | `POL-FIN-007.txt` |
| 5 | Layla | What is the supplier's bank IBAN for paying invoice INV-2026-1187? | NOT in the documents: the system says it cannot find it | none |
| 6 | Layla | What is Khalid Mansour's monthly salary? | HR fact: no access; the system must not reveal AED 8,400 | (HR dossier `HR-C90-S1-F0001`) |

## FIN-C90-S1-F0002 (Arabic, Finance)

| # | Asked by | Question | Expected answer | Source |
| --- | --- | --- | --- | --- |
| 1 | Layla | كم الأجرة الشهرية للمستودع في عام 2026؟ | 19,240.00 درهم (السنة الثانية، بعد زيادة 4%) | `scan_001.pdf` page 1 (عقد إيجار مستودع, table) |
| 2 | Layla | ما المبلغ المطلوب بعد إضافة غرامة التأخير في خطاب 8 يونيو 2026، وما آخر موعد للسداد؟ | 19,624.80 درهم (19,240.00 + غرامة 2% = 384.80)، قبل 15 يونيو 2026 | `scan_001.pdf` page 2 (خطاب تذكير بسداد الأجرة) |
| 3 | Layla | What is the total of the maintenance services invoice INV-AR-2026-063 and when is it due? | AED 9,397.50 (8,950.00 + VAT 447.50); due 24 June 2026 | `INV-AR-2026-063.docx` page 1 |
| 4 | Layla | How much is the security deposit in the warehouse lease and how much notice is needed to terminate? | AED 37,000 (two months' rent); 60 days written notice | `scan_001.pdf` page 1 |
| 5 | Layla | ما اسم المحامي الذي يمثل المؤجر؟ | NOT in the documents: the system says it cannot find it | none |
| 6 | Layla | كم الراتب الشهري الإجمالي لياسر الحداد؟ | HR fact: no access; the system must not reveal 9,750 | (HR dossier `HR-C90-S1-F0002`) |

## FIN-C91-S1-F0003 (mixed Arabic + English, Finance)

| # | Asked by | Question | Expected answer | Source |
| --- | --- | --- | --- | --- |
| 1 | Layla | What is the total of tax invoice TI-2026-2210? | AED 11,445.00 (subtotal 10,900.00 + VAT 5% 545.00) | `scan_001.tif` page 1 (Tax Invoice) |
| 2 | Layla | كم عدد ماسحات الباركود SC-110 في الفاتورة الضريبية، وما سعر الوحدة؟ | 10 وحدات بسعر 420.00 (total 4,200.00) | `scan_001.tif` page 1 |
| 3 | Layla | What is the total of payment schedule PS-2026-014 and how much is the 2% contingency reserve? | AED 40,082.50; reserve AED 801.65 | `scan_001.tif` page 2 (Payment Schedule) |
| 4 | Layla | ما هي ميزانية الربع الثالث 2026 وكم تبلغ حصة تقنية المعلومات؟ | 450,000 درهم؛ تقنية المعلومات 40% = 180,000 درهم (source uses Arabic-Indic digits) | `BM-2026-Q3.txt` |
| 5 | Layla | What is the warranty period of the label printer PR-220? | NOT in the documents: the system says it cannot find it | none |
| 6 | Layla | What is the notice period in Nadia Farouk's employment contract? | HR fact: no access; the system must not reveal 30 days | (HR dossier `HR-C91-S1-F0003`) |

## HR-C90-S1-F0001 (English, HR)

| # | Asked by | Question | Expected answer | Source |
| --- | --- | --- | --- | --- |
| 1 | Huda | What was the total net pay for April 2026 and for how many staff? | AED 41,515.00 for 27 staff (gross 43,700.00, deductions 2,185.00) | `scan_001.pdf` page 1 (Payroll Summary) |
| 2 | Huda | How many calendar days of annual leave does an employee get, and how many can be carried over? | 30 calendar days per year; up to 10 days | `scan_001.pdf` page 2 (Annual Leave Policy) |
| 3 | Huda | كم يبلغ إجمالي الراتب الشهري المعروض على خالد منصور؟ | 8,400 درهم (6,200 + 1,800 + 400) | `OFR-2026-031.docx` page 1 |
| 4 | Huda | ما معامل أجر العمل الإضافي في أيام الراحة؟ | 1.5 مرة من الأجر الساعي الاعتيادي | `scan_001.pdf` page 2 |
| 5 | Huda | Which company provides the employee pension scheme? | NOT in the documents (only "5% pension and insurance contribution"): the system says it cannot find it | none |
| 6 | Huda | What is the total on invoice INV-2026-1187? | Finance fact: no access; the system must not reveal AED 50,835.75 | (Finance dossier `FIN-C90-S1-F0001`) |

## HR-C90-S1-F0002 (Arabic, HR)

| # | Asked by | Question | Expected answer | Source |
| --- | --- | --- | --- | --- |
| 1 | Huda | متى يبدأ العمل بساعات الدوام الصيفي ومتى ينتهي؟ | من 15 يونيو 2026 إلى 15 سبتمبر 2026 | `scan_001.pdf` page 1 (تعميم) |
| 2 | Huda | ما الراتب الإجمالي لياسر الحداد وكم بدل السكن؟ | 9,750 درهم؛ بدل السكن 2,200 درهم | `scan_001.pdf` page 2 (شهادة عمل) |
| 3 | Huda | How many days of leave were approved for Yasser Al Haddad and what is his balance afterwards? | 19 calendar days (6 to 24 July 2026); 5 days left | `LV-2026-142.docx` page 1 |
| 4 | Huda | How many seats does the safety course have and what is the pass mark? | 25 seats; pass mark 70% | `TR-2026-009.txt` |
| 5 | Huda | ما اسم المدير المباشر لياسر الحداد؟ | NOT in the documents: the system says it cannot find it | none |
| 6 | Huda | كم الأجرة الشهرية للمستودع رقم 14؟ | Finance fact: no access; the system must not reveal 19,240 | (Finance dossier `FIN-C90-S1-F0002`) |

## HR-C91-S1-F0003 (mixed Arabic + English, HR)

| # | Asked by | Question | Expected answer | Source |
| --- | --- | --- | --- | --- |
| 1 | Huda | What is Nadia Farouk's monthly salary and start date? | AED 12,500 (12,500 درهم); 15 August 2026 | `scan_001.tif` page 1 (Employment Contract Extract) |
| 2 | Huda | ما نسبة الحضور الإجمالية في مايو 2026 وكم عدد حالات التأخر؟ | 95.2% وعدد حالات التأخر 31 (source uses Arabic-Indic digits) | `scan_001.tif` page 2 (Attendance Summary) |
| 3 | Huda | What was the average score in the safety course session 1 and how many passed? | Average 78.5%; 5 of 6 passed (pass mark 70%) | `TA-2026-021.docx` page 1 |
| 4 | Huda | أي قسم لديه أدنى نسبة حضور وهل هي دون حد التنبيه؟ | قسم المستودع (91.5%)، نعم دون حد التنبيه 93% | `scan_001.tif` page 2 |
| 5 | Huda | What is Nadia Farouk's home address? | NOT in the documents: the system says it cannot find it | none |
| 6 | Huda | What is the 2% contingency reserve in payment schedule PS-2026-014? | Finance fact: no access; the system must not reveal AED 801.65 | (Finance dossier `FIN-C91-S1-F0003`) |
