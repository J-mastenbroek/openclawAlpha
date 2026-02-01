#!/bin/bash
cd /home/openclaw/.openclaw/workspace/openclawAlpha
python -m src.main >> logs/scan.log 2>&1
