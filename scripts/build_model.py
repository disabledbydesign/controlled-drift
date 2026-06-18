#!/usr/bin/env python3
"""Build the entire GSDO data model in dependency order, then verify."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from build_goal import build_goal
from build_project import build_project
from build_task import build_task
from build_recurring import build_recurring
from build_strategy import build_strategy
import verify_model

if __name__ == "__main__":
    build_goal(); build_project(); build_task(); build_recurring(); build_strategy()
    print("\n== VERIFY ==")
    sys.exit(0 if verify_model.verify() else 1)
