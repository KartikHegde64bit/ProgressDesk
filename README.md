# ProgressDesk

A small Windows desktop app for tracking progress across learning goals, watchlists, reading plans, and custom projects.

## Run

Double-click `ProgressDesk.bat` or `ProgressDesk.pyw` for the app-style launcher without a terminal window. For debugging, run:

```powershell
python task_tracker.py
```

## What It Tracks

- A left sidebar with Current, To Watch, Movies, Series, and other project views.
- A search bar with a `Search here` placeholder for quick filtering.
- A Current tab for items you have started or made progress on.
- A To Watch tab for untouched movie and series items.
- Progress as completed units out of total units.
- Remaining time based on the estimated hours you enter.
- Active time spent with a start/pause timer.
- Categories for Learning, Series, Movies, Reading, and Custom goals.
- A one-time movie and series watchlist seed that adds missing items without duplicating existing ones.
- Optional Windows startup launch from the in-app Settings window.
- A shutdown prompt that can cancel shutdown so you can review your progress first.

Your data is stored locally at:

```text
%LOCALAPPDATA%\ProgressDesk\tasks.json
```

## Examples

- System Design: total `5`, unit name `designs`, estimated hours `20`.
- Series: total `12`, unit name `episodes`, estimated hours `9`.
- Movie watchlist: total `8`, unit name `movies`, estimated hours `16`.
