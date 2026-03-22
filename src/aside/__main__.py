"""Entry point for `python -m aside` and `aside` console script."""
import sys


def main():
    """Launch Aside."""
    from aside.ui.app import App
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
