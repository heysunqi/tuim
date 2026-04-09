"""Entry point for Trelay: python -m trelay."""
import argparse
import sys


def main():
    """Main entry point for the Trelay TUI application."""
    parser = argparse.ArgumentParser(
        prog="trelay",
        description="Trelay - TUI Remote Connection Manager",
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to connections YAML config file",
    )
    args = parser.parse_args()

    from trelay.app import TrelayApp

    app = TrelayApp(config_path=args.config)
    app.run()


if __name__ == "__main__":
    main()
