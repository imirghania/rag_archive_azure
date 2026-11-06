"""One Azure AI Services (Foundry) account: model deployments, OCR (Document Intelligence / Content Understanding) and
Content Safety all live behind it. Deployments come from DOCAI_MODELS__* in .env (one deployment per distinct model)."""
from __future__ import annotations

from .lib import Ctx, DeployError

# The account is created through the ARM API: az 2.72.0 has neither --allow-project-management nor `account project`.
API = "?api-version=2025-04-01-preview"  # the version the Foundry quickstart uses for projects: unverified here


def run(ctx: Ctx) -> None:
    az, n = ctx.az, ctx.n
    ais_path = ctx.scope(f"Microsoft.CognitiveServices/accounts/{n.ais}")
    url = f"https://management.azure.com{ais_path}"
    if not az.rest_exists(url + API):
        az.rest("put", url + API, {
            "location": n.loc, "kind": "AIServices", "sku": {"name": "S0"}, "identity": {"type": "SystemAssigned"},
            "properties": {"customSubDomainName": n.ais, "allowProjectManagement": True, "publicNetworkAccess": "Enabled"}})
    # Wait until the account is usable before creating deployments and the project.
    if not az.wait(["rest", "--method", "get", "--url", url + API], "properties.provisioningState", "Succeeded", tries=40, delay=15):
        raise DeployError(f"the AI Services account {n.ais} is not 'Succeeded' after 10 minutes: check the portal, then run this step again")
    for role in ("Cognitive Services User", "Foundry User"):  # the bootstrap creates the agent with the second one
        ctx.role(ctx.need("DEPLOYER_OID"), role, ais_path, "User")

    # The Foundry project that hosts the answer agent (the agent itself is created by the bootstrap).
    project = f"{url}/projects/{n.project}{API}"
    if not az.rest_exists(project):
        az.rest("put", project, {"location": n.loc, "identity": {"type": "SystemAssigned"},
                                 "properties": {"displayName": n.project, "description": "DocAI answer agent"}})

    for model, version, sku, cap in ctx.cfg.models:
        # Deployments on one account are created one at a time; the service rejects parallel changes.
        if az.exists(["cognitiveservices", "account", "deployment", "show", "-g", n.rg, "-n", n.ais, "--deployment-name", model]):
            ctx.log(f"deployment {model} exists")
            continue
        ctx.log(f"deploying {model} {version} ({sku}, {cap})")
        az.run(["cognitiveservices", "account", "deployment", "create", "-g", n.rg, "-n", n.ais, "--deployment-name", model,
                "--model-name", model, "--model-version", version, "--model-format", "OpenAI", "--sku-name", sku, "--sku-capacity", str(cap)])

    endpoint = f"https://{n.ais}.cognitiveservices.azure.com/"
    ctx.state.set("FOUNDRY_PROJECT_ENDPOINT", f"https://{n.ais}.services.ai.azure.com/api/projects/{n.project}")
    for key in ("FOUNDRY_ENDPOINT", "OCR_ENDPOINT", "CONTENT_SAFETY_ENDPOINT"):
        ctx.state.set(key, endpoint)
    ctx.log("ai ok")
