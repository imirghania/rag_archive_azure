# Grounded document assistant

A document question-answering system that runs on Azure. People upload **dossiers**: scanned pages, Word files and text files, in Arabic
and English, printed or handwritten. The system reads them, files them by department, and answers questions in plain language. **Every
answer cites the exact lines it came from**, and the answer is checked against those lines before anyone sees it. When the evidence does
not support an answer, the system says it cannot find one instead of guessing.

This is an MVP. It is built to prove the whole path works on real Azure services, from an uploaded scan to a cited answer.

## What it does

```
upload (web app)
   |
   v   intake -> digital text / page images -> OCR -> second reader for handwriting
   |   -> reconcile the two readings -> split the dossier into documents -> metadata -> chunk and embed -> index
   v
review: experts and stewards settle the lines the system is unsure about
   |
   v
ask: question -> router -> search (limited to the user's departments) -> answer agent -> verifier -> cited answer
```

- **Trust in every line.** Each line records how it was read: from a digital file, from clean print, from handwriting that two readers
  agreed on, or not verified. Only lines that are reliable enough can be cited.
- **A four-part check on every answer.** The answer must have the right structure, cite only trusted lines, use only numbers that appear in
  the evidence, and be supported by it.
- **Access by department.** What a person can do comes from their role (reader, expert, steward, admin). What they can see comes from the
  department group they belong to. A Finance reader never sees an HR dossier, in search or in the database.
- **Handwriting gets a second opinion.** Document Intelligence reads the page, a vision model reads the handwritten lines again, and
  disagreements on digits or doubtful lines go to a person for review.

Under the hood it is a set of small jobs and apps on Azure Container Apps, connected by Service Bus queues, with PostgreSQL for the
workflow state, AI Search for retrieval, and Azure AI Foundry for the models and the answering agent. Everything runs from one container
image, and the deployment below creates all of it.

## Deploying to Azure

This guide takes you from an empty Azure subscription to the app running in your browser. It is a list of steps in the order you run
them. Each step says why it is there, the command, how to tell it worked, and what to do if it did not.

Everything is created with one Python package, `deploy/`, driven from the repository root. Every step can be run again safely, so when
something fails you fix the cause and repeat the same step. Apart from the throwaway test server in section 4, nothing is created until section 8, and the dry run in
section 7 shows you every command before anything runs.

**Time and cost.** Plan on one to two hours, most of it waiting on Azure. While everything exists it costs about 0.15 USD an hour
(roughly 110 USD a month). AI Search is most of that, and it bills by the hour even when idle. Models and OCR are pay-per-use. A few hours
of testing cost a few dollars. Delete everything when you stop (last step).

### 1. Check what you have

You need:

- An Azure subscription where you are **Owner**. The deployment creates resources and gives roles to the identities it creates, and
  only an Owner can do the second part.
- Rights in Entra ID (Azure Active Directory) to create app registrations, groups and users. Global Administrator is the easy way. You
  must be signed in as a **user**, not a service principal, because the database administrator is set to you.
- The Azure CLI (`az`) 2.72 or newer. Older versions miss flags the deployment uses.
- `uv`, which installs Python and the dependencies.

You do not need Docker. The container image is built inside Azure.

Install or update the Azure CLI:

```bash
# Ubuntu, Debian, WSL
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash      # installs it; run again later to update
# macOS
brew update && brew upgrade azure-cli                       # or: brew install azure-cli
# Windows (PowerShell)
winget install --exact --id Microsoft.AzureCLI              # update with: winget upgrade --id Microsoft.AzureCLI
```

Then check:

```bash
az version --query '"azure-cli"' -o tsv     # 2.72.0 or higher
uv --version
```

Install `uv` from https://docs.astral.sh/uv/ if the command is missing. If `az` is older than 2.72, update it now: a half-working
CLI produces confusing errors later.

### 2. Install the project

```bash
git@github.com:imirghania/rag_archive_azure.git && cd rag_archive_azure
uv sync --extra azure --extra samples
```

The `azure` extra holds the Azure libraries the deployment itself imports (without it, step 60 fails with `No module named
azure.identity`). The `samples` extra lets you regenerate the test documents later.

Keep `git status` clean from here on. The image that runs in Azure is built from your working tree, so uncommitted edits would be
deployed without a trace in the history.

### 3. Sign in and pick the subscription

```bash
az login
az account set --subscription "<subscription name or id>"
az account show --query "{name:name, id:id, tenant:tenantId, user:user.name}" -o table
```

Why: every command that follows acts on whatever `az account show` prints. If you have several subscriptions, the wrong default is the
most common way to deploy to the wrong place.

You are done when the table shows the subscription you mean and your own user name. In WSL, if the browser does not open, use
`az login --use-device-code`.

### 4. Choose and test the region

Pick the region once, now. Every resource lives in it and it cannot be changed later without deleting everything.

The default region is Sweden Central, and on the reference subscription it **refused to create the PostgreSQL server** even though
the SKU list claimed it was available (`SkuNotAvailable`). France Central worked. Azure decides this per subscription, so test it before
you create anything. A throwaway server takes a few minutes and costs a few cents:

```bash
REGION=francecentral
az provider register -n Microsoft.DBforPostgreSQL --wait
az group create -n rg-pgtest -l $REGION
az postgres flexible-server create -g rg-pgtest -n pgtest-$RANDOM -l $REGION \
  --tier Burstable --sku-name Standard_B1ms --storage-size 32 --version 16 \
  --microsoft-entra-auth Enabled --password-auth Disabled --public-access 0.0.0.0 --yes
az group delete -n rg-pgtest --yes --no-wait
```

You are done when the create command finishes without an error. Delete the test group either way. If it fails, try another region from
the top of this section. Skipping this test is the single most expensive mistake: step 20 fails after a lot of work, and you have to delete
everything and start again.

The models have a quota in each region too. Step 00 checks it for you and stops with a clear message if you do not have enough
(you need 100 free for `gpt-5-mini` and for `text-embedding-3-large`). A quota of 0 for `gpt-5` does not matter, because every role
uses `gpt-5-mini`.

### 5. Write the `.env` file

The deployment reads its settings from a file named `.env` in the repository root. Almost everything has a working default, and the
subscription and tenant come from `az`, so the file you need is short. Start it with the region you tested:

```bash
echo "DOCAI_LOCATION=francecentral" > .env
```

The region line is the only one that must be there. If you leave it out, the deployment uses Sweden Central, which may refuse
PostgreSQL (section 4).

Later, after you create the test users (section 9), you add one line per user so the deployment can give them roles:

```bash
DOCAI_USER_LAYLA=layla@<your-tenant>.onmicrosoft.com     # Reader: asks questions
DOCAI_USER_SARA=sara@<your-tenant>.onmicrosoft.com       # Expert: uploads documents
DOCAI_USER_RANA=rana@<your-tenant>.onmicrosoft.com       # Steward: resolves review tasks
DOCAI_USER_YOUSEF=yousef@<your-tenant>.onmicrosoft.com   # Admin: reprocesses dossiers
DOCAI_USER_HUDA=huda@<your-tenant>.onmicrosoft.com       # optional second Reader
```

A missing user line does not stop the deployment, but that user gets no role, so nobody can sign in with the right permissions.

Three things that surprise people:

- The containers in Azure never read `.env`. Step 50 hands each container its settings as environment variables, and the file is kept
  out of the image on purpose. The file only drives the deployment from your machine.
- Do not copy secrets or endpoints into it by hand. Step 90 appends the endpoints and IDs when it finishes.
- If you change the name settings (`DOCAI_PREFIX`, `DOCAI_ENV`), set `DOCAI_RESOURCE_GROUP` too. The group name is not derived from
  them.

### 6. Set a budget alert

Do this before the first resource exists. In the Azure portal open **Cost Management, Budgets, Add**. Scope: the subscription. Amount:
150 USD a month. Alerts: actual spend at 50%, 80% and 100%, and forecast at 100%, sent to your e-mail.

Why: a budget only e-mails you, it stops nothing, but it is the only warning you get if you forget the project is running. 30 USD is
too low for this system: it would alert you within a couple of days.

### 7. Dry run

```bash
uv run python -m deploy --dry-run
```

This prints every `az` command the deployment would run and runs none. You are done when it ends without an error (about 250 lines
with no users in `.env`). Skim it once: if the region, names or subscription look wrong, fix `.env` or step 3 now, while it is free.

### 8. Run the steps, one at a time

Use `--only N` for each step, in the order below. Do not run a range or the plain `uv run python -m deploy`. A range runs the steps in
number order, so step 50 runs before 60, and the database login of the apps fails until 60 has run. Running one step at a time also
means each failure tells you exactly where you are.

Each step prints what it does. A failure prints `[error]` and the Azure message. Fix the cause and run the same step again.

**Step 00, preflight (2 to 10 minutes).** Registers the Azure resource providers, installs two CLI extensions and checks your model
quota. Registration is slow the first time, which is why it is its own step.

```bash
uv run python -m deploy --only 0
```

Done when it prints `preflight ok`.

**Step 10, core (5 to 10 minutes).** Creates the resource group, the log store, the container registry, the key vault, the Container
Apps environment and 21 managed identities (one per job or app, so each can be given only the access it needs). It also creates
`.local/deploy.json`, the file that remembers the random suffix in the resource names and every ID. Never delete that file while the
deployment exists.

```bash
uv run python -m deploy --only 10
az identity list -g rg-docai-dev --query "length(@)"        # 21
```

**Step 20, data (10 to 20 minutes).** Creates the three storage accounts, Service Bus with its 13 queues, the PostgreSQL server (login
by Entra only, no passwords) and AI Search. This is where billing starts in earnest. It needs to reach `https://api.ipify.org` to learn
your public IP address for the database firewall.

```bash
uv run python -m deploy --only 20
```

Done when the server is `Ready` and a database named `docai` exists. If it stops with `SkuNotAvailable`, you skipped section 4: see
"If a step fails" below.

**Step 30, AI (5 to 10 minutes).** Creates the AI Services account, the Foundry project and the two model deployments
(`gpt-5-mini` for every chat role, `text-embedding-3-large` for search vectors).

```bash
uv run python -m deploy --only 30
```

Done when the account, the project and both deployments report `Succeeded` in the portal.

**Step 40, access rights (6 to 10 minutes).** Gives each identity exactly the roles it needs on the queues, the storage, the models,
the registry and the key vault: 116 assignments in all. Nothing works without them, and nothing has more access than it needs.

```bash
uv run python -m deploy --only 40
```

**Wait five minutes after steps 20, 30 and 40.** Azure takes a few minutes to apply a new role. A `403` or "not authorized" in the next
step right after one of these is normal and goes away on its own.

**Step 41, Entra apps and groups (1 to 3 minutes).** Creates the sign-in side: the app registration for the API (with its six roles and
the `access_as_user` scope), the one for the web app, five groups and the secrets they use, stored in the key vault.

```bash
uv run python -m deploy --only 41
```

Check it in the Entra admin center (entra.microsoft.com). Under App registrations, `docai-api` shows the scope `access_as_user` and six
app roles. Under Enterprise applications, `docai-api` and `docai-web` both have **Assignment required** set to Yes: that setting is why
only people you assign can sign in.

### 9. Create the test users

Step 42 assigns roles to users, so the users must exist first. The deployment does not create users, so you make them by hand.

In the Entra admin center go to **Users, New user, Create new user**. Create `layla`, `sara`, `rana`, `yousef` and optionally `huda`
on your tenant's `<tenant>.onmicrosoft.com` domain, with auto-generated passwords. Write the passwords down. Then add the five
`DOCAI_USER_*` lines from section 5 to `.env`, with the exact sign-in names you created.

### 10. Assign the users

```bash
uv run python -m deploy --only 42
```

Why: this gives each user an app role on the web app (Layla Reader, Sara Expert, Rana Steward, Yousef Admin) and puts them in the
department groups. You are done when each user is listed under Enterprise applications, `docai-web`, Users and groups. If it says a user
"does not exist", the user was created seconds ago: wait 30 seconds and run it again.

Know one limit: only Finance has an expert group. Sara can therefore upload Finance dossiers, and **HR dossiers cannot be uploaded**
with these default users. Readers can still be refused HR facts, which is what the isolation test checks.

### 11. Bootstrap the database, search and agent (before step 50)

```bash
uv run python -m deploy --only 60
```

Why: this creates the tables, one database user for each managed identity (using your Entra token), the Search indexes and synonym
maps, and the chat agent in Foundry. It must run **before** the apps exist, because the apps need the database and the agent the moment
they start. That is why the order is 60, then 50.

Done when it finishes without an error. If it times out connecting, your public IP changed since step 20: run step 20 again, then 60.

### 12. Build and start the apps

```bash
uv run python -m deploy --only 50
```

Why: this builds the one container image in your registry, then creates 13 jobs and 8 apps from it, and tells the sign-in app its public
address. It is the longest step, 20 to 40 minutes, and mostly silent while Azure builds. Do not interrupt it.

Check:

```bash
az containerapp list -g rg-docai-dev --query "[].{name:name, state:properties.runningStatus}" -o table   # 8 apps, Running
az containerapp job list -g rg-docai-dev --query "length(@)"                                              # 13
FQDN=$(az containerapp show -g rg-docai-dev -n app-web --query properties.configuration.ingress.fqdn -o tsv)
curl -s https://$FQDN/healthz                                                                             # {"ok":true}
```

If a component stops with `The command failed with an unexpected error`, that is the Container Apps CLI extension crashing in its own
error handling. The step already retries each component three times; if it still stops, run the step again and it continues.

### 13. Write the endpoints into `.env`

```bash
cp .env .env.bak
uv run python -m deploy --only 90
diff .env.bak .env
```

Why: it appends the endpoints and IDs (`DOCAI_AZURE__*`, `DOCAI_DATABASE__*`, `DOCAI_AUTH__*`) so the project's own tools can talk to
your deployment from your machine. Azure does not need them. The diff shows what was added.

### 14. See it work

Open `https://<the address from section 12>` in a **private window**. Each user signs in once to set a password, and Microsoft may ask them
to register a second factor.

1. Sign in as **Sara** and open **Upload**. Choose department **FIN**, mode **By dossier**, and type the dossier ID
   `FIN-C90-S1-F0001`. Select the files in `samples/test_pack/typed/FIN-C90-S1-F0001/` (not `dossier.json`), press **Check files**,
   then **Confirm and upload**.
2. Wait a few minutes. The dossier moves through the jobs and ends as `completed`. Lines the system is unsure about become review
   tasks for Sara or Rana.
3. Sign in as **Layla** in another private window and ask a question about the documents. The questions and their expected answers are
   in `samples/test_pack/typed/questions.md`. This is the check to do first: the upload pipeline was proven on Azure, but chat answers
   were not yet confirmed there. A fact that is not in the documents should get "cannot find it", not a guess.
4. As **Yousef**, the admin screen lists dossiers and **Reprocess** runs one again as a new revision.

Signing out ends only the app's own session. Microsoft shows its account picker at the next sign-in, so to switch user choose **Use
another account**.

If a dossier does not finish, look at the jobs:

```bash
az containerapp job execution list -g rg-docai-dev -n job-ocr-online -o table
az containerapp logs show -g rg-docai-dev -n app-review --tail 50
```

### If a step fails

Most failures were met on the first real deployment and are fixed in the code. The ones you can still hit:

- **`SkuNotAvailable` in step 20.** The region cannot create PostgreSQL for your subscription. Delete the resource group, purge the
  key vault (`az keyvault purge --name kv-docai-<suffix> --location <region>`, because a deleted vault keeps its name), move
  `.local/deploy.json` out of the way so the next run gets a new suffix, set a tested region in `.env`, and start again at step 00.
- **`Role '...' doesn't exist` in step 30 or 40.** Microsoft renames built-in roles. "Azure AI User" is now **Foundry User**, same role.
  List current names with `az role definition list --query "[?contains(roleName,'Foundry')].roleName"` and fix the name in the code.
- **`does not exist` right after something was created, in steps 41 and 42.** Entra needs a few seconds to replicate. Wait 30 seconds
  and run the same step again.
- **A 403, "not authorized", or a timeout calling a new service.** The role is not applied yet. Wait five minutes and run again. A
  gateway timeout or 503 from the AI project is Azure being slow: run the step again.
- **A timeout connecting to PostgreSQL in step 60.** Your public IP changed. Run step 20 (it refreshes the firewall rule), then 60.
- **A container keeps restarting.** Read its log with `az containerapp logs show -g rg-docai-dev -n <app> --tail 50`. The usual cause
  is a mismatch between the code and a real library that the tests, which use fakes, could not catch.

### Updating after a code change

Commit the change first, then run step 50 again:

```bash
git commit -am "my change"
uv run python -m deploy --only 50
```

The image is built from the working tree, so only what is on disk goes in, and committing first keeps what runs in Azure matching your
history. Existing jobs and apps move to the new image.

### Stopping the bill

AI Search bills every hour whether or not anyone uses the app, and it cannot be paused. For a break of a few days you can stop the
database (`az postgres flexible-server stop`), but the cheap and clean way to stop paying is to delete everything:

```bash
uv run python -m deploy --teardown
```

It asks you to type the resource group name, then deletes the group, purges the soft-deleted key vault and AI account, and removes the
two Entra apps and the five groups. It does not delete the users, your `.env` or your budget. It has not been run against a real
subscription yet. If you prefer to do it by hand: `az group delete -n rg-docai-dev --yes`, then `az keyvault purge`, `az cognitiveservices
account purge`, `az ad app delete` for the two apps, and delete the groups. Without the purges a redeploy cannot reuse the names.
