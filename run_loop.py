"""Run loop — 3 chapters"""
import sys, os
sys.path.insert(0, '.agents/skills/story-engine/tools')
base = os.path.dirname(os.path.abspath(__file__))
os.environ['API_KEY'] = 'sk-ad9450b1670b485c8a456a52520dc5a8'

from loop_engine import run_loop

print("Loop: 3 chapters x 3 rounds")
history = run_loop('configs/test_female.json', start=1, end=3, max_loops=3)
print("Done")
