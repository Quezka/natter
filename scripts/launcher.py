"""PyInstaller entry point (a script, so the package imports normally)."""
import sys

from natter.app import main

sys.exit(main())
