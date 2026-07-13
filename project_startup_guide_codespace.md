If you're using **GitHub Codespaces**, the main differences are:

1. Create and activate a virtual environment.
2. Install dependencies.
3. Expose port **8000** so you can access the app in your browser.
4. Use the Codespaces forwarded URL instead of `localhost`.

Here's the complete workflow.

---

## 1. Open the Codespace

Open the repository in GitHub Codespaces.

Open a terminal.

---

## 2. Create a virtual environment

### Linux (Codespaces)

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

You should now see something like:

```text
(venv) vscode ➜ /workspaces/project-name $
```

---

## 3. Install dependencies

If the project has `requirements.txt`

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If it uses Poetry

```bash
poetry install
```

If it uses `pyproject.toml` only

```bash
pip install -e .
```

---

## 4. Verify the project structure

You should have something similar to

```text
app/
scripts/
venv/
requirements.txt
```

---

## 5. Initialize the database

If the database already exists:

```bash
rm -f rto.db
```

Then run

```bash
python scripts/init_db.py
python scripts/seed_data.py
```

You should see messages indicating tables were created and seed data inserted.

---

## 6. Start the backend

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Important:** In Codespaces, use:

```bash
--host 0.0.0.0
```

instead of the default localhost.

The output should end with something like:

```text
Uvicorn running on
http://0.0.0.0:8000
```

---

## 7. Forward the port

Codespaces usually detects port **8000** automatically.

If not:

* Open the **Ports** tab.
* Find port **8000**.
* Set its visibility to **Public** or **Private** as needed.
* Click the forwarded URL.

It will look something like:

```
https://https://ubiquitous-fiesta-977j96w9x7rvhpwxv-8000.app.github.dev
```

This URL replaces `http://localhost:8000`.

---

## 8. Open the chat UI

Instead of

```
http://https://https://ubiquitous-fiesta-977j96w9x7rvhpwxv-8000.app.github.dev/api/v1/chat
```

open

```
https://https://https://ubiquitous-fiesta-977j96w9x7rvhpwxv-8000.app.github.dev/api/v1/chat
```

---

## 9. Open three tabs

Open three browser tabs using the forwarded URL:

```
https://https://https://ubiquitous-fiesta-977j96w9x7rvhpwxv-8000.app.github.dev/api/v1/chat
```

Login as:

**Tab A**

```
bob@example.com
```

**Tab B**

```
rm1@example.com
```

**Tab C**

```
slm1@example.com
```

---

## 10. Trigger compliance check

Open another terminal in Codespaces.

Keep the first terminal running Uvicorn.

In the second terminal:

```bash
source venv/bin/activate
```

Run:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/compliance/check \
  -H "Content-Type: application/json" \
  -d '{"emp_sapid":"E002","policy_type":"WEEKLY"}'
```

Since the `curl` command runs inside the Codespace, using `127.0.0.1:8000` (or `localhost:8000`) is appropriate.

---

## 11. Test the flow

After the `curl` command succeeds:

* A new chat should appear in all three browser tabs.
* Go to the **RM** tab (`rm1@example.com`).
* Send:

```
Discussed with Bob - he was on approved client visit to NY last week. Ticket: ABC-123
```

---

## Common issues

### `ModuleNotFoundError`

Install the missing package:

```bash
pip install -r requirements.txt
```

or

```bash
pip install <package-name>
```

---

### `uvicorn: command not found`

Install it:

```bash
pip install uvicorn
```

or

```bash
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

### `No module named app`

Make sure you're in the repository root:

```bash
pwd
ls
```

You should see:

```
app/
scripts/
```

---

### `sqlite3.OperationalError`

Delete the database and recreate it:

```bash
rm -f rto.db
python scripts/init_db.py
python scripts/seed_data.py
```

If you run into any errors, share:

* the output of `ls`
* the output of `pwd`
* the repository structure (or a screenshot)
* the exact error message

and I can help you troubleshoot the setup.
