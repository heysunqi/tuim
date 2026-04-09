"""Entry point for Trelay: python -m trelay."""
import argparse
import sys

from trelay.i18n import t


def main():
    """Main entry point for the Trelay TUI application."""
    parser = argparse.ArgumentParser(
        prog="trelay",
        description=t("app_description"),
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help=t("config_help"),
    )
    args = parser.parse_args()

    from trelay.app import TrelayApp

    app = TrelayApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
