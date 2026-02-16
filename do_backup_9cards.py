# -*- coding: utf-8 -*-
"""
숏츠 생성기(9장 54초) 백업 - 이 폴더 내용을 _backup_9cards_54sec 에 복사
실행: python do_backup_9cards.py
"""
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent
BACKUP_NAME = "_backup_9cards_54sec"
BACKUP_DIR = BASE / BACKUP_NAME

def ignore(dirs, names):
    skip = {".venv", "venv", "__pycache__", ".git", BACKUP_NAME}
    return [n for n in names if n in skip]

def main():
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    shutil.copytree(BASE, BACKUP_DIR, ignore=ignore)
    print("백업 완료:", BACKUP_DIR)

if __name__ == "__main__":
    main()
