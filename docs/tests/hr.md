# HR tests: upload, questions, and department isolation

Seven HR dossiers: three typed, two of filled forms (one of them partial), two of handwriting. Huda uploads them (department `HR`) and asks the questions. Rana, who is a steward for both departments, handles hints and escalated review tasks. Layla and Sara must never see HR content. Paths are relative to `samples/dossiers/<document-type>/`.

**People.** Huda is the HR expert: role Expert, with the HR readers and HR experts groups. She uploads HR dossiers, settles HR review tasks, asks HR questions and submits HR hints. Rana holds the Steward role with the Finance and HR readers and stewards groups, so she settles escalated HR tasks and approves HR hints. Sara stays a Finance expert, Layla a Finance reader, Yousef the admin.

**Before you start.** The HR experts and HR stewards groups exist on Azure, and Huda and Rana were added to them (deploy steps 41, 42 and 60 are done; no new image was needed). Huda and Rana must **sign out and in again** so their tokens carry the new groups. The access checks in this file are the code's rules; they have not been run on Azure yet.

## 1. Upload the HR dossiers

1. Sign in as **Huda** in a private window.
2. Open **Upload**. Change **Department** to `HR` (it is pre-filled with `FIN`). Leave **Mode** on **By dossier**. Type the dossier ID. Choose the files listed. Never choose a `dossier.json`, an answer key or a questions file.
3. **Check files**, then **Confirm and upload**. Wait until the dossier shows `completed`.
4. Lines the system is unsure of become review tasks. They go to Huda under **Review**: she is the only HR expert. Tasks that were abandoned three times are escalated to Rana, who takes them from **Review**, **Escalated tasks**.
5. Run the questions below as Huda (Ask, in the language shown).
6. Then run section 3 with the other people. Sara and Layla must still be able to do their Finance work.

Run the dossiers in this order. Typed first, forms next, handwriting last, because handwriting costs an OCR call per page and a vision call per handwritten line.

For the typed dossiers select the files listed from their folder under `samples/dossiers/typed/`. For the forms and the handwriting, open the dossier's folder under `samples/dossiers/forms/` or `samples/dossiers/handwritten/` and select all its files.

| Order | Dossier ID        | Files                                                                       | Kind                      | State                                                                                       |
| ----- | ----------------- | --------------------------------------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------- |
| 1     | `HR-C90-S1-F0001` | `typed/HR-C90-S1-F0001/scan_001.pdf`, `OFR-2026-031.docx`                   | typed, English            | complete                                                                                    |
| 2     | `HR-C90-S1-F0002` | `typed/HR-C90-S1-F0002/scan_001.pdf`, `LV-2026-142.docx`, `TR-2026-009.txt` | typed, Arabic             | complete                                                                                    |
| 3     | `HR-C91-S1-F0003` | `typed/HR-C91-S1-F0003/scan_001.tif`, `TA-2026-021.docx`                    | typed, Arabic and English | complete                                                                                    |
| 4     | `HR-C92-S1-F0001` | folder `forms/dossiers/HR-C92-S1-F0001/`: F01, F07, F09                     | filled forms              | complete                                                                                    |
| 5     | `HR-C93-S1-F0001` | folder `forms/dossiers/HR-C93-S1-F0001/`: F10                               | filled form               | partial: two Arabic forms of this dossier do not exist yet, so only questions 4 and 5 apply |
| 6     | `HR-C95-S1-F0001` | folder `handwritten/dossiers/HR-C95-S1-F0001/`: HW01, HW05, HW11            | handwriting               | complete                                                                                    |
| 7     | `HR-C96-S1-F0001` | folder `handwritten/dossiers/HR-C96-S1-F0001/`: HW07, HW15, HW17            | handwriting               | complete                                                                                    |

## 2. HR questions (ask as Huda)

Types: **numeric**, **correction**, **not in documents** (the answer must be that the documents do not say), **cross-department** (a Finance fact: Huda must get no access or nothing found, and the value must not appear).

### HR-C90-S1-F0001: English payroll, leave policy, offer letter

| #   | Language | Question                                                                                       | Expected answer                                                                                 | Type                         |
| --- | -------- | ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ---------------------------- |
| 1   | EN       | What was the total net pay for April 2026 and for how many staff?                              | AED 41,515.00 for 27 staff (gross 43,700.00, deductions 2,185.00). Scan page 1, Payroll Summary | numeric                      |
| 2   | EN       | How many calendar days of annual leave does an employee get, and how many can be carried over? | 30 calendar days per year; up to 10 days. Scan page 2, Annual Leave Policy                      | numeric                      |
| 3   | AR       | كم يبلغ إجمالي الراتب الشهري المعروض على خالد منصور؟                                           | 8,400 درهم (6,200 plus 1,800 plus 400), from the English offer letter                           | numeric, Arabic over English |
| 4   | AR       | ما معامل أجر العمل الإضافي في أيام الراحة؟                                                     | 1.5 مرة من الأجر الساعي الاعتيادي. Scan page 2                                                  | numeric                      |
| 5   | EN       | Which company provides the employee pension scheme?                                            | Not in the documents (only a 5% pension and insurance contribution is mentioned)                | not in documents             |
| 6   | EN       | What is the total on invoice INV-2026-1187?                                                    | Finance fact: no access. AED 50,835.75 must not appear                                          | cross-department             |

### HR-C90-S1-F0002: Arabic circular, employment certificate, leave notice, training notice

| #   | Language | Question                                                                                      | Expected answer                                                                  | Type                         |
| --- | -------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------------------- |
| 1   | AR       | متى يبدأ العمل بساعات الدوام الصيفي ومتى ينتهي؟                                               | من 15 يونيو 2026 إلى 15 سبتمبر 2026. Scan page 1, circular                       | date                         |
| 2   | AR       | ما الراتب الإجمالي لياسر الحداد وكم بدل السكن؟                                                | 9,750 درهم؛ بدل السكن 2,200 درهم. Scan page 2, employment certificate            | numeric                      |
| 3   | EN       | How many days of leave were approved for Yasser Al Haddad and what is his balance afterwards? | 19 calendar days (6 to 24 July 2026); 5 days left. English over an Arabic notice | numeric, English over Arabic |
| 4   | EN       | How many seats does the safety course have and what is the pass mark?                         | 25 seats; pass mark 70%. English over an Arabic notice                           | numeric, English over Arabic |
| 5   | AR       | ما اسم المدير المباشر لياسر الحداد؟                                                           | Not in the documents                                                             | not in documents             |
| 6   | AR       | كم الأجرة الشهرية للمستودع رقم 14؟                                                            | Finance fact: no access. 19,240 must not appear                                  | cross-department             |

### HR-C91-S1-F0003: mixed Arabic and English

| #   | Language | Question                                                                       | Expected answer                                                                                  | Type             |
| --- | -------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ | ---------------- |
| 1   | EN       | What is Nadia Farouk's monthly salary and start date?                          | AED 12,500 (12,500 درهم); 15 August 2026. Scan page 1, Employment Contract Extract               | numeric, date    |
| 2   | AR       | ما نسبة الحضور الإجمالية في مايو 2026 وكم عدد حالات التأخر؟                    | 95.2% وعدد حالات التأخر 31. The source uses Arabic-Indic digits. Scan page 2, Attendance Summary | numeric          |
| 3   | EN       | What was the average score in the safety course session 1 and how many passed? | Average 78.5%; 5 of 6 passed (pass mark 70%)                                                     | numeric          |
| 4   | AR       | أي قسم لديه أدنى نسبة حضور وهل هي دون حد التنبيه؟                              | قسم المستودع (91.5%)، نعم دون حد التنبيه 93%                                                     | text             |
| 5   | EN       | What is Nadia Farouk's home address?                                           | Not in the documents                                                                             | not in documents |
| 6   | EN       | What is the 2% contingency reserve in payment schedule PS-2026-014?            | Finance fact: no access. AED 801.65 must not appear                                              | cross-department |

### HR-C92-S1-F0001: English HR forms (F01, F07, F09)

| #   | Language | Question                                                                                                            | Expected answer                                                                                                                                                           | Type                  |
| --- | -------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| 1   | EN       | How many working days of leave did Layla Mansour request, and from when to when?                                    | 7 working days, 12/03/2026 to 20/03/2026 (the end date is written this way on the form)                                                                                   | numeric, dates        |
| 2   | EN       | Was the leave approved, and what did the manager remark?                                                            | Approved. 'Approved. Omar to cover the approvals queue.'                                                                                                                  | checkbox, margin note |
| 3   | EN       | How many hours did she work in the week ending 13/03/2026?                                                          | 36.5 hours (the written total). The written start and end times do not add up to it: see question 7                                                                       | numeric               |
| 4   | EN       | What is Layla Mansour's mobile number?                                                                              | +20 100 555 0143. A number on the update form is crossed out and the corrected one written; the corrected one is the answer                                               | correction, digits    |
| 5   | AR       | ما اسم جهة الاتصال في حالات الطوارئ وما صلتها بالموظفة؟                                                             | Samir Mansour, brother (أخ). Arabic question over a bilingual form                                                                                                        | text                  |
| 6   | EN       | What is Layla Mansour's salary grade?                                                                               | Not in the documents                                                                                                                                                      | not in documents      |
| 7   | EN       | On Monday of the week ending 13/03/2026, when did Layla Mansour finish and how many hours are recorded for the day? | Finish 15:00 and 8.0 hours, as written. The two disagree (08:30 to 15:00 less 30 minutes is 6.0 hours), so the answer should give both and not compute one from the other | inconsistent entry    |
| 8   | EN       | What is Layla Mansour's email address?                                                                              | layla.mansour@example.com, as written                                                                                                                                     | text                  |

### HR-C93-S1-F0001: visitor log (partial)

Only the visitor log (F10) exists. Questions 1 to 3 need two Arabic forms that are not in the sample folder, so skip them.

| #   | Language | Question                                                                                 | Expected answer                                                       | Type             |
| --- | -------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------- | ---------------- |
| 4   | EN       | How many visitors are in the visitor log of 12 Mar 2026, and who came to see Hana Saleh? | 3 visitors; Nadia Fawzy of Delta Print. English over a bilingual form | numeric          |
| 5   | EN       | What is the visitor's car registration number?                                           | Not in the documents                                                  | not in documents |

### HR-C95-S1-F0001: resignation, leave request, employment letter (handwriting)

| #   | Language | Question                                                   | Expected answer                                                                                              | Type             |
| --- | -------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ---------------- |
| 1   | EN       | What is Khaled Nasser's last working day?                  | 14 January 2027 (HW01)                                                                                       | date             |
| 2   | AR       | كم يوما طلبت ليلى الخطيب كإجازة سنوية ومتى تعود إلى العمل؟ | 10 working days; she returns on Sunday 20 December 2026. The dates are written in Arabic-Indic digits (HW05) | numeric, date    |
| 3   | AR       | ما إجمالي الراتب الشهري المعروض على السيد العلي؟           | 3,400 USD (2,800 basic plus 600 housing) (HW11)                                                              | numeric          |
| 4   | EN       | When does Mr Al-Ali's probation period end?                | 3 April 2027 (HW11)                                                                                          | date             |
| 5   | EN       | Why is Khaled Nasser resigning?                            | Not in the documents: the letter gives no reason                                                             | not in documents |

### HR-C96-S1-F0001: onboarding note, overtime with margin note, Arabic minutes (handwriting)

| #   | Language | Question                                                                        | Expected answer                                                                  | Type             |
| --- | -------- | ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ---------------- |
| 1   | EN       | Which laptop model will the new employee receive and what does it cost?         | Model LT-5520, 1,150 USD (HW07)                                                  | numeric          |
| 2   | EN       | What is the total overtime amount for the warehouse team in November 2026?      | 2,592.00 USD (144 hours at 18.00) (HW15)                                         | numeric          |
| 3   | EN       | Was the overtime approved, by whom and when? (the answer is in the margin note) | Yes: approved by R.M. on 18/11/2026, to be paid with the November payroll (HW15) | margin note      |
| 4   | AR       | كم بلغت التكلفة الإجمالية لدورة السلامة المهنية؟                                | 1,800 USD for 12 trainees (HW17)                                                 | numeric          |
| 5   | AR       | من هو المدرب الذي سيقدم دورة السلامة المهنية؟                                   | Not in the documents: the minutes only say the trainer must still be confirmed   | not in documents |

## 3. Department isolation and roles

A refusal means the answer says it cannot find it, or that you have no access, and shows **none** of the facts named in "Must not show". Before any refusal test, ask the same question as the person who owns the document and confirm it is answered, otherwise a refusal proves nothing.

### Reader isolation

| #   | Person                 | Language | Question                                                                                                 | Correct result                      | Must not show                                |
| --- | ---------------------- | -------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------- | -------------------------------------------- |
| I1  | Layla (Finance reader) | EN       | Who is the trainer of the occupational safety course, and how many seats does it have?                   | Refused: no access or nothing found | Dr Hala Samir (الدكتورة هالة سمير), 25 seats |
| I2  | Layla                  | AR       | كم بلغ صافي الرواتب المدفوعة عن شهر أبريل 2026؟                                                          | Refused                             | 41,515.00 and 27 staff                       |
| I3  | Layla                  | EN       | What is Khaled Nasser's last working day? (only after `HR-C95-S1-F0001` is uploaded)                     | Refused                             | 14 January 2027                              |
| I4  | Huda (HR expert)       | EN       | What was the closing balance in the May 2026 bank statement?                                             | Refused                             | 173,839.25                                   |
| I5  | Huda                   | AR       | ما هي ميزانية الربع الثالث لعام 2026؟                                                                    | Refused                             | 450,000 درهم / ٤٥٠٬٠٠٠                       |
| I6  | Huda                   | EN       | What did Bluewave Marine's invoice INV-5520 charge in total? (only after `FIN-C95-S1-F0001` is uploaded) | Refused                             | 740.00 USD                                   |

### Role and upload checks

| #   | Person                     | Action                                                                                                                                                                                             | Correct result                                                                                                                                                                                                                                       |
| --- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Sara (Finance expert)      | Upload, department `HR`, ID `HR-C90-S1-F0001`, **Check files**                                                                                                                                     | Refused: "You are not allowed to do that."                                                                                                                                                                                                           |
| R2  | Huda                       | Upload, department `FIN`, ID `FIN-C90-S1-F0001`, **Check files**                                                                                                                                   | Refused, same message                                                                                                                                                                                                                                |
| R3  | Huda                       | Upload, department `HR`, ID `FIN-C90-S1-F0001`                                                                                                                                                     | Rejected at **Check files**: the dossier ID must have the shape of a barcode and start with HR                                                                                                                                                       |
| R4  | Sara                       | Upload, department `FIN`, ID `HR-C90-S1-F0001`                                                                                                                                                     | Rejected at **Check files**: the ID must start with FIN                                                                                                                                                                                              |
| R5  | Yousef (Admin)             | Ask any question, for example "What is the total on invoice INV-2026-1187?"                                                                                                                        | No access: "You are not allowed to do that." The admin sees no document content                                                                                                                                                                      |
| R6  | Layla                      | Copy a **Sources** link from Huda's answer to an HR question (it looks like `/citation?chunk=HR-...&line=p001/L1`) and open it while signed in as Layla                                            | The page says "This citation was not found, or you are not allowed to see it." with no page image. The same must happen for Sara                                                                                                                     |
| R7  | Sara, then Huda            | Open **Review** after both a Finance and an HR dossier have review tasks                                                                                                                           | Sara sees only Finance tasks, Huda only HR tasks                                                                                                                                                                                                     |
| R8  | Rana                       | Open **Hints** and **Review** while HR hints await approval and HR escalated tasks exist                                                                                                           | She sees the HR hints awaiting approval and the HR escalated tasks, together with any Finance ones, and can settle them                                                                                                                              |
| R9  | Huda, then Rana, then Huda | Huda submits an HR hint (from an HR answer: **Add expert hint**; change the **Department** field to `HR`, it is pre-filled with `FIN`). Rana opens **Hints** and approves it. Huda opens **Inbox** | The Inbox shows "Your hint was approved by ... and is now used in answers"                                                                                                                                                                           |
| R10 | Sara, then Layla           | While the HR hint of R9 awaits approval, open **Hints** and **Inbox**                                                                                                                              | Neither sees the hint or an Approve button. Sara has no steward rights; Layla is a reader                                                                                                                                                            |
| R11 | Rana                       | Try to submit an HR hint herself                                                                                                                                                                   | Not possible in the web app: the hint form is shown to the Expert role only, and Rana is a steward. Record that. The four-eyes rule (the store also refuses an author approving their own hint) is covered in the access tests of the code, not here |
| R12 | Rana (API or script only)  | Restrict an HR dossier to the HR stewards group through `POST /api/dossiers/{id}/acl` (the web app has no page for this)                                                                           | Layla still cannot see it (R6 stays refused). Huda loses sight of it unless her group is in the list                                                                                                                                                 |

### Languages over HR documents

| #   | Person | Language                     | Question                                                           | Correct result                                                                                   |
| --- | ------ | ---------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| L1  | Huda   | EN, over an Arabic document  | Where is the safety course held, and at what time on 21 June 2026? | Hall 2 (القاعة 2), 9:00 am to 1:00 pm (`TR-2026-009.txt`, dossier `HR-C90-S1-F0002`)             |
| L2  | Huda   | AR, over an English document | ما مسمى الوظيفة المعروضة على خالد منصور وما تاريخ مباشرته؟         | Warehouse Supervisor (مشرف مستودع), 1 July 2026 (`OFR-2026-031.docx`, dossier `HR-C90-S1-F0001`) |

## Open points

- **Not run on Azure.** No HR upload has run yet. The expected refusal wording in R1 to R5 comes from the code (the access rules, the upload check and the web error text), not from a run.
- **R6** relies on the new page view returning 404 outside the reader's scope; no real HR chunk link has been opened. Copy the chunk ID from an answer.
- **R7 to R12** follow from the access rule (a capability needs the role and that department's own group) and the hint rules. They are untried on Azure. R12 is API only and its exact effect on Huda depends on the group list you send.
- **The forms and handwriting answers** were read off the scans by eye, not by the system. They may need a second look after the first real run.
- **The typed sample question file** says dossiers are uploaded as Sara. For the HR dossiers that is now Huda; Sara is refused.
