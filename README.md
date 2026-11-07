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

## Install
Download **EyeCare-Setup.exe** from the [latest release](https://github.com/imhamiddev/Eyes-protect/releases/latest)
and run it. It installs per-user (no admin rights), adds a Start-menu entry (optional desktop shortcut),
starts Eye Care with Windows and registers an uninstaller in *Apps & features*.

## Build the installer
Push a tag like `v0.2.0` (or run the *Build Windows installer* workflow). Locally:
`pyinstaller eyecare.spec`, then compile `installer/eyecare.iss` with Inno Setup 6.

## Notes
Night light and dimmer use the display gamma ramp; Windows limits how dark it can go, so
brightness is clamped to 30%. Settings live in `%APPDATA%\EyeCare`.
Fonts: Inter and Vazirmatn (SIL OFL). Icons: Lucide-style (ISC).
