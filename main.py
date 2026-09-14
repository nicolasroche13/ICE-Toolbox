from app.core.logging_setup import configure_logging
from app.ui.main_window import run_app

if __name__ == "__main__":
    configure_logging()
    run_app()
