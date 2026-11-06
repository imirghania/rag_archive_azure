# Grounded document assistant (MVP)

A document question-answering system for Azure. People upload **dossiers** (scanned pages, Word files, text files; Arabic and English;
printed and handwritten). The system reads them, files them by department, and answers questions in plain language. **Every answer
cites the exact lines it came from**, and the answer is checked against those lines before it is shown.

## 1. What it does

```
upload (web app)
   |
   v   intake -> digital text / page images -> OCR (Document Intelligence) -> second reader for handwriting (vision model)
   |   -> reconcile the two readings -> segment the dossier into documents -> metadata -> chunk + embed -> index (AI Search)
   v
review: stewards and experts settle lines the system is unsure about           (web app, Review)
   |
   v
ask: question -> router -> search (hybrid, with the user's department scope) -> answer agent -> 4-layer verifier -> cited answer
```

- **Trust tiers.** Every line carries how it was read (`digital_source`, `printed_high_conf`, `handwritten_dual_agreed`, `unverified`...).
  Only lines that are reliable enough can be cited.
- **Four-layer verifier.** An answer is checked for structure, trust tier of the cited lines, numbers (every figure must appear in the
  evidence) and entailment (the evidence supports the claim). An answer that fails says so instead of guessing.
- **Access by department.** A user's rights come from the app role in the token **and** the department's own security group. The same scope
  filters the search index, and PostgreSQL row-level security protects the review tasks. A Finance reader never sees an HR dossier.
- **Handwriting.** Document Intelligence reads the page, a vision model reads the handwritten lines a second time, and a rule set
  compares them. Disagreements on digits and lines the system is unsure of go to review.

| App role        | Can do                                                   | Test user                  |
| --------------- | -------------------------------------------------------- | -------------------------- |
| `DocAI.Reader`  | Ask questions                                            | Layla (Finance), Huda (HR) |
| `DocAI.Expert`  | Upload, settle review tasks, submit hints                | Sara (Finance)             |
| `DocAI.Steward` | Approve hints, settle escalated tasks                    | Rana (Finance)             |
| `DocAI.Admin`   | Status page, reprocess a dossier; no access to documents | Yousef                     |

### Azure resources (all in one resource group, created by `deploy/`)

| Resource                                                                                                          | What for                                                                                                 |
| ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Container Apps: 13 **jobs** (start when a queue has messages, then exit) and 8 **apps** (HTTP or queue consumers) | The pipeline steps and the web app, one image `docai-run <module>`                                       |
| Service Bus (13 queues, one topic)                                                                                | Messages between the steps (transactional outbox, fan-in, dead letters)                                  |
| Storage accounts (3, ADLS Gen2)                                                                                   | Originals (write-once), page images and OCR output, upload staging                                       |
| Azure Database for PostgreSQL (Flexible Server, Entra-only login)                                                 | All workflow state; SQLAlchemy Core and Alembic migrations                                               |
| AI Search (Basic)                                                                                                 | Document and note indexes (keyword, vector, semantic)                                                    |
| Azure AI Services (Foundry) + project                                                                             | Models (`gpt-5-mini`, `text-embedding-3-large`), Document Intelligence, Content Safety, the answer agent |
| Entra ID                                                                                                          | Two app registrations (`docai-api`, `docai-web`), six app roles, five department groups                  |
| Key Vault, Container Registry, Log Analytics, Application Insights                                                | Secrets, the image, logs and traces; 21 managed identities with only the rights each needs               |

## 2. Deploy to Azure

The deployment is a Python package, `deploy/`, one module per numbered step. Every step can be re-run safely. Nothing is created until you
run a step without `--dry-run`. **Details, doubts and troubleshooting: `docs/running-on-azure.md` and `docs/azure-setup.md`.**

### 2.1 Before you start

| You need                                                                                                         | Check                                                                                                  |
| ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| An Azure subscription where you are **Owner**                                                                    | `az account show`                                                                                      |
| Entra rights to create apps, groups and role assignments (Global Administrator is easiest)                       | You must be a signed-in **user**, not a service principal                                              |
| `az` 2.72 or later and `uv`                                                                                      | `az version`, `uv --version`. Nothing else: no bash, curl, or Docker (the image is built in the cloud) |
| Tokens-per-minute quota for `gpt-5-mini` (GlobalStandard) and `text-embedding-3-large` (Standard) in your region | the quota command in 2.3                                                                               |

**Cost.** An **estimate** of about 0.15 USD per hour (roughly 110 USD a month) while everything exists, almost all of it AI Search Basic
(about 75 USD a month, billed hourly, cannot be paused) plus PostgreSQL, Service Bus, the registry and two always-on apps. Models and OCR
are pay-per-use. These are rough list prices from memory, not checked for your region or for PostgreSQL: read the Azure pricing pages.
Create a budget alert first (2.4). A few hours of testing cost a few dollars; delete everything when you stop (2.8).

### 2.2 Install and configure

```bash
uv sync --extra azure --extra samples
az login
az account set --subscription "<name or id>"
az account show --query "{name:name, id:id, tenant:tenantId}" -o table
cp .env.example .env
```

Edit `.env`. Everything else is filled in by step 90. The `DOCAI_USER_*` lines are not in `.env.example`: add them yourself.

| Variable                                                           | Meaning                                                                                                                                                                             | Default                                                              |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| `DOCAI_LOCATION`                                                   | The one region for everything                                                                                                                                                       | `swedencentral`                                                      |
| `DOCAI_PREFIX`, `DOCAI_ENV`                                        | Short name in resource names (lowercase letters and digits; 13 characters at most, 8 advised) and the environment name (`dev`, `test` or `prod` by convention; it is not validated) | `docai`, `dev`                                                       |
| `DOCAI_RESOURCE_GROUP`                                             | The resource group. It is **not** derived from the prefix and environment: if you change them, set this too                                                                         | `rg-docai-dev`                                                       |
| `DOCAI_MODELS__*`                                                  | The model deployment of each role                                                                                                                                                   | `gpt-5-mini` for chat roles, `text-embedding-3-large` for embeddings |
| `DOCAI_USER_LAYLA`, `_SARA`, `_RANA`, `_YOUSEF` (`_HUDA` optional) | Sign-in names of the test users, for example `layla@<your-tenant>.onmicrosoft.com`. Create the users first (2.6)                                                                    | empty                                                                |

### 2.3 Check the region and quota (read-only)

Everything lives in one region and it cannot be changed later. Check the models and quota there:

```bash
az cognitiveservices usage list -l <region> \
  --query "[?contains(name.value,'gpt-5-mini') || name.value=='OpenAI.Standard.text-embedding-3-large'].{name:name.value, limit:limit, used:currentValue}" -o table
```

This list is empty until the providers are registered (step 00). Need `gpt-5-mini` 100 and `text-embedding-3-large` 100 free. A `gpt-5` limit of 0
is fine: every chat role uses `gpt-5-mini`.

**Test that PostgreSQL can be created in the region before step 20.** `az postgres flexible-server list-skus -l <region>` can say
`Standard_B1ms` is available while your subscription still cannot create it (`SkuNotAvailable`, in every zone). On the reference
subscription Sweden Central refused and **France Central worked**. A server that failed to create stays in `Dropping` and keeps its name
reserved for a while, so test with a throwaway name and delete it:

```bash
az group create -n rg-pgtest -l <region>
az postgres flexible-server create -g rg-pgtest -n pgtest-<random> -l <region> --tier Burstable --sku-name Standard_B1ms --storage-size 32 \
   --version 16 --microsoft-entra-auth Enabled --password-auth Disabled --public-access 0.0.0.0 --yes
az group delete -n rg-pgtest --yes
```

### 2.4 Dry run and budget

```bash
uv run python -m deploy --dry-run        # prints every az command it would run; never calls az; expect exit code 0
```

Budget alert (portal, free): **Cost Management, Budgets, Add**. Scope: the subscription. Monthly amount: 150 USD. Alerts: actual 50%, 80%,
100% and forecast 100%, to your e-mail. A budget only sends e-mail; it stops nothing.

### 2.5 Run the steps, one at a time

Run from the repository root. Each step takes `--only N`; `--menu` picks from a list. Read what each step prints. A failed step stops
with `[error]` and the command's output: fix the cause and run the same step again. **Use `--only` in the order of the table.** A range
(`--from N --to M`) or a plain `uv run python -m deploy` runs the steps in number order, so step 50 comes before 60 and `app-review` logs
database login errors until 60 has run.

| Step | Command                                              | Creates                                                                                                                                                                                   | Time        | Check                                                             |
| ---- | ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------- |
| 00   | `uv run python -m deploy --only 0`                   | 12 resource providers registered, 2 CLI extensions, quota check                                                                                                                           | 2-10 min    | prints `preflight ok`                                             |
| 10   | `... --only 10`                                      | Resource group, Log Analytics, Application Insights, registry, Key Vault, Container Apps environment, 21 managed identities                                                               | 5-10 min    | `az identity list -g <rg> --query "length(@)"` is 21              |
| 20   | `... --only 20`                                      | 3 storage accounts, Service Bus (13 queues), **PostgreSQL**, **AI Search** (billing starts). Needs to reach `https://api.ipify.org` to find your public IP for the database firewall rule | 10-20 min   | server `Ready`, Entra admin set, `docai` database exists          |
| 30   | `... --only 30`                                      | AI Services account, Foundry project, the two model deployments                                                                                                                           | 5-10 min    | account, project and both deployments `Succeeded`                 |
| 40   | `... --only 40`                                      | 95 role assignments, one per access each identity needs                                                                                                                                   | 6-10 min    | 116 assignments to the 21 identities (with `AcrPull`)             |
| 41   | `... --only 41`                                      | Entra: `docai-api` (six app roles, scope `access_as_user`), `docai-web`, five groups, two secrets in Key Vault                                                                            | 1-3 min     | portal check below                                                |
| -    | create the users (2.6), set `DOCAI_USER_*` in `.env` |                                                                                                                                                                                           |             |                                                                   |
| 42   | `... --only 42`                                      | App roles, `docai-web` assignment and group memberships for each user                                                                                                                     | under 1 min | each user listed under Enterprise applications                    |
| 60   | `... --only 60`                                      | Database migrations, 20 database users for the identities, registry seed, Search indexes, the Foundry agent                                                                               | 1-3 min     | 24 tables, 20 `id-*` users, 2 indexes, agent `docai-answer-agent` |
| 50   | `... --only 50`                                      | Builds the image in the registry, creates 13 jobs and 8 apps, sets the sign-in address                                                                                                    | 20-40 min   | 8 apps `Running`, 13 jobs, `/healthz` answers                     |
| 90   | `... --only 90`                                      | Writes the endpoints and IDs into `.env`                                                                                                                                                  | seconds     | `diff .env.bak .env`                                              |

Wait about 5 minutes after steps 20, 30 and 40 before the next one: role assignments take time to apply (a `403` at that point is normal).
Step 60 comes before 50 so that the database exists when the always-on apps start. Command output is short on purpose; the detail of each
step, its failures and how to verify it is in `docs/running-on-azure.md`, section 7.

**Portal check after step 41** (entra.microsoft.com): App registrations, `docai-api`: Expose an API shows `access_as_user`, App roles shows
six roles, the manifest has `"groupMembershipClaims": "SecurityGroup"`. Enterprise applications, `docai-api` and `docai-web`, Properties:
Assignment required is **Yes**.

### 2.6 Create the test users (portal)

Entra admin center, **Users, New user, Create new user**: `layla`, `sara`, `rana`, `yousef` and optionally `huda`, on your tenant's
`onmicrosoft.com` domain, with auto-generated passwords. Put their sign-in names in `.env` as `DOCAI_USER_*` and run step 42. Each user signs
in once in a private window to set a password (multi-factor registration may be asked).

### 2.7 Try it

The address is printed by step 50; to read it again:

```bash
az containerapp show -g rg-docai-dev -n app-web --query properties.configuration.ingress.fqdn -o tsv
```

1. Sign in as **Sara**, open **Upload**, choose department **FIN**, mode **By dossier**, type the dossier ID (for example
   `FIN-C90-S1-F0001`), select the files of `samples/test_pack/typed/FIN-C90-S1-F0001/` (not `dossier.json`), **Check files**, **Confirm and upload**.
2. The dossier moves through the jobs and ends `completed`. Lines the system is unsure of become review tasks for Sara or Rana.
3. Sign in as **Layla** and ask questions; `samples/test_pack/typed/questions.md` lists questions with the expected answers. Questions
   about a fact that is not in the documents must be answered with "cannot find it", and a Finance reader asking about an HR fact must be refused.
4. As **Yousef**, **Admin** shows the dossiers and **Reprocess** runs one again as a new revision.

Signing out only ends the app's session. At the next sign-in Microsoft shows its account picker (choose **Use another account** to switch user).

**Test material** (`samples/test_pack/`, regenerate with the scripts in `samples/test_pack/tools/`): `typed/` (21 typed documents in English, Arabic
and mixed, as DOCX, TXT and scans), `forms/` (15 printed forms to fill in by hand, with `WHAT_TO_WRITE.md` saying what to write where) and
`handwritten/` (official-looking blank paper and 17 texts to copy by hand). Each folder has a `README.md` and a `questions.md`. **HR dossiers
cannot be uploaded** with the default test users: uploading needs the Expert role _and_ the department's expert group, and only Finance has one.

### 2.8 Operate, update, stop

| Task                                     | How                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Deploy changed code                      | Commit, then `uv run python -m deploy --only 50` (the image is built from the working tree: keep it clean)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Roll one component to a new image        | `az acr build -r <acr> -t docai:<tag> -f deploy/Dockerfile .`, then `az containerapp update -g <rg> -n <app> --image <acr>.azurecr.io/docai:<tag>` (`containerapp job update` for a job)                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| Read the logs of a job that has finished | `az monitor log-analytics query -w <workspace customer id> --analytics-query "ContainerAppConsoleLogs_CL \| where ContainerGroupName_s startswith 'job-ocr-online' \| where Log_s contains 'ERROR'"`                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| See why a message failed                 | Service Bus queue `<name>`, dead-letter sub-queue; the watchdog marks those pages failed and never retries them. **Reprocess** the dossier                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| Save money for a few days                | Stop PostgreSQL (`az postgres flexible-server stop`) and set the two always-on apps to zero replicas. **Search keeps billing**; for a long break delete everything                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| **Delete everything**                    | `uv run python -m deploy --teardown` (type the resource group name; `--yes` skips the prompt). It deletes the resource group, purges the soft-deleted Key Vault and AI account, removes the two Entra apps and the five groups, and deletes `.local/deploy.json`. It leaves the users, `.env` and the budget. It has not been run against Azure. Doing it by hand takes all of that: `az group delete -n <rg> --yes`, `az keyvault purge --name <kv> --location <region>`, `az cognitiveservices account purge`, and delete the Entra apps (`az ad app delete --id <id>`) and the groups, or a redeploy cannot reuse the names and finds the old apps |

### 2.9 If a step fails

All of these happened on the first real deployment and are fixed in the code, except where stated. The first column is what you will see.

| You see                                                       | Cause and what to do                                                                                                                                                                                                               |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Step 20: `SkuNotAvailable` for PostgreSQL                     | Your subscription cannot create Burstable servers in that region (2.3). Delete the resource group, purge the Key Vault, set `DOCAI_LOCATION` to a region that passed the test, delete `.local/deploy.json`, start again at step 00 |
| Step 30: `Role '...' doesn't exist`                           | Azure renames built-in roles ("Azure AI User" is now **Foundry User**). List the current names: `az role definition list --query "[?contains(roleName,'Foundry')].roleName"`                                                       |
| Step 30: gateway timeout on the project                       | Azure did not answer in time. Run the step again                                                                                                                                                                                   |
| Steps 41 and 42: `does not exist` right after a create        | Entra replication delay. Wait 30 seconds, run again                                                                                                                                                                                |
| Step 50: `The command failed with an unexpected error`        | A crash of the `containerapp` CLI extension on a read call. The step retries the component by itself; if it still stops, run it again                                                                                              |
| Step 60: `pgaadauth_create_principal_with_oid does not exist` | The extension exists only in the `postgres` database. The code connects there for this call. Update to the current code                                                                                                            |
| Step 60: Search index `400`                                   | The index files do not match the pinned Search API version `2024-07-01`; aliases are not available in it and are not used                                                                                                          |
| Step 60: connection timeout                                   | Your public IP changed. Run step 20 again (it refreshes the firewall rule)                                                                                                                                                         |
| An app crash-loops at start                                   | Read its log (`az containerapp logs show -g <rg> -n <app> --tail 50`). Test code against the real library, not a fake: three of the first failures were that                                                                       |
| Pages dead-lettered in `q-ocr-online`                         | The OCR step raised an error. Read the job log (2.8), fix, then reprocess the dossier                                                                                                                                              |
