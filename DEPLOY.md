# Railway Deployment Guide

This is your step-by-step guide to deploy the Timesheet Analysis Tool to Railway so HR can access it from anywhere via a URL.

**Time needed:** ~45 minutes the first time.

**What you need before starting:**
- Your OpenAI API key (starts with `sk-...`)
- A Railway account at railway.app (free to sign up)
- This GitHub repo: https://github.com/daetan999/timesheet_tool

---

## Step 1 — Create a Railway account

Go to https://railway.app and sign up. Connect your GitHub account when prompted — Railway needs this to access the repo.

---

## Step 2 — Create a new project

1. In Railway dashboard, click **New Project**
2. Click **Deploy from GitHub repo**
3. Find and select `daetan999/timesheet_tool`
4. Click **Deploy Now**

Railway will start building. It will fail the first time — that is expected because you haven't added the environment variables yet. Continue to Step 3.

---

## Step 3 — Add environment variables

In your Railway project, click the service (it will be named something like `timesheet-tool`). Then click **Variables** in the left sidebar. Add these one by one:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | Your API key (starts with `sk-...`) |
| `OPENAI_MODEL` | `gpt-5.4` |
| `AI_EXTRACTION_MODE` | `real_openai` |
| `DATA_DIR` | `/data` |

> **Important:** `DATA_DIR=/data` tells the app to store all session data on the persistent Volume (Step 4). Without this, all HR data is lost every time the app restarts.

---

## Step 4 — Add a Volume (persistent storage)

This is the most important step. Without it, all session data and config is deleted every time Railway restarts the app.

1. In your Railway project, click **New** → **Volume**
2. Connect the Volume to your service
3. Set the mount path to: `/data`
4. Click **Create**

Railway will restart the app. Wait for it to go green.

---

## Step 5 — Set the start command

1. Click your service → **Settings** → **Deploy**
2. Find **Start Command** and set it to:
   ```
   uvicorn app:app --host 0.0.0.0 --port $PORT
   ```
3. Click **Save** and let it redeploy

---

## Step 6 — Set instances to 1

Still in **Settings** → **Deploy**, find **Replicas** or **Instances** and set it to **1**.

> **Why:** The app keeps batch progress in memory. If two instances run at the same time, HR's batch won't work correctly. Always keep it at 1.

---

## Step 7 — Seed the initial config onto the Volume

This seeds the 3 baseline SOP codes. You only do this once.

**There is no "Shell" tab in the Railway dashboard.** Shell access is done through the Railway CLI on your own computer (it connects into the running container over SSH). Do this from a Terminal on your Mac:

**7a. Install the Railway CLI** (one-time, skip if you already have it):

```bash
npm install -g @railway/cli
```

If you don't have `npm`, you can also install with Homebrew: `brew install railway`

**7b. Log in and link the CLI to your project:**

```bash
railway login
```

This opens your browser to authorize. Then, from inside your project folder on your computer:

```bash
cd "/Users/dae/Desktop/Timesheet Analysis Tool"
railway link
```

> If you're on a different computer where you cloned the repo somewhere else, replace the path above with wherever you cloned it — run `pwd` inside that folder to check, or just `cd` into the folder first then run `railway link` without `cd` at all.

Follow the prompts to select your Railway project and the service you deployed.

**7c. Open a shell inside the deployed container:**

```bash
railway ssh
```

The first time you run this, it will ask to register an SSH key — accept it. This drops you into a live terminal *inside* your running Railway service (the same container that has `/data` mounted).

**7d. Run the seed commands inside that shell:**

```bash
mkdir -p /data/config /data/sessions /data/uploads
cp config/sop_codes.json /data/config/sop_codes.json
echo "[]" > /data/config/workers.json
```

Type `exit` when done to leave the SSH session — this does not stop your app, it just disconnects your terminal from it.

> **Important:** do this BEFORE HR uses the app. If the app boots before you seed, it will create empty config files. Run the `cp` command again to overwrite with the 3 SOP codes.

> **Alternative:** in the Railway dashboard, you can right-click your service and choose **Copy SSH Command** — this gives you the exact `railway ssh` command pre-filled for that specific service, useful if you have more than one service in the project.

---

## Step 8 — Get the public URL

In Railway, click your service and look for the **Domain** section. Railway gives you a URL like:

```
https://your-app-name-production.up.railway.app
```

That is the URL you give to HR. They just open it in their browser — no installation needed.

---

## Step 9 — Verify it works

Open the URL in your browser. You should see the home page of the Timesheet Analysis Tool.

1. Click **Start New Month** → pick a month → click Start
2. You should be taken through the workflow steps
3. Check that the SOP codes page shows the 3 seeded codes (OFF, EARLY OUT 早回, LATE IN 迟到)
4. Upload a test image to confirm uploads work
5. The review page should load with no errors

If anything fails, check Railway logs: **Service → Deployments → View Logs**.

---

## Step 10 — Done. Give HR the URL.

Send HR the `HR_GUIDE.md` file alongside the URL. That is their daily use guide.

---

## Future deploys (when you make code changes)

Every time you push to the `main` branch of the GitHub repo, Railway auto-deploys. No manual steps needed.

```bash
# On your local machine, after making changes:
git add .
git commit -m "description of change"
git push origin clean-main:main
```

Railway picks it up automatically. The Volume data (sessions, config) is not affected by deploys — it persists.

---

## Troubleshooting

**App shows an error on startup:**
- Check Railway logs for the error message
- Most likely a missing env var or the Volume not being mounted correctly

**Data disappears after restart:**
- Volume is not mounted at `/data`, or `DATA_DIR` env var is missing
- Go back to Step 3 and 4 and verify

**OpenAI calls fail:**
- Check that `OPENAI_API_KEY` is correct and the model `gpt-5.4` is available on your account
- Check `AI_EXTRACTION_MODE=real_openai` is set

**SOP codes are empty after deploy:**
- The app booted before you seeded. Re-run the seed command from Step 7.

**HR sees an old version:**
- Hard refresh the browser (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)

---

## Cost summary

| Item | Monthly cost |
|---|---|
| Railway service (Starter plan) | ~$5–10 |
| Railway Volume (~1 GB) | ~$0.25 |
| OpenAI GPT-5.4 (~45 workers) | ~$5–7 |
| **Total** | **~$14/month** |

---

## Emergency: reset everything

If you need to start fresh (e.g. data corruption):

```bash
# In Railway shell — deletes all session data but keeps config
rm -rf /data/sessions
mkdir -p /data/sessions
```

To also reset config:
```bash
cp config/sop_codes.json /data/config/sop_codes.json
echo "[]" > /data/config/workers.json
```
