# Test questions

Upload one dossier (see README), wait for `completed`, then ask these in the chat. Questions in Arabic over English documents and the reverse are on purpose. Kinds: numeric, correction (the corrected value is the answer), none (not answerable: the system must say it cannot find it).

Expected answers come from what is written on the sheets, which is not always what the original key intended. Where they differ, the question says so.

## Dossier `FIN-C95-S1-F0001` (HW02, HW03, HW04, HW16: letters and requests, Finance)

1. [en, numeric] How many life jackets were damaged in order PO-7731?
   - Expected: 6 (of the 34 that arrived).
   - Source: HW02
   - Note: the handwritten "6" is a hooked glyph that can look like 8.
2. [en, numeric] What is the annual renewal fee for warehouse licence WL-5521 and by what date must it be paid?
   - Expected: 3,450 USD, by 15 December 2026.
   - Source: HW16
3. [ar, numeric] ما المبلغ الإجمالي المستحق على Delta Office Systems بعد إضافة غرامة التأخير؟
   - Expected: 12,941.25 USD (12,750.00 plus the 191.25 late charge).
   - Source: HW03
4. [ar, text] متى أمرت الشركة المصرف بتحويل رسوم تجديد الترخيص؟
   - Expected: On 10 December 2026 (١٠ ديسمبر ٢٠٢٦).
   - Source: HW04
5. [en, none] What discount did Bluewave Marine Supplies offer on the next order?
   - Expected: NOT ANSWERABLE: the documents mention no discount. The system should say it cannot find it.
   - Source: -

## Dossier `FIN-C95-S1-F0002` (HW06, HW08, HW12, HW13: mixed notes, voucher, bank transfer, digits, Finance)

1. [ar, numeric] كم المبلغ الذي أوصت لينا قاسم بتعليق دفعه بخصوص الفاتورة INV-5520؟
   - Expected: 222.00 USD (12 pieces).
   - Source: HW06
2. [en, numeric] How much was paid to Marwan Salem Transport and on what date?
   - Expected: 1,275.50 USD (the boxed amount and the amount in words), on 2 November 2026 (02/11/2026).
   - Source: HW08
   - Note: the sheet contradicts itself. The body lists a fuel surcharge of 125.00 and a total of 1,275.00, so the lines add up to 1,275.00. A good answer gives 1,275.50 and mentions the 1,275.00 in the body. The date is not in doubt.
3. [ar, text] ما رقم حساب Bluewave Marine Supplies في تعليمات التحويل المصرفي؟
   - Expected: 7730-1195-4402.
   - Source: HW12
4. [en, numeric] What is the total outstanding amount in the statement of unpaid invoices?
   - Expected: 27,352.20 USD.
   - Source: HW13
5. [en, digits] What is the date of the statement of unpaid invoices and the amount of invoice INV-6104 in it?
   - Expected: 5 November 2026 (05/11/2026) and 12,750.00 USD.
   - Source: HW13
   - Note: the key expects a line in Arabic-Indic digits (٢٠٢٦/١١/٠٥); the sheet has Western digits, so no Arabic-Indic digit test exists on it.
6. [en, none] What is the SWIFT code of First Coastal Bank?
   - Expected: NOT ANSWERABLE: no SWIFT code appears in the documents.
   - Source: -

## Dossier `FIN-C96-S1-F0001` (HW09, HW10, HW14: minutes, clause, crossed-out correction, Finance)

1. [en, correction] On what date will the annual stock count take place?
   - Expected: 29 December 2026. The first value, 28 December, is crossed out and corrected by hand: the corrected value is the answer.
   - Source: HW14
2. [ar, text] من يجب أن يحصل على إشعار الدائن من Bluewave ومتى؟
   - Expected: Tariq Aziz, by 20 November 2026.
   - Source: HW09
3. [ar, numeric] كم بلغت ميزانية الربع الرابع التي تمت الموافقة عليها؟
   - Expected: 214,000 USD.
   - Source: HW09
4. [en, text] What late charge does the contract clause allow if an invoice is not paid on time?
   - Expected: A one-time late charge of 1.5% of the overdue amount (clause 7.2).
   - Source: HW10
5. [en, none] Who will lead each stock-count team in the warehouse?
   - Expected: NOT ANSWERABLE: the memo gives team sizes but no team leaders.
   - Source: -
6. [en, date] On what date was the meeting recorded in the minutes held?
   - Expected: 7 November 2026, as written in the DATE box. (The original key said 9 November; the sheet was written with 7.)
   - Source: HW09

## Dossier `HR-C95-S1-F0001` (HW01, HW05, HW11: resignation, leave request, employment letter, HR)

1. [en, text] What is Khaled Nasser's last working day?
   - Expected: 14 January 2027.
   - Source: HW01
2. [ar, numeric] كم يوما طلبت ليلى الخطيب كإجازة سنوية ومتى تعود إلى العمل؟
   - Expected: 10 working days; she returns on Sunday 20 December 2026.
   - Source: HW05
   - Note: the dates are written in Arabic-Indic digits (٢٠ ديسمبر ٢٠٢٦).
3. [ar, numeric] ما إجمالي الراتب الشهري المعروض على السيد العلي؟
   - Expected: 3,400 USD (2,800 basic plus 600 housing).
   - Source: HW11
4. [en, text] When does Mr Al-Ali's probation period end?
   - Expected: 3 April 2027.
   - Source: HW11
5. [en, none] Why is Khaled Nasser resigning?
   - Expected: NOT ANSWERABLE: the letter gives no reason.
   - Source: -

## Dossier `HR-C96-S1-F0001` (HW07, HW15, HW17: onboarding note, margin note, Arabic minutes, HR)

1. [en, numeric] Which laptop model will the new employee receive and what does it cost?
   - Expected: Model LT-5520, 1,150 USD.
   - Source: HW07
2. [en, numeric] What is the total overtime amount for the warehouse team in November 2026?
   - Expected: 2,592.00 USD (144 hours at 18.00).
   - Source: HW15
3. [en, text] Was the overtime approved, by whom and when? (answer is in the margin note)
   - Expected: Yes: approved by R.M. on 18/11/2026, to be paid with the November payroll.
   - Source: HW15
4. [ar, numeric] كم بلغت التكلفة الإجمالية لدورة السلامة المهنية؟
   - Expected: 1,800 USD for 12 trainees.
   - Source: HW17
   - Note: the year of action item أ ("2026.") wraps onto its own line, but this question does not use it.
5. [ar, none] من هو المدرب الذي سيقدم دورة السلامة المهنية؟
   - Expected: NOT ANSWERABLE: the minutes only say the trainer must still be confirmed.
   - Source: HW17

## Changes since the first version of this file

- Nine sheets were re-wrapped from landscape pages to A4 portrait (see README), so nothing is damaged and the dossiers are back to their themes. The five dossier groups are the original ones.
- Changed: the HW08 question now expects 1,275.50 and asks the answer to mention the 1,275.00 in the body.
- Added: the HW09 meeting date (7 November 2026) and the HW13 date and amount question.
