import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

load_dotenv(PROJECT_DIR / ".env")

# SMB configuration
SMB_PATH = os.getenv("SMB_PATH", "")
SMB_USERNAME = os.getenv("SMB_USERNAME", "")
SMB_PASSWORD = os.getenv("SMB_PASSWORD", "")

ROOT_ADDITION_PATH = os.getenv("ROOT_ADDITION_PATH", "")