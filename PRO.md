# HM-Bar for Windows

Right-click the island to open **Settings** or **Workspace**. You can also launch `dist\HM-Bar-Settings.exe` directly. Keep both executables in the same folder for the menu shortcut. Settings apply while the island is running. Double-click the island to open the animated launcher grid for Timer, Notes, File Shelf, Spotify, Weather, Themes, and the other panels. Press **Ctrl+H** from anywhere in Windows to hide or restore the island. Hover to expand the original panels and scroll to switch panels. Use **Quit** in the same menu to close the app.

| Feature | What it does |
| --- | --- |
| Theme | Choose Obsidian, Aurora, Midnight, Ember, or Orchid. Custom accent overrides the preset accent until you select Reset accent. |
| Island Style | Switch between Default, Liquid Glass, and Notch Nook. |
| Media effects | Choose Glow Sweep, Fluid Blobs, Neon Border, or Off. Island transitions still animate. |
| Media source | Auto prefers apps that are playing and uses the Windows current session to break ties. Spotify first prefers Spotify even when it is paused. |
| Now playing | Show the current track on the collapsed island, switch the expanded panel to Media when a source appears, and optionally disable lyrics requests. |
| Panel and launcher motion | Choose Smooth, Fast, or Reduced transitions, and turn the launcher animation on or off separately. Appearance shows a live preview of your selected theme, accent, and shape. |
| Song position | Hover over the Music panel to see elapsed time and duration. Click or drag the seek bar to jump within players that support seeking through Windows. Use arrows for 5-second steps when the bar has focus. |
| Cover art and synced lyrics | Spotify and other media apps that expose a cover to Windows show it beside the track before lyrics appear. Change the 1?8 second intro and artwork animation in Settings. Turn off Show synced lyrics in Settings or the island menu to keep the track and cover visible. Lyrics stay inside the compact notch, with long lines shortened if needed. |
| Default panel | Choose which panel to start on. Scroll over the island to switch panels. |
| Focus | Pick 5, 25, or 50 minutes or enter 1–180 minutes. Pause, resume, or reset the timer. The idle island displays the countdown, and the app alerts you when it ends. |
| Notes | A plain text scratchpad that saves automatically on this computer. |
| File shelf | Add or drop local files, then double-click to open them. Removing an item removes its shortcut from the shelf. |
| Start with Windows | Enable or disable startup for this Windows account. Disabled by default. |

The original media and lyrics controls, weather, calendar, tasks, system metrics, keyboard indicators, and power tools are still available. Feature availability depends on Windows permissions, an active media session, and network access for weather and lyrics. Change the weather location from the island menu.

Settings, notes, and file shortcuts are stored in `%LOCALAPPDATA%\DynamicIslandPro\settings.json`. The settings app stores appearance and media preferences in `preferences.json` next to `settings.json`. The focus timer runs while the app is open.

Double-click `dist\HM-Bar.exe` to start the portable Windows x64 build. To run or rebuild from source in PowerShell:

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe main.py
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

Based on [rajsriv/dynamic-island-for-windows](https://github.com/rajsriv/dynamic-island-for-windows) at commit `b4bce08`. The upstream README declares MIT and links to a LICENSE file absent from that checkout. Feature research included [NotchIsland](https://github.com/Brozovec/NotchIsland-Windows) and [Peak](https://github.com/AinzDerErste/Peak).


If Spotify does not appear, play a track in the desktop app and select **Spotify first**. Browser playback only appears if the browser exposes it as a Windows media session.

## AirPad link and desktop tools

Open AirPad for Windows and HM-Bar on the same PC. Scan the normal AirPad pairing QR with the Android app. HM-Bar reads the companion's local dashboard and shows the authenticated phone connection in the launcher tile **AirPad**. Previously paired phones appear when they reconnect. A second QR and phone app update are unnecessary when the Windows companion supports the dashboard.

The AirPad page lists up to 30 recent received files. Open a file or add it to the existing File Shelf. Select a file in File Shelf, choose a connected phone in AirPad, and use **Send shelf file**. For **Send clipboard**, HM-Bar prepares the current text or image as a local file in the profile's AirPadShare directory. Accept the offer on the phone. AirPad handles pairing and transfer permissions.

Drop a file, image, or web link on the island or Workspace to stash it. Drag shelf entries out to apps that accept file and web links. Middle-click the island for the optional five-item Clipboard history. History entries stay in memory until cleared or the app exits.

**Desktop Tools** provides a battery estimate, Windows sound and power shortcuts, best-effort camera and microphone activity while the Workspace is open, a color picker, local Windows OCR, left and right snapping on unscaled monitors, a manual meeting timer, and Git, npm build, and Docker status for tools installed on the PC. Start with the Windows sound panel to choose an output. AirPad's existing phone-side media and meeting commands continue through its companion. HM-Bar reads media state from Windows.
