# Eye Care (eyes-protect)

A quiet Windows companion that protects your eyes. Runs in the tray, starts with Windows.

## Features
- **20-20-20 rule** – timer, desktop toast, snooze, natural-break detection (idle time).
- **Night light** – warmth slider, quick toggle, schedule by time.
- **Screen dimmer** – Day / Night / Reading profiles, separate night brightness, schedule.
- **Blink reminder**, **Hydration reminder**.
- **Eye exercises** – guided, auto-advancing routines.
- **Auto dark mode** – switches Windows between light and dark by time.
- **Break Lock** – full-screen break on every monitor, skippable.
- English + Persian (RTL), dark + light theme, per the visual identity in the design brief.

## Run from source (Windows)
```
pip install -r requirements.txt
python -m eyecare
```
`--background` starts hidden in the tray (this is what autostart uses).

## Build the exe
Push a tag like `v0.1.0` (or run the *Build Windows exe* workflow) and download `EyeCare.exe`,
or locally: `pip install -r requirements-dev.txt && pyinstaller eyecare.spec`.

## Notes
Night light and dimmer use the display gamma ramp; Windows limits how dark it can go, so
brightness is clamped to 30%. Settings live in `%APPDATA%\EyeCare`.
Fonts: Inter and Vazirmatn (SIL OFL). Icons: Lucide-style (ISC).
