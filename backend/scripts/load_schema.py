from pathlib import Path

from app.config import get_settings
from app.db import connection


def main() -> None:
    schema = Path(__file__).resolve().parents[1] / "schema.sql"
    statements = [statement.strip() for statement in schema.read_text(encoding="utf-8").split(";")]
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    if statement:
                        cursor.execute(statement)
            conn.commit()
    except Exception as exc:
        settings = get_settings()
        raise SystemExit(
            f"Schema loading failed for {settings.db_host}:{settings.db_port}/{settings.db_name}: {exc}"
        ) from exc
    print("SmartFlow schema loaded successfully.")


if __name__ == "__main__":
    main()