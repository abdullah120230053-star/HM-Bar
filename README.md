# HM-Bar

**Music, tools, and phone transfers within reach on Windows.**

HM-Bar adds a compact, animated island to the top of your desktop. Hover to check what is playing, scrub through a song, or see your current panel. Double-click to open a grid of apps and tools. Use it while working in another window, then press **Ctrl+H** when you want the screen clear.

![Animated HM-Bar tour showing song controls, the seek bar, and the desktop app grid](docs/assets/hm-bar-in-action.gif)

## Get started

1. Download **HM-Bar.exe** and **HM-Bar-Settings.exe** from the [latest Windows x64 release](https://github.com/abdullah120230053-star/HM-Bar/releases/latest).
2. Put both executables in the same folder and open **HM-Bar.exe**.
3. Double-click the island and choose **Themes & Settings** to customize it.

| Gesture | What it does |
| --- | --- |
| Hover | Expand the selected panel. |
| Scroll | Switch panels. |
| Double-click | Open the animated app grid. |
| Middle-click | Open the optional clipboard history. |
| Right-click | Change settings, toggle synced lyrics, or quit. |
| Ctrl+H | Hide or restore the island from anywhere in Windows. |

## What you can do with HM-Bar

| Feature | How it works |
| --- | --- |
| **Music and Spotify** | See the current track and artwork, play or pause, and skip tracks. Use Spotify priority to select Spotify ahead of other media apps. Hover over Music and click or drag the seek bar to jump to a new timestamp when the player supports seeking. |
| **Artwork and lyrics** | Give cover art an animated intro before synced lyrics appear. Set the intro to 1–8 seconds, turn off the artwork animation, or hide lyrics while keeping the artwork and track visible. |
| **Focus, notes, and tasks** | Run a focus timer with presets or a custom duration, jot down notes that save automatically, and check your tasks and month progress. |
| **File Shelf** | Drop files, images, or web links onto the island, then open them or drag them back out into a compatible app. |
| **Clipboard history** | Opt in to keep your last five text or image copies in memory. Middle-click the island to browse, restore, or clear them. |
| **Weather and system panels** | See the forecast for a chosen location, CPU and memory usage, storage, network activity, and battery estimates. Open common Windows tools from Quick Apps. |
| **Screen and desktop tools** | Pick a screen color, snip text to the clipboard with Windows OCR, start a manual meeting timer, or snap a window left or right on an unscaled display. Open Windows audio, power, camera, and microphone settings. |
| **Project tools** | Choose a Git project to see its branch, tracked changes, and conflicts. Run its npm build on request and check active Docker containers when those tools are installed. |
| **AirPad** | See which phone is connected, open received files, add them to File Shelf, or offer a selected shelf file or clipboard item to the phone. |

## Set the look and motion

Choose **Obsidian**, **Aurora**, **Midnight**, **Ember**, or **Orchid**, and add a custom accent if you like. Try **Default**, **Liquid Glass**, or the edge-attached **Notch Nook**. The Settings app previews changes as you make them. Save to apply them to the running island.

Choose **Smooth**, **Fast**, or **Reduced** panel transitions. Media effects, launcher motion, and artwork animation have separate controls. You can also choose the default panel and opt in to starting HM-Bar with Windows.

![Animated appearance tour cycling through Obsidian, Aurora Notch Nook, and Orchid Liquid Glass](docs/assets/hm-bar-settings.gif)

## Link AirPad with one QR code

1. Open **AirPad for Windows** and **HM-Bar** on the same PC.
2. Scan the usual AirPad pairing QR on your phone, or reconnect a phone you already paired.
3. Double-click HM-Bar and choose **AirPad**. The phone appears once it connects to the Windows companion.

HM-Bar uses the existing connection. A second QR code is unnecessary. File and clipboard offers are initiated from HM-Bar and must be accepted in AirPad.

## Build from source

Use Windows x64, Python 3.11, and [uv](https://docs.astral.sh/uv/). Run the following from the repository folder in PowerShell:

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

To create the portable executables in `dist`, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Local preferences, notes, and file shortcuts are stored under `%LOCALAPPDATA%\DynamicIslandPro`. Weather and lyric lookup may need internet access. Media seeking and album artwork depend on what the player exposes to Windows. See the [full user guide](PRO.md) for setup, behavior, and limits.

## Contributing and credits

When reporting an issue, include your Windows version, the affected panel, and steps to reproduce. For changes, run both HM-Bar and Settings. For AirPad changes, check pairing with the Windows companion and a phone.

HM-Bar is based on [rajsriv/dynamic-island-for-windows](https://github.com/rajsriv/dynamic-island-for-windows) at commit `b4bce08`. The upstream README identifies the project as MIT and links to a license file that was absent from the source checkout. The demos use sample media.
