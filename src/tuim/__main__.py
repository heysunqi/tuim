"""Entry point for Tuim: python -m tuim."""
import argparse
import sys

from tuim.i18n import t


def main():
    """Main entry point for the Tuim TUI application."""
    parser = argparse.ArgumentParser(
        prog="tuim",
        description=t("app_description"),
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help=t("config_help"),
    )
    args = parser.parse_args()

    from tuim.app import TuimApp

    app = TuimApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
