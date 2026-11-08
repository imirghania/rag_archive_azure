# Access, review, hints and what to do when something fails

The question-and-answer tests live in the Finance and HR files. This one covers the behaviour around them: who may do what, how a doubtful line gets settled, how an expert hint reaches an answer, how to run a dossier again, what each status means, and where to look when something stops. It is based on the code and the web pages. Where a thing could not be confirmed it says so.

## 1. Departments are separate, both ways

The principle: what a person sees comes from the groups in their sign-in token. Each dossier is readable by its department's reader group. The search index filters on those groups, so another department's text is never even retrieved for the question, and the review tasks in the database are protected by row-level security, so a task of another department is invisible and not just refused. A citation link to another department's page answers "This citation was not found, or you are not allowed to see it." The same message is used for a link that does not exist, so it tells a guesser nothing.

To check it, run the isolation questions I1 to I6 and the link test R6 in the HR file. Both directions matter: a Finance reader must not get an HR fact, and an HR expert must not get a Finance fact.

## 2. Roles: what each person may do

A capability is the role together with the department's own group. Check each row by trying it, and check that the other rows are refused.

- **Reader (Layla).** Ask only. The menu shows **Ask** and **Inbox**. No Upload, Review or Hints page.
- **Expert (Sara for Finance, Huda for HR).** Ask, upload, settle ordinary review tasks, submit hints. The menu shows **Ask, Upload, Review, Hints, Inbox**. An expert cannot approve hints and cannot take escalated tasks.
- **Steward (Rana, for Finance and HR).** Ask (she is also a reader), approve, reject or revoke hints, take escalated review tasks, restrict who may read a dossier. The menu shows **Ask, Review, Hints, Inbox**. The Review page of a steward also has an **Escalated tasks** button. A steward cannot upload, and the hint form is not shown to her, because it is for experts.
- **Admin (Yousef).** The **Admin** page with dossier status and a **Reprocess** button per dossier, plus the **Inbox** (he is told about failed and partial dossiers and rejected uploads). He has no access to documents: asking a question gives "You are not allowed to do that."

Anyone without the role or the department group is refused with "You are not allowed to do that." at upload, review and hints.

## 3. Review tasks: a doubtful line gets a person

When two readers of a handwritten line disagree, or a digit is doubtful, or the system cannot trust a line, the line becomes a review task for the department's experts. Until someone settles it, the line cannot be quoted: a question that depends on it gets "A handwritten note on this subject exists, but its content is still awaiting expert verification, so I cannot state it yet." This is correct, not a bug.

Run it as the department's expert (Sara for Finance, Huda for HR):

1. Open **Review** and press **Next task**. The page shows the dossier, page and line, the reason, a crop of the line and a crop with the lines around it, a table of what each reader read, and sometimes a suggested correction. If no task is open it says "No open task for you right now."
2. You hold the task for a lease of 15 minutes. The page renews the lease while it is open. Close the page and the lease runs out, and the task goes back to the pool. A task abandoned three times is escalated to a steward.
3. Decide with one button: **Accept OCR** (the first reader's text), **Accept second reader** (the vision model's text), **Illegible**, or type the correct text and press **Use my text**. A correction needs text.
4. The decision is written once and can never be overwritten. If you decide after the lease ran out, the page tells you the task was reassigned and nothing is recorded.
5. After a decision the page is saved again as a new version with that line's final text and a trust level of human-verified (or illegible), and the dossier is indexed again. Ask the question again: the answer changes from "awaiting expert verification" to the value.

Check three things: another person cannot decide your task (they get "reassigned"), the decision shows in the next answer, and an HR expert never sees a Finance task (R7 in the HR file).

Escalated tasks: take the task as Rana (**Review**, **Escalated tasks**). She also gets an Inbox message "Review task N needs a steward" when one is escalated. The announcement is sent when someone next claims a task, so it can come late.

The two checks that need real handwriting to disagree are not in the typed or form dossiers. They depend on the handwriting sheets, and whether a given sheet produces a task depends on what the models read. Treat "a review task appears for a doubtful handwritten line" as something to look for in the handwriting dossiers, not a guaranteed result.

## 4. Expert hints

A hint is a short note from a domain expert that the system can use in answers later (a context note or a terminology entry with its terms). It needs a second person to approve it: nobody approves their own.

1. An expert opens **Hints** (or the **Add expert hint** link under an abstention) and fills in the form: **Department** (pre-filled with `FIN`: type `HR` for an HR hint), type, text, terms for terminology, and optionally a chunk ID and line as evidence. The chunk ID can be copied from an answer's source link. Press **Submit**.
2. The hint waits for approval. The steward sees it under **Hints**, **Waiting for your approval**, with its text, who wrote it, whether it has documentary evidence, the automatic checks and how many groups will be able to read it.
3. The steward presses **Approve**, or enters a reason and presses **Reject**. A rejection needs a reason, because the author is told why.
4. The author's **Inbox** shows "Your hint was approved by ... and is now used in answers" (or "Your hint ... was not accepted", with the reason). A steward can later revoke an approved hint; an expert cannot, not even their own.
5. Ask the question the hint is about: the answer can now use the note, and it is limited to the people who may read the hint's department.

Things to confirm: Sara (Finance expert) and Layla do not see Huda's HR hint and have no Approve button. Rana cannot be tested as an author in the web app. An approved Finance hint does not help an HR question.

A hint can also propose a corrected text for a line; that is API only and is not covered here.

## 5. Abstentions and refusals

- **A fact that is not in the documents.** The text says it could not find supporting evidence in the documents you have access to. Experts also see **Add expert hint**.
- **Part of an answer could not be verified.** The answer leaves that part out and says so at the end.
- **A question that is not about the documents.** It is declined with one line saying what the system answers (letters, contracts, memos and similar).
- **A question the safety filter will not process.** The answer is "I could not process this question."
- **Another department's facts.** No access or nothing found, and none of the values.
- **A document with a planted instruction.** The code removes such a chunk before the model sees it, excludes it for everyone and leaves it for a steward to judge. No sample document in the test pack contains a planted instruction, so this is untested here; it needs a document written for it.

## 6. Reprocess a dossier

Use it after a fix, or to see that a dossier can be run again.

1. Sign in as Yousef and open **Admin**.
2. Find the dossier and press **Reprocess**. It starts a new revision from the files already uploaded (no new upload).
3. The table shows the dossier again with `r2` (then `r3`, and so on). While the new revision is built the older one is still the one that answers. When the new one is complete, it replaces the old one and the old one becomes `superseded`.
4. Only the admin can do this: Rana or Sara get "You are not allowed to do that."

Uploading an existing dossier ID again also makes a new revision.

## 7. What each status means

Dossier (shown on the upload page and on Admin):

- `received`: the upload was accepted and the dossier is waiting for intake.
- `preparing`: waiting for Word and text files to be turned into PDFs.
- `preprocessing`: pages are being cleaned and prepared.
- `processing`: pages are being read (OCR, and the second reader for handwriting) and reconciled.
- `segmenting`: defined in the code, but nothing sets it, so you will not see it.
- `indexing`: documents are being cut into chunks, embedded and indexed.
- `completed`: finished and searchable.
- `partial`: searchable, but some pages could not be read. Admin sees a note, and stewards are told.
- `failed`: something stopped it for good. Admin gets a message with the reason.
- `failed_intake`: the files did not match what was announced, or were missing.
- `superseded`: replaced by a newer revision.

Upload: `open` (files are still going up), `scanning`, `committed` (the dossier was created), `rejected` (the page shows the reason), `expired` (nobody finished it in time).

Page: `preprocessed`, `ocr_done`, `awaiting_second_read`, `reconciled` (done) and `failed` (done, but unreadable).

The Admin table shows pages done out of total and, in red, how many failed.

## 8. When something fails

Start with the Admin page: which dossier, which revision, how many pages failed. Then:

```bash
RG=rg-docai-dev
# the runs of a job (change the name for another stage)
az containerapp job execution list -g $RG -n job-ocr-online -o table
# an app's live log
az containerapp logs show -g $RG -n app-review --tail 50
# queue sizes: active, dead-lettered
SBNS=sbns-docai-<suffix>
az servicebus queue list -g $RG --namespace-name $SBNS \
  --query "[].{queue:name, active:countDetails.activeMessageCount, dead:countDetails.deadLetterMessageCount}" -o table
```

Read the queue table like this. `active` above zero for a long time with no job running means the job was not started. `dead` above zero means a message failed five times. To read a dead-lettered message, open the queue in the portal, Service Bus Explorer, the Dead-letter tab, and look at the reason. The watchdog job looks at the dead-letter queues every ten minutes: for a page queue it marks that page `failed` and the dossier can still finish as `partial`; for the intake queue it sends the "failed" message to the admin. It never reads a dead-letter queue to delete it.

For everything that mentions one dossier in the logs (errors and dead letters only), use the Log Analytics workspace of the deployment:

```
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(6h)
| where Log_s has "FIN-C90-S1-F0001"
| project TimeGenerated, App = coalesce(ContainerJobName_s, ContainerAppName_s), Log_s
| order by TimeGenerated asc
```

A job does not log each successful dossier. It logs one line per run ("handled N message(s); exiting"). A dossier ID appears in a log line only when a handler fails or a message is dead-lettered. Message IDs look like `ocr:<dossier id>-r1-p0001`.

After the fix, ask Yousef to **Reprocess** the dossier.

## Open points

- The review and hint behaviour above is read from the code and the web pages and was exercised by the automated tests with fakes. It has not been run against the real Azure services.
- Whether a handwritten sheet produces a review task depends on what the models read; there is no sheet guaranteed to produce one.
- A new revision that ends `partial` is not swapped in by the code as it stands, so the older revision keeps answering. This was read from the code and not tried; if a reprocess ends `partial`, check which revision is answering.
- The Application Insights telemetry is wired but untested; the Log Analytics queries above use the console logs.
- The log and job commands (`az containerapp job execution list`, the log query) are the ones used during deployment; the exact column names of the log table may differ in your workspace (`ContainerAppConsoleLogs_CL | getschema` shows them).
