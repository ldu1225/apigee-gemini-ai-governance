#!/usr/bin/env python3
"""
Automatically provisions an Apigee X environment ('eval-env'), imports the API Proxy bundle
'gemini-ai-governance.zip', and deploys it to your Google Cloud Apigee X Organization.

Usage:
    export GCP_PROJECT_ID="your-gcp-project-id"
    python3 deploy_to_apigee.py
"""
import subprocess
import time
import urllib.request
import json
import os
import zipfile

ORG = os.environ.get("GCP_PROJECT_ID", "your-gcp-project-id")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_PATH = os.path.join(SCRIPT_DIR, "gemini-ai-governance.zip")
APIPROXY_DIR = os.path.join(SCRIPT_DIR, "apiproxy")

def get_token():
    cmd = ["gcloud", "auth", "print-access-token"]
    account = os.environ.get("GCP_ACCOUNT")
    if account:
        cmd.append(f"--account={account}")
    return subprocess.check_output(cmd, text=True).strip()

def build_zip():
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(APIPROXY_DIR):
            for file in files:
                abs_file = os.path.join(root, file)
                rel_path = os.path.relpath(abs_file, SCRIPT_DIR)
                zf.write(abs_file, rel_path)
    print(f"Packaged API proxy bundle: {ZIP_PATH}")

def check_org_ready():
    token = get_token()
    url = f"https://apigee.googleapis.com/v1/organizations/{ORG}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            return data.get("state") == "ACTIVE"
    except Exception:
        return False

def create_env():
    print("Creating Apigee environment 'eval-env'...")
    token = get_token()
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://apigee.googleapis.com/v1/organizations/{ORG}/environments",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"name": "eval-env", "displayName": "Demo Evaluation Environment"})
    ]
    out = subprocess.check_output(cmd, text=True)
    print("Create Env Result:", out)
    return out

def import_proxy():
    print("Importing API proxy gemini-ai-governance.zip into Apigee X...")
    token = get_token()
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://apigee.googleapis.com/v1/organizations/{ORG}/apis?name=gemini-ai-governance&action=import",
        "-H", f"Authorization: Bearer {token}",
        "-F", f"file=@{ZIP_PATH}"
    ]
    out = subprocess.check_output(cmd, text=True)
    print("Import Result:", out)
    return out

def deploy_proxy():
    print("Deploying revision 1 of gemini-ai-governance to eval-env...")
    token = get_token()
    cmd = [
        "curl", "-s", "-X", "POST",
        f"https://apigee.googleapis.com/v1/organizations/{ORG}/environments/eval-env/apis/gemini-ai-governance/revisions/1/deployments?override=true",
        "-H", f"Authorization: Bearer {token}"
    ]
    out = subprocess.check_output(cmd, text=True)
    print("Deploy Result:", out)
    return out

if __name__ == "__main__":
    build_zip()
    print(f"Checking Apigee X Organization '{ORG}' status...")
    for i in range(60):
        if check_org_ready():
            print("Apigee X Organization is ACTIVE!")
            break
        print(f"[{i*10}s] Waiting for Apigee Organization '{ORG}' to become ACTIVE...")
        time.sleep(10)

    create_env()
    time.sleep(3)
    import_proxy()
    time.sleep(3)
    deploy_proxy()
    print("DONE! Apigee proxy 'gemini-ai-governance' is now live in the Google Cloud Apigee Console.")
