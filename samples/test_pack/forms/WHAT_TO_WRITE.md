# What to write on the test forms

Print the forms, write on them by hand exactly as listed below, scan them, group the scans into dossiers and upload. Keep this document next to you. All names, numbers and data are made up.


## 1. Printing

- Print each form F01 to F15 on A4 paper, one side, one page each.
- In the print dialog choose ACTUAL SIZE (100%). NEVER choose Fit to page: the zones are sized for real size.
- Black and white is fine. Do not print the PREVIEW_ images, answer_key.md, questions.md or this document into the scan batch.

## 2. Pen and writing

- Use a black or dark blue ballpoint or gel pen. No pencil, no highlighter, no thick felt tip.
- Write naturally, at your normal speed and with your normal handwriting. Do not print neat capitals unless the table says so.
- Copy the text exactly: same digits, commas, dots, slashes, spaces and capital letters. Write inside the boxes, never over printed text or the grey Z labels.
- Arabic is written from right to left, as you normally write it. Arabic-Indic digits (for example 12/03/2026 written with Arabic digits) are given where needed.
- CORRECTION rows: write the first value, cross it out with ONE straight line (it must stay readable), then write the second value beside it. The second value is the true one.
- Margin note rows: write small, as a quick note. Signature rows: sign with your normal signature, no printed name. Checkbox rows: tick the one box named, with a normal tick.
- Rows marked Leave empty stay empty on purpose. If you make a mistake that is not a planned correction, start the page again.

## 3. Scanning

- Flatbed scanner: 300 dpi, grayscale or colour. Phone: use a scanner app, flat cropped result, even light, all four corners visible.
- One page per scan, or one multi-page TIFF or PDF. Keep the pages straight.

## 4. Naming and grouping into dossiers

A dossier ID looks like FIN-C92-S1-F0001: department (FIN or HR), -C and two digits, -S and one digit, -F and four digits. Make one folder per dossier, named with the ID, and put its scans in the order given here. Page order matters; each page starts its own document (the system cuts on the capital-letter title and the Ref line).

- FIN-C92-S1-F0001  (Purchasing cycle): F03 Purchase Order, F04 Goods Received Note, F12 Invoice Approval Sheet, F13 Cheque Request.
- FIN-C93-S1-F0001  (Cash and expenses): F02 Expense Claim, F05 Bank Deposit Slip, F06 Petty Cash Voucher.
- FIN-C94-S1-F0001  (Meeting and fleet): F08 Meeting Minutes, F11 Vehicle Maintenance Log.
- HR-C92-S1-F0001  (English HR forms): F01 Leave Request, F07 Weekly Timesheet, F09 Employee Information Update.
- HR-C93-S1-F0001  (Arabic and bilingual HR forms): F15 Leave Request, F14 Official Memorandum, F10 Visitor Log.
Example: folder FIN-C92-S1-F0001 holds scan_001.pdf (4 pages: F03, F04, F12, F13, in that order) or four single-page scans named 001, 002, 003, 004.


## 5. Upload

- Open the web app and sign in as Sara. Click Upload. Choose the Department (FIN or HR) of the dossier and keep Mode on By dossier.
- Type the dossier ID, choose the scan file or files, click Check files, then Confirm and upload.
- The local dev server cannot read real handwriting (its readers are fixtures). Real reading needs the Azure deployment.
- Never upload this document, answer_key.md, questions.md or the PREVIEW_ images.

## F01  Leave Request   (English, HR)

File: F01_leave_request.pdf (and F01_leave_request.png). Dossier: HR-C92-S1-F0001. Printed Ref: HR/LV/2026/0417. Purpose: Employee asks for annual leave; the manager decides in the lower box.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Employee name" | `Layla Mansour` | English |  |
| Z2 | top centre, box under "Employee ID" | `EMP-20417` | English |  |
| Z3 | top right, box under "Department" | `Procurement` | English |  |
| Z4 | top full-width, row of checkboxes under "Leave type" | Tick the box:<br>`Annual leave` | Tick | Tick only this box. |
| Z5 | upper left, box under "First day of leave" | `12/03/2026` | Digits |  |
| Z6 | upper centre, box under "Last day of leave" | `20 March 2026` | English |  |
| Z7 | upper right, box under "Working days" | `7` | Digits |  |
| Z8 | upper full-width, box under "Reason for leave" | Line 1:<br>`Family wedding in Alexandria. I will be`<br>Line 2:<br>`back at my desk on 23 March.` | English |  |
| Z9 | middle left, box under "Phone during leave" | `+20 100 555 0143` | Digits |  |
| Z10 | middle right, box under "Work handed over to" | `Omar Farouk (ext. 214)` | English |  |
| Z11 | middle left, box under "Employee signature" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z12 | middle right, box under "Date signed" | `5 March 2026` | English |  |
| Z13 | lower full-width, row of checkboxes under "Decision" | Tick the box:<br>`Approved` | Tick | Tick only this box. |
| Z14 | lower full-width, box under "Manager's remarks (margin note)" | `Approved. Omar to cover the approvals queue.` | English | Margin note: write it small, to the right, as a manager would. |


## F02  Expense Claim   (English, FIN)

File: F02_expense_claim.pdf (and F02_expense_claim.png). Dossier: FIN-C93-S1-F0001. Printed Ref: FIN/EX/2026/0233. Purpose: Employee lists trip expenses in a line-item table and signs.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Claimant name" | `Layla Mansour` | English |  |
| Z2 | top centre, box under "Cost centre" | `CC-4410` | English |  |
| Z3 | top right, box under "Claim date" | `3 March 2026` | English |  |
| Z4 | top full-width, box under "Purpose of trip" | `Supplier visit, Cairo` | English |  |
| Z5 | upper left, Expenses table, row 1, "Date" column (row labelled "1") | `02/03/2026` | Digits |  |
| Z6 | upper centre, Expenses table, row 1, "Description" column (row labelled "1") | `Taxi to airport` | English |  |
| Z7 | upper right, Expenses table, row 1, "Amount (EGP)" column (row labelled "1") | `185.50` | Digits |  |
| Z8 | upper left, Expenses table, row 2, "Date" column (row labelled "2") | `02/03/2026` | Digits |  |
| Z9 | upper centre, Expenses table, row 2, "Description" column (row labelled "2") | `Hotel, 2 nights` | English |  |
| Z10 | upper right, Expenses table, row 2, "Amount (EGP)" column (row labelled "2") | Write:<br>`1,240.00`<br>cross it out with one line, then write beside it:<br>`1,420.00` | Digits | CORRECTION. |
| Z11 | upper left, Expenses table, row 3, "Date" column (row labelled "3") | `03/03/2026` | Digits |  |
| Z12 | upper centre, Expenses table, row 3, "Description" column (row labelled "3") | `Client lunch` | English |  |
| Z13 | upper right, Expenses table, row 3, "Amount (EGP)" column (row labelled "3") | `312.75` | Digits |  |
| Z14 | middle left, Expenses table, row 4, "Date" column (row labelled "4") | `03/03/2026` | Digits |  |
| Z15 | middle centre, Expenses table, row 4, "Description" column (row labelled "4") | `Parking` | English |  |
| Z16 | middle right, Expenses table, row 4, "Amount (EGP)" column (row labelled "4") | `45.00` | Digits |  |
| Z17 | middle left, Expenses table, row 5, "Date" column (row labelled "5") | Leave empty | - |  |
| Z18 | middle centre, Expenses table, row 5, "Description" column (row labelled "5") | Leave empty | - |  |
| Z19 | middle right, Expenses table, row 5, "Amount (EGP)" column (row labelled "5") | Leave empty | - |  |
| Z20 | middle right, box under "TOTAL CLAIMED (EGP)" | `1,963.25` | Digits |  |
| Z21 | middle left, box under "Notes (margin note)" | `Taxi receipt to follow.` | English | Margin note, written small. |
| Z22 | middle left, box under "Claimant signature" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z23 | middle right, box under "Date signed" | `05/03/2026` | Digits |  |


## F03  Purchase Order   (English + Arabic, FIN)

File: F03_purchase_order.pdf (and F03_purchase_order.png). Dossier: FIN-C92-S1-F0001. Printed Ref: FIN/PO/2026/0417. Purpose: Order of office supplies from one supplier; item table in English and Arabic.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Supplier" | `Sunrise Office Supplies Ltd` | English |  |
| Z2 | top centre, box under "Supplier code" | `SUP-3381` | English |  |
| Z3 | top right, box under "PO number" | `PO-2026-0417` | English |  |
| Z4 | top left, box under "Order date" | `12/03/2026` | Digits |  |
| Z5 | top centre, box under "Delivery date" | `2026-03-26` | Digits |  |
| Z6 | top right, box under "Deliver to" | `Main warehouse, Gate 3` | English |  |
| Z7 | upper left, Items table, row 1, "Description" column (row labelled "1") | `A4 copier paper, 5-ream box` | English |  |
| Z8 | upper centre, Items table, row 1, "Qty" column (row labelled "1") | `40` | Digits |  |
| Z9 | upper right, Items table, row 1, "Unit price" column (row labelled "1") | `18.75` | Digits |  |
| Z10 | upper right, Items table, row 1, "Line total" column (row labelled "1") | `750.00` | Digits |  |
| Z11 | upper left, Items table, row 2, "Description" column (row labelled "2") | `Toner cartridge HP-85` | English |  |
| Z12 | upper centre, Items table, row 2, "Qty" column (row labelled "2") | `6` | Digits |  |
| Z13 | upper right, Items table, row 2, "Unit price" column (row labelled "2") | Write:<br>`62.40`<br>cross it out with one line, then write beside it:<br>`64.20` | Digits | CORRECTION. |
| Z14 | upper right, Items table, row 2, "Line total" column (row labelled "2") | `385.20` | Digits |  |
| Z15 | upper left, Items table, row 3, "Description" column (row labelled "3") | `Stapler, heavy duty` | English |  |
| Z16 | upper centre, Items table, row 3, "Qty" column (row labelled "3") | `12` | Digits |  |
| Z17 | upper right, Items table, row 3, "Unit price" column (row labelled "3") | `7.95` | Digits |  |
| Z18 | upper right, Items table, row 3, "Line total" column (row labelled "3") | `95.40` | Digits |  |
| Z19 | middle left, Items table, row 4, "Description" column (row labelled "4") | Leave empty | - |  |
| Z20 | middle centre, Items table, row 4, "Qty" column (row labelled "4") | Leave empty | - |  |
| Z21 | middle right, Items table, row 4, "Unit price" column (row labelled "4") | Leave empty | - |  |
| Z22 | middle right, Items table, row 4, "Line total" column (row labelled "4") | Leave empty | - |  |
| Z23 | middle right, box under "GRAND TOTAL (EGP)" | `1,230.60` | Digits |  |
| Z24 | middle left, row of checkboxes under "Payment terms" | Tick the box:<br>`30 days / ٣٠ يوماً` | Tick | Tick only this box. |
| Z25 | middle left, box under "Approved by (signature)" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z26 | middle right, box under "Approver name" | `Hana Saleh` | English |  |


## F04  Goods Received Note   (English, FIN)

File: F04_goods_received_note.pdf (and F04_goods_received_note.png). Dossier: FIN-C92-S1-F0001. Printed Ref: FIN/GR/2026/0102. Purpose: Warehouse records what arrived against the purchase order (the toner is short).


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Supplier" | `Sunrise Office Supplies Ltd` | English |  |
| Z2 | top centre, box under "PO number" | `PO-2026-0417` | English |  |
| Z3 | top right, box under "Delivery note no." | `DN-88213` | English |  |
| Z4 | top left, box under "Date received" | `26 March 2026` | English |  |
| Z5 | top centre, box under "Driver name" | `Karim Aziz` | English |  |
| Z6 | top right, box under "Vehicle plate" | `KLM 7305` | English |  |
| Z7 | upper left, Goods table, row 1, "Description" column (row labelled "1") | `A4 copier paper, 5-ream box` | English |  |
| Z8 | upper right, Goods table, row 1, "Qty ordered" column (row labelled "1") | `40` | Digits |  |
| Z9 | upper right, Goods table, row 1, "Qty received" column (row labelled "1") | `40` | Digits |  |
| Z10 | upper left, Goods table, row 2, "Description" column (row labelled "2") | `Toner cartridge HP-85` | English |  |
| Z11 | upper right, Goods table, row 2, "Qty ordered" column (row labelled "2") | `6` | Digits |  |
| Z12 | upper right, Goods table, row 2, "Qty received" column (row labelled "2") | Write:<br>`5`<br>cross it out with one line, then write beside it:<br>`4` | Digits | CORRECTION. |
| Z13 | upper left, Goods table, row 3, "Description" column (row labelled "3") | `Stapler, heavy duty` | English |  |
| Z14 | upper right, Goods table, row 3, "Qty ordered" column (row labelled "3") | `12` | Digits |  |
| Z15 | upper right, Goods table, row 3, "Qty received" column (row labelled "3") | `12` | Digits |  |
| Z16 | middle left, Goods table, row 4, "Description" column (row labelled "4") | Leave empty | - |  |
| Z17 | middle right, Goods table, row 4, "Qty ordered" column (row labelled "4") | Leave empty | - |  |
| Z18 | middle right, Goods table, row 4, "Qty received" column (row labelled "4") | Leave empty | - |  |
| Z19 | middle full-width, row of checkboxes under "Condition on arrival" | Tick the box:<br>`Some damaged` | Tick | Tick only this box. |
| Z20 | middle full-width, box under "Remarks" | Line 1:<br>`Toner: 2 boxes short. Supplier to`<br>Line 2:<br>`deliver the balance by 2 April.` | English |  |
| Z21 | lower left, box under "Received by (signature)" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z22 | lower right, box under "Receiver name" | `Omar Farouk` | English |  |


## F05  Bank Deposit Slip   (English, FIN)

File: F05_bank_deposit_slip.pdf (and F05_bank_deposit_slip.png). Dossier: FIN-C93-S1-F0001. Printed Ref: FIN/BD/2026/0058. Purpose: Cash count, cheques and total of a bank deposit: an amounts-heavy form.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Account name" | `Meridian Falak Group, Operating` | English |  |
| Z2 | top right, box under "Deposit date" | `12.03.2026` | Digits |  |
| Z3 | top left, box under "Account number" | `4471 0093 2258` | Digits |  |
| Z4 | top right, box under "Bank branch" | `Port Meridian Main` | English |  |
| Z5 | upper centre, Cash table, row 1, "Count" column (row labelled "200") | `12` | Digits |  |
| Z6 | upper right, Cash table, row 1, "Amount (EGP)" column (row labelled "200") | `2,400.00` | Digits |  |
| Z7 | upper centre, Cash table, row 2, "Count" column (row labelled "100") | `8` | Digits |  |
| Z8 | upper right, Cash table, row 2, "Amount (EGP)" column (row labelled "100") | `800.00` | Digits |  |
| Z9 | upper centre, Cash table, row 3, "Count" column (row labelled "50") | `15` | Digits |  |
| Z10 | upper right, Cash table, row 3, "Amount (EGP)" column (row labelled "50") | `750.00` | Digits |  |
| Z11 | middle centre, Cash table, row 4, "Count" column (row labelled "20") | `30` | Digits |  |
| Z12 | middle right, Cash table, row 4, "Amount (EGP)" column (row labelled "20") | `600.00` | Digits |  |
| Z13 | middle left, Cheques table, row 1, "Cheque no." column | `004512` | Digits |  |
| Z14 | middle centre, Cheques table, row 1, "Drawn on bank" column | `Nile Delta Bank` | English |  |
| Z15 | middle right, Cheques table, row 1, "Amount (EGP)" column | `3,200.00` | Digits |  |
| Z16 | middle left, Cheques table, row 2, "Cheque no." column | `004519` | Digits |  |
| Z17 | middle centre, Cheques table, row 2, "Drawn on bank" column | `Port Meridian Bank` | English |  |
| Z18 | middle right, Cheques table, row 2, "Amount (EGP)" column | `1,150.50` | Digits |  |
| Z19 | lower right, box under "TOTAL DEPOSIT (EGP)" | Write:<br>`8,090.50`<br>cross it out with one line, then write beside it:<br>`8,900.50` | Digits | CORRECTION. |
| Z20 | lower left, box under "Total in words" | `Eight thousand nine hundred and fifty (50/100)` | English |  |
| Z21 | lower left, box under "Depositor signature" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z22 | lower right, box under "Depositor name" | `Tarek Nabil` | English |  |


## F06  Petty Cash Voucher   (English + Arabic, FIN)

File: F06_petty_cash_voucher.pdf (and F06_petty_cash_voucher.png). Dossier: FIN-C93-S1-F0001. Printed Ref: FIN/PC/2026/0319. Purpose: Small cash payment with a mixed Arabic/English purpose line.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Date" | `12/03/2026` | Digits |  |
| Z2 | top centre, box under "Paid to" | `محمود عادل` | Arabic |  |
| Z3 | top right, box under "Amount (EGP)" | `86.50` | Digits |  |
| Z4 | top full-width, box under "Amount in words" | `Eighty-six and 50/100` | English |  |
| Z5 | upper full-width, box under "Purpose" | `رسوم شحن عبر FastRoute رقم 7741` | Arabic + English |  |
| Z6 | upper left, box under "Account code" | `6120-04` | Digits |  |
| Z7 | upper right, row of checkboxes under "Category" | Tick the box:<br>`Office / مكتبي` | Tick | Tick only this box. |
| Z8 | upper full-width, box under "Notes (margin note)" | `Receipt no. 4417 attached.` | English | Margin note. |
| Z9 | middle left, box under "Received by (signature)" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z10 | middle right, box under "Approved by (signature)" | Sign with your normal signature | Signature | Sign with a different, shorter signature. |


## F07  Weekly Timesheet   (English, HR)

File: F07_weekly_timesheet.pdf (and F07_weekly_timesheet.png). Dossier: HR-C92-S1-F0001. Printed Ref: HR/TS/2026/W11. Purpose: Hours worked Monday to Friday (a weekly grid with times and totals).


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Employee name" | `Layla Mansour` | English |  |
| Z2 | top centre, box under "Employee ID" | `EMP-20417` | English |  |
| Z3 | top right, box under "Week ending (Friday)" | `13/03/2026` | Digits |  |
| Z4 | upper centre, Timesheet table, row 1, "Start" column (row labelled "Mon 09/03") | `08:30` | Digits |  |
| Z5 | upper centre, Timesheet table, row 1, "End" column (row labelled "Mon 09/03") | `17:00` | Digits |  |
| Z6 | upper right, Timesheet table, row 1, "Break (min)" column (row labelled "Mon 09/03") | `30` | Digits |  |
| Z7 | upper right, Timesheet table, row 1, "Hours" column (row labelled "Mon 09/03") | `8.0` | Digits |  |
| Z8 | upper centre, Timesheet table, row 2, "Start" column (row labelled "Tue 10/03") | `08:45` | Digits |  |
| Z9 | upper centre, Timesheet table, row 2, "End" column (row labelled "Tue 10/03") | `17:15` | Digits |  |
| Z10 | upper right, Timesheet table, row 2, "Break (min)" column (row labelled "Tue 10/03") | `30` | Digits |  |
| Z11 | upper right, Timesheet table, row 2, "Hours" column (row labelled "Tue 10/03") | `8.0` | Digits |  |
| Z12 | upper centre, Timesheet table, row 3, "Start" column (row labelled "Wed 11/03") | `09:00` | Digits |  |
| Z13 | upper centre, Timesheet table, row 3, "End" column (row labelled "Wed 11/03") | `13:00` | Digits |  |
| Z14 | upper right, Timesheet table, row 3, "Break (min)" column (row labelled "Wed 11/03") | `0` | Digits |  |
| Z15 | upper right, Timesheet table, row 3, "Hours" column (row labelled "Wed 11/03") | `4.0` | Digits | Wednesday is a half day. |
| Z16 | upper centre, Timesheet table, row 4, "Start" column (row labelled "Thu 12/03") | `08:30` | Digits |  |
| Z17 | upper centre, Timesheet table, row 4, "End" column (row labelled "Thu 12/03") | `18:30` | Digits |  |
| Z18 | upper right, Timesheet table, row 4, "Break (min)" column (row labelled "Thu 12/03") | `60` | Digits |  |
| Z19 | upper right, Timesheet table, row 4, "Hours" column (row labelled "Thu 12/03") | `9.0` | Digits |  |
| Z20 | upper centre, Timesheet table, row 5, "Start" column (row labelled "Fri 13/03") | `08:30` | Digits |  |
| Z21 | upper centre, Timesheet table, row 5, "End" column (row labelled "Fri 13/03") | `16:30` | Digits |  |
| Z22 | upper right, Timesheet table, row 5, "Break (min)" column (row labelled "Fri 13/03") | `30` | Digits |  |
| Z23 | upper right, Timesheet table, row 5, "Hours" column (row labelled "Fri 13/03") | `7.5` | Digits |  |
| Z24 | middle left, box under "Notes (margin note)" | `Wed: dentist, left at 13:00.` | English | Margin note. |
| Z25 | middle right, box under "TOTAL HOURS" | `36.5` | Digits |  |
| Z26 | middle left, box under "Employee signature" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z27 | middle right, box under "Supervisor signature" | Sign with your normal signature | Signature | Sign with a different signature. |
| Z28 | middle full-width, row of checkboxes under "Supervisor decision" | Tick the box:<br>`Approved` | Tick | Tick only this box. |


## F08  Meeting Minutes   (English, FIN)

File: F08_meeting_minutes.pdf (and F08_meeting_minutes.png). Dossier: FIN-C94-S1-F0001. Printed Ref: FIN/MM/2026/0007. Purpose: Budget meeting: attendees, discussion with a margin-notes box, and an action-items table.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Meeting title" | `Q1 budget review` | English |  |
| Z2 | top centre, box under "Date" | `11 March 2026` | English |  |
| Z3 | top right, box under "Time" | `10:30` | Digits |  |
| Z4 | top left, box under "Location" | `Meeting Room 2` | English |  |
| Z5 | top right, box under "Attendees" | Line 1:<br>`Hana Saleh (chair), Omar Farouk,`<br>Line 2:<br>`Layla Mansour, Tarek Nabil` | English |  |
| Z6 | upper centre, box under "Discussion" | Line 1:<br>`Q1 budget ceiling set at 480,000.`<br>Line 2:<br>`Travel spend is 12% over plan.`<br>Line 3:<br>`Vendor contracts to be re-tendered.`<br>Line 4:<br>`Next meeting: 25/03/2026 at 10:00.` | English |  |
| Z7 | upper right, box under "Margin notes" | Line 1:<br>`check with Hana`<br>Line 2:<br>`re: travel 12%?` | English | Margin notes box. Write small. |
| Z8 | middle left, Actions table, row 1, "Action" column (row labelled "1") | `Prepare revised travel policy` | English |  |
| Z9 | middle right, Actions table, row 1, "Owner" column (row labelled "1") | `Omar Farouk` | English |  |
| Z10 | middle right, Actions table, row 1, "Due date" column (row labelled "1") | `20/03/2026` | Digits |  |
| Z11 | middle left, Actions table, row 2, "Action" column (row labelled "2") | `Send tender documents` | English |  |
| Z12 | middle right, Actions table, row 2, "Owner" column (row labelled "2") | `Tarek Nabil` | English |  |
| Z13 | middle right, Actions table, row 2, "Due date" column (row labelled "2") | `5 April 2026` | English |  |
| Z14 | middle left, Actions table, row 3, "Action" column (row labelled "3") | `Reconcile Q1 accruals` | English |  |
| Z15 | middle right, Actions table, row 3, "Owner" column (row labelled "3") | `Layla Mansour` | English |  |
| Z16 | middle right, Actions table, row 3, "Due date" column (row labelled "3") | `2026-03-31` | Digits |  |
| Z17 | lower left, box under "Chair signature" | Sign with your normal signature | Signature | Sign with your normal signature. |


## F09  Employee Information Update   (English + Arabic, HR)

File: F09_employee_info_update.pdf (and F09_employee_info_update.png). Dossier: HR-C92-S1-F0001. Printed Ref: HR/EI/2026/0094. Purpose: Employee corrects contact details and next of kin; mixed Arabic/English address.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Full name (English)" | `Layla Mansour` | English |  |
| Z2 | top right, box under "Full name (Arabic)" | `ليلى منصور` | Arabic |  |
| Z3 | top left, box under "Employee ID" | `EMP-20417` | English |  |
| Z4 | top centre, box under "Date of birth" | `04/09/1991` | Digits |  |
| Z5 | top right, box under "Effective from" | `1 April 2026` | English |  |
| Z6 | upper left, box under "Mobile" | Write:<br>`+20 100 555 0134`<br>cross it out with one line, then write beside it:<br>`+20 100 555 0143` | Digits | CORRECTION. |
| Z7 | upper right, box under "Email" | `layla.mansour@example.org` | English |  |
| Z8 | upper full-width, box under "Home address" | Line 1:<br>`Flat 12, 7 Garden Street,`<br>Line 2:<br>`الإسكندرية - Alexandria 21500` | Arabic + English |  |
| Z9 | middle full-width, row of checkboxes under "Marital status" | Tick the box:<br>`Married / متزوج` | Tick | Tick only this box. |
| Z10 | middle left, box under "Emergency contact" | `Samir Mansour` | English |  |
| Z11 | middle centre, box under "Relation" | `Brother` | English |  |
| Z12 | middle right, box under "Contact phone" | `+20 122 555 0198` | Digits |  |
| Z13 | middle left, box under "Employee signature" | Sign with your normal signature | Signature | Sign with your normal signature. |


## F10  Visitor Log   (English + Arabic, HR)

File: F10_visitor_log.pdf (and F10_visitor_log.png). Dossier: HR-C93-S1-F0001. Printed Ref: HR/VL/2026/0311. Purpose: Reception log: a table of visitors with times and signatures.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Date" | `12 Mar 2026` | English |  |
| Z2 | top centre, box under "Receptionist" | `Dina Yousef` | English |  |
| Z3 | top right, box under "Building" | `Block A` | English |  |
| Z4 | upper left, Visitors table, row 1, "Visitor" column (row labelled "1") | `Nadia Fawzy` | English |  |
| Z5 | upper centre, Visitors table, row 1, "Company" column (row labelled "1") | `Delta Print` | English |  |
| Z6 | upper centre, Visitors table, row 1, "Visiting" column (row labelled "1") | `Hana Saleh` | English |  |
| Z7 | upper right, Visitors table, row 1, "In" column (row labelled "1") | `09:05` | Digits |  |
| Z8 | upper right, Visitors table, row 1, "Out" column (row labelled "1") | `09:50` | Digits |  |
| Z9 | upper right, Visitors table, row 1, "Signature" column (row labelled "1") | Sign with your normal signature | Signature | Sign small, as a visitor would. |
| Z10 | upper left, Visitors table, row 2, "Visitor" column (row labelled "2") | `Robert Collins` | English |  |
| Z11 | upper centre, Visitors table, row 2, "Company" column (row labelled "2") | `BlueArch Audit` | English |  |
| Z12 | upper centre, Visitors table, row 2, "Visiting" column (row labelled "2") | `Omar Farouk` | English |  |
| Z13 | upper right, Visitors table, row 2, "In" column (row labelled "2") | `10:15` | Digits |  |
| Z14 | upper right, Visitors table, row 2, "Out" column (row labelled "2") | `12:40` | Digits |  |
| Z15 | upper right, Visitors table, row 2, "Signature" column (row labelled "2") | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z16 | upper left, Visitors table, row 3, "Visitor" column (row labelled "3") | `خالد إبراهيم` | Arabic | Arabic name. |
| Z17 | upper centre, Visitors table, row 3, "Company" column (row labelled "3") | `شركة النور` | Arabic | Arabic. |
| Z18 | upper centre, Visitors table, row 3, "Visiting" column (row labelled "3") | `ليلى منصور` | Arabic | Arabic. |
| Z19 | upper right, Visitors table, row 3, "In" column (row labelled "3") | `11:30` | Digits |  |
| Z20 | upper right, Visitors table, row 3, "Out" column (row labelled "3") | `11:55` | Digits |  |
| Z21 | upper right, Visitors table, row 3, "Signature" column (row labelled "3") | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z22 | upper left, Visitors table, row 4, "Visitor" column (row labelled "4") | Leave empty | - |  |
| Z23 | upper centre, Visitors table, row 4, "Company" column (row labelled "4") | Leave empty | - |  |
| Z24 | upper centre, Visitors table, row 4, "Visiting" column (row labelled "4") | Leave empty | - |  |
| Z25 | upper right, Visitors table, row 4, "In" column (row labelled "4") | Leave empty | - |  |
| Z26 | upper right, Visitors table, row 4, "Out" column (row labelled "4") | Leave empty | - |  |
| Z27 | upper right, Visitors table, row 4, "Signature" column (row labelled "4") | Leave empty | - |  |
| Z28 | middle left, box under "Visitors today" | `3` | Digits |  |
| Z29 | middle right, row of checkboxes under "All badges returned" | Tick the box:<br>`Yes / نعم` | Tick | Tick only this box. |


## F11  Vehicle Maintenance Log   (English, FIN)

File: F11_vehicle_maintenance_log.pdf (and F11_vehicle_maintenance_log.png). Dossier: FIN-C94-S1-F0001. Printed Ref: FIN/VM/2026/0045. Purpose: Service history of one fleet vehicle with costs.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Vehicle ID" | `FLT-07` | English |  |
| Z2 | top centre, box under "Plate" | `KLM 7305` | English |  |
| Z3 | top right, box under "Odometer today (km)" | `84,215` | Digits |  |
| Z4 | upper left, Service history table, row 1, "Date" column | `15/01/2026` | Digits |  |
| Z5 | upper left, Service history table, row 1, "Odometer (km)" column | `81,030` | Digits |  |
| Z6 | upper centre, Service history table, row 1, "Service performed" column | `Oil and filter change` | English |  |
| Z7 | upper right, Service history table, row 1, "Cost (EGP)" column | `420.00` | Digits |  |
| Z8 | upper right, Service history table, row 1, "Garage" column | `Al Amal Garage` | English |  |
| Z9 | upper left, Service history table, row 2, "Date" column | `2 Feb 2026` | English |  |
| Z10 | upper left, Service history table, row 2, "Odometer (km)" column | `82,540` | Digits |  |
| Z11 | upper centre, Service history table, row 2, "Service performed" column | `Front brake pads` | English |  |
| Z12 | upper right, Service history table, row 2, "Cost (EGP)" column | `1,180.00` | Digits |  |
| Z13 | upper right, Service history table, row 2, "Garage" column | `Al Amal Garage` | English |  |
| Z14 | upper left, Service history table, row 3, "Date" column | `02/03/2026` | Digits |  |
| Z15 | upper left, Service history table, row 3, "Odometer (km)" column | `84,015` | Digits |  |
| Z16 | upper centre, Service history table, row 3, "Service performed" column | `Tyre rotation` | English |  |
| Z17 | upper right, Service history table, row 3, "Cost (EGP)" column | `150.00` | Digits |  |
| Z18 | upper right, Service history table, row 3, "Garage" column | `QuickFit Port` | English |  |
| Z19 | upper left, Service history table, row 4, "Date" column | Leave empty | - |  |
| Z20 | upper left, Service history table, row 4, "Odometer (km)" column | Leave empty | - |  |
| Z21 | upper centre, Service history table, row 4, "Service performed" column | Leave empty | - |  |
| Z22 | upper right, Service history table, row 4, "Cost (EGP)" column | Leave empty | - |  |
| Z23 | upper right, Service history table, row 4, "Garage" column | Leave empty | - |  |
| Z24 | middle left, box under "TOTAL COST (EGP)" | `1,750.00` | Digits |  |
| Z25 | middle centre, box under "Next service at (km)" | `90,000` | Digits |  |
| Z26 | middle right, box under "Next service month" | `June 2026` | English |  |
| Z27 | middle full-width, row of checkboxes under "Roadworthy" | Tick the box:<br>`Yes` | Tick | Tick only this box. |
| Z28 | middle left, box under "Mechanic remarks (margin note)" | `Squeak from rear left, recheck.` | English | Margin note. |
| Z29 | middle right, box under "Mechanic name" | `Youssef Barakat` | English |  |
| Z30 | lower left, box under "Mechanic signature" | Sign with your normal signature | Signature | Sign with your normal signature. |


## F12  Invoice Approval Sheet   (English, FIN)

File: F12_invoice_approval_sheet.pdf (and F12_invoice_approval_sheet.png). Dossier: FIN-C92-S1-F0001. Printed Ref: FIN/IA/2026/0188. Purpose: Stamp box and three signature blocks that approve a supplier invoice.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top left, box under "Supplier" | `Sunrise Office Supplies Ltd` | English |  |
| Z2 | top centre, box under "Invoice no." | `INV-55120` | English |  |
| Z3 | top right, box under "Invoice date" | `18 March 2026` | English |  |
| Z4 | top left, box under "PO number" | `PO-2026-0417` | English |  |
| Z5 | top centre, box under "Invoice amount (EGP)" | `1,102.20` | Digits |  |
| Z6 | top right, box under "Payment due" | `19 April 2026` | English |  |
| Z7 | upper full-width, row of checkboxes under "Three-way match" | Tick the box:<br>`Variance explained below` | Tick | Tick only this box. |
| Z8 | upper left, box under "Received stamp (write in capitals)" | Line 1:<br>`RECEIVED`<br>Line 2:<br>`20 MAR 2026`<br>Line 3:<br>`FINANCE PORT MERIDIAN` | English | Stands in for a rubber stamp. Capitals. |
| Z9 | upper right, box under "Variance explanation" | Line 1:<br>`Toner billed for 4 units, not 6.`<br>Line 2:<br>`2 units outstanding on the PO.` | English | Hand-written explanation. |
| Z10 | middle left, box under "Prepared by (signature)" | Sign with your normal signature | Signature | Sign with your normal signature; use a different style for each role. |
| Z11 | middle left, box under "Prepared by (name)" | `Layla Mansour` | English |  |
| Z12 | middle left, box under "Prepared by (date)" | `20/03/2026` | Digits |  |
| Z13 | middle centre, box under "Checked by (signature)" | Sign with your normal signature | Signature | Sign with your normal signature; use a different style for each role. |
| Z14 | middle centre, box under "Checked by (name)" | `Omar Farouk` | English |  |
| Z15 | middle centre, box under "Checked by (date)" | `21 Mar 2026` | English |  |
| Z16 | middle right, box under "Approved by (signature)" | Sign with your normal signature | Signature | Sign with your normal signature; use a different style for each role. |
| Z17 | middle right, box under "Approved by (name)" | `Hana Saleh` | English |  |
| Z18 | middle right, box under "Approved by (date)" | `2026-03-22` | Digits |  |


## F13  Cheque Request   (Arabic, FIN)

File: F13_cheque_request_ar.pdf (and F13_cheque_request_ar.png). Dossier: FIN-C92-S1-F0001. Printed Ref: FIN/CQ/2026/0231. Purpose: Arabic form: request to pay the supplier invoice by cheque.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top right, box under "Beneficiary" | `صن رايز لمستلزمات المكاتب` | Arabic |  |
| Z2 | top left, box under "Request date" | `١٢/٠٣/٢٠٢٦` | Arabic-Indic digits |  |
| Z3 | upper right, box under "Amount in figures (EGP)" | Write:<br>`١٢٣٠.٦٠`<br>cross it out with one line, then write beside it:<br>`١١٠٢.٢٠` | Arabic-Indic digits | CORRECTION. |
| Z4 | upper left, box under "Amount in words" | `ألف ومئة وجنيهان وعشرون قرشاً` | Arabic |  |
| Z5 | upper right, box under "Invoice number" | `INV-55120` | English |  |
| Z6 | upper left, box under "Reason for payment" | Line 1:<br>`سداد فاتورة مستلزمات مكتبية`<br>Line 2:<br>`حسب أمر الشراء PO-2026-0417` | Arabic + English |  |
| Z7 | upper full-width, row of checkboxes under "Payment method" | Tick the box:<br>`شيك (Cheque)` | Tick | Tick only this box. |
| Z8 | middle right, box under "Requested by (signature)" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z9 | middle left, box under "Requester name" | `عمر فاروق` | Arabic |  |
| Z10 | middle right, box under "Finance manager decision (margin note)" | `يُسلَّم الشيك للمورد يداً بيد` | Arabic | Margin note. |
| Z11 | middle left, box under "Approval date" | `٢١ مارس ٢٠٢٦` | Arabic |  |
| Z12 | lower right, box under "Finance manager (signature)" | Sign with your normal signature | Signature | Sign with a different signature. |
| Z13 | lower left, box under "Manager name" | `هناء صالح` | Arabic |  |


## F14  Official Memorandum   (Arabic, HR)

File: F14_official_memorandum_ar.pdf (and F14_official_memorandum_ar.png). Dossier: HR-C93-S1-F0001. Printed Ref: HR/MEM/2026/0072. Purpose: Arabic memo (printed text) with a handwritten decision box.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | upper centre, box under "Decision" | Line 1:<br>`تمت الموافقة على التعميم`<br>Line 2:<br>`يُنفَّذ اعتباراً من ٠١/٠٦/٢٠٢٦`<br>Line 3:<br>`يُعمَّم على جميع الإدارات.` | Arabic |  |
| Z2 | upper left, box under "Margin note" | Line 1:<br>`للمتابعة مع`<br>Line 2:<br>`شؤون الموظفين` | Arabic | Margin note, small. |
| Z3 | middle right, box under "Issue number" | `٢٠٢٦/٠٧٢` | Arabic-Indic digits |  |
| Z4 | middle left, box under "Date" | `٢٠٢٦/٠٣/١٥` | Arabic-Indic digits |  |
| Z5 | middle right, box under "General manager (signature)" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z6 | middle left, box under "Name" | `هبة الشريف` | Arabic |  |


## F15  Leave Request   (Arabic, HR)

File: F15_leave_request_ar.pdf (and F15_leave_request_ar.png). Dossier: HR-C93-S1-F0001. Printed Ref: HR/LV/2026/0418. Purpose: Arabic leave request with Arabic-Indic digits and a manager decision.


| Zone | Where on the page | Write exactly | Language | Note |
| --- | --- | --- | --- | --- |
| Z1 | top right, box under "Employee name" | `سامي عبد الله` | Arabic |  |
| Z2 | top centre, box under "Employee ID" | `٣١٩٥٢` | Arabic-Indic digits |  |
| Z3 | top left, box under "Department" | `المحاسبة` | Arabic |  |
| Z4 | upper full-width, row of checkboxes under "Leave type" | Tick the box:<br>`مرضية (Sick)` | Tick | Tick only this box. |
| Z5 | upper right, box under "From" | `٠٢/٠٤/٢٠٢٦` | Arabic-Indic digits |  |
| Z6 | upper centre, box under "To" | `٠٦/٠٤/٢٠٢٦` | Arabic-Indic digits |  |
| Z7 | upper left, box under "Days" | `٥` | Arabic-Indic digits |  |
| Z8 | upper full-width, box under "Reason" | Line 1:<br>`وعكة صحية، مرفق تقرير طبي`<br>Line 2:<br>`من مستشفى الأمل رقم 5521` | Arabic |  |
| Z9 | middle right, box under "Employee signature" | Sign with your normal signature | Signature | Sign with your normal signature. |
| Z10 | middle left, box under "Date" | `٢٨ مارس ٢٠٢٦` | Arabic |  |
| Z11 | middle full-width, row of checkboxes under "Decision" | Tick the box:<br>`موافق (Approved)` | Tick | Tick only this box. |
| Z12 | lower right, box under "Manager remarks (margin note)" | `موافق مع تمنياتنا بالشفاء` | Arabic | Margin note. |
| Z13 | lower left, box under "Manager name" | `هناء صالح` | Arabic |  |

