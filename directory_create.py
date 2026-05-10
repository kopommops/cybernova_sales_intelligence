import os

PROJECT_ROOT = "dashboard"

STRUCTURE = {
    "etl":            "CSV ingestion, cleaning, and star-schema loader scripts",
    "analytics":      "KPI computation, funnel, causal, and anomaly modules",
    "api/routers":    "FastAPI route handlers — one file per actor role",
    "api/schemas":    "Pydantic request/response models",
    "api/auth":       "JWT authentication, bcrypt hashing, RBAC middleware",
    "api/deps":       "Shared FastAPI dependencies (DB session, current user)",
    "frontend/pages": "One NiceGUI page per dashboard view",
    "frontend/components": "Reusable chart, KPI card, and table components",
    "frontend/assets":     "Static CSS overrides and logo assets",
    "tests/unit":         "Unit tests for analytics and ETL functions",
    "tests/integration":  "API endpoint integration tests",
    "notebooks":      "EDA and causal analysis notebooks",
    "docs":           "Portfolio report, methodology notes, client contact sheets",
}

# files to create at root level
ROOT_FILES = [
    "main.py",
    "requirements.txt", 
    ".env",           
    ".gitignore",
    "README.md",
]

# files to create inside key packages
PACKAGE_FILES = {
    "etl":              ["__init__.py", "ingest.py", "clean.py", "loader.py"],
    "analytics":        ["__init__.py", "kpis.py", "funnel.py", "causal.py",
                         "anomaly.py", "geo.py", "summary_stats.py"],
    "api":              ["__init__.py"],
    "api/routers":      ["__init__.py", "auth.py", "salesperson.py",
                         "sales_manager.py", "systems_manager.py"],
    "api/schemas":      ["__init__.py", "user.py", "analytics.py", "upload.py"],
    "api/auth":         ["__init__.py", "jwt_handler.py", "hashing.py", "rbac.py"],
    "api/deps":         ["__init__.py", "db.py", "current_user.py"],
    "frontend":         ["__init__.py", "app.py"],
    "frontend/pages":   ["__init__.py", "login.py", "register.py",
                         "salesperson_dashboard.py", "sales_manager_dashboard.py",
                         "systems_manager_dashboard.py"],
    "frontend/components": ["__init__.py", "kpi_card.py", "trend_chart.py",
                             "funnel_chart.py", "heatmap.py", "geo_chart.py",
                             "causal_panel.py", "anomaly_alert.py",
                             "action_plan.py", "email_cta.py", "pdf_export.py"],
    "tests/unit":       ["__init__.py", "test_kpis.py", "test_funnel.py",
                         "test_causal.py", "test_clean.py"],
    "tests/integration":["__init__.py", "test_auth.py", "test_salesperson.py",
                         "test_systems_manager.py"],
}

def scaffold():
    print(f"Scaffolding project: {PROJECT_ROOT}/\n")

    # creating directories
    for path, description in STRUCTURE.items():
        full_path = os.path.join(PROJECT_ROOT, path)
        os.makedirs(full_path, exist_ok=True)
        print(f"  [DIR]  {full_path:<55}  # {description}")

    print()

    # creating root-level files
    for filename in ROOT_FILES:
        full_path = os.path.join(PROJECT_ROOT, filename)
        if not os.path.exists(full_path):
            open(full_path, "w").close()
        print(f"  [FILE] {full_path}")

    print()

    # creating package files
    for package, files in PACKAGE_FILES.items():
        for filename in files:
            full_path = os.path.join(PROJECT_ROOT, package, filename)
            if not os.path.exists(full_path):
                open(full_path, "w").close()
            print(f"  [FILE] {full_path}")

    print(f"\nScaffold complete.")
    print(f"  Directories : {len(STRUCTURE)}")
    total_files = len(ROOT_FILES) + sum(len(v) for v in PACKAGE_FILES.values())
    print(f"  Files       : {total_files}")
    print(f"\nNext step: populate requirements.txt and main.py, then run:")
    print(f"  cd {PROJECT_ROOT} && uvicorn main:app --reload")


if __name__ == "__main__":
    scaffold()