# 1945

A Python 3 and Pygame arcade shooter with varied enemy planes, boats, scrolling
islands, curved formations, and collectible weapon upgrades.

Based on [1945 by Haroon Khalid](https://github.com/sodacrunch/1945).
This fork preserves the original history and adds Python 3 support, gameplay
fixes, new enemy behavior, power-ups, and regression tests.

## Run

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python game.py
```

On Windows, activate with `.venv\Scripts\activate`.

## Controls

- Enter: start the game.
- Arrow keys: move.
- Space: fire.
- Left Ctrl: use a bomb.
- F1: start again after game over.
- Escape: exit.

Collect POW pickups for wingmen or triple fire. Shoot down every plane in a red
formation to earn another POW. Upgrades expire when your plane dies.

## Tests

```bash
python -m unittest discover -s tests
```

Tests use headless video and audio drivers.
