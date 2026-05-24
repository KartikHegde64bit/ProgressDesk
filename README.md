# ProgressDesk

A small Windows desktop app for tracking progress across learning goals, watchlists, reading plans, and custom projects.

## Run

Double-click `run.bat` or `ProgressDesk.pyw` for the app-style launcher without a terminal window. For debugging, run:

```powershell
python task_tracker.py
```

## What It Tracks

- Progress as completed units out of total units.
- Remaining time based on the estimated hours you enter.
- Active time spent with a start/pause timer.
- Categories for Learning, Series, Movies, Reading, and Custom goals.

Your data is stored locally at:

```text
%LOCALAPPDATA%\ProgressDesk\tasks.json
```

## Examples

- System Design: total `5`, unit name `designs`, estimated hours `20`.
- Series: total `12`, unit name `episodes`, estimated hours `9`.
- Movie watchlist: total `8`, unit name `movies`, estimated hours `16`.
