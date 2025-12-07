#!/bin/bash
# Quick launcher for Spelling Practice
# Just run this file to start!

cd "$(dirname "$0")"

echo ""
echo "====================================="
echo "   Spelling Practice Launcher"
echo "====================================="
echo ""

# Use system python3 (dependencies installed globally)
echo "Starting Spelling Practice..."
echo ""
python3 spelling_practice.py

echo ""
echo "Press any key to exit..."
read -n 1 -s
