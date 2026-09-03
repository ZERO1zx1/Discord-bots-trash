import os
import runpy
import sys


if __name__ == "__main__":
    project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Gurten-LGC")
    main_file = os.path.join(project_dir, "main.py")

    if not os.path.exists(main_file):
        raise FileNotFoundError(f"Bot launcher not found: {main_file}")

    os.chdir(project_dir)
    sys.path.insert(0, project_dir)
    runpy.run_path(main_file, run_name="__main__")
