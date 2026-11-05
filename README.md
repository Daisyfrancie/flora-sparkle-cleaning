# Flora Sparkle Cleaning

This project uses PostgreSQL. PostgreSQL databases are managed by the PostgreSQL server and do not appear as a `.db` file in the project folder.

## Run locally with VS Code and pgAdmin 4

1. Make sure PostgreSQL is installed and its server is running.
2. In pgAdmin 4, create a database named `flora_sparkle_db`.
3. In VS Code, open this project folder and copy `.env.example` to `.env` (in PowerShell, run `Copy-Item .env.example .env`). Set `DB_PASSWORD` to the password for your PostgreSQL user. Set `ADMIN_PASSWORD` and `SECRET_KEY` to strong, unique values.
4. Open a terminal in this folder and install dependencies using Python 3.12. Use `requirements.txt` (plural):

   ```powershell
   py -3.12 -m pip install -r requirements.txt
   ```

5. Start the website:

   ```powershell
   py -3.12 run.py
   ```

6. Open <http://127.0.0.1:5000> in your browser. On startup, the app creates its tables and sample data in `flora_sparkle_db`. Refresh the database in pgAdmin to see them.

The `.env` file contains local credentials and should not be shared. The app creates tables in the PostgreSQL database; it does not create or use a local `.db` file.

## Deploy to Render

The `render.yaml` Blueprint defines a Python web service and a PostgreSQL database. Push this project folder to a GitHub repository, then in Render choose **New → Blueprint**, connect the repository, and apply the Blueprint. Render supplies `DATABASE_URL` and generates `SECRET_KEY`; no local `.env` file should be uploaded.

The Blueprint uses Render's Free plans for testing. Free web services can sleep when idle, and Free PostgreSQL databases expire after 30 days. Upgrade the database before expiry if you need to keep its data. The Blueprint generates an `ADMIN_PASSWORD`; after deployment, reveal it in the Render service's Environment settings and use it at `/admin/login`. Do not commit or share the password.
