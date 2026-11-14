# Which device can use this? (honest answers)

The editor works on **files**: your game's `index` file and your save file. Whether you can reach those files depends on the device, not on this program.

| Device | Ready-made app | Can it find the game's files? |
|---|---|---|
| **Windows (Microsoft Store game)** | Yes: build it with `build_exe.bat` | Yes, automatic. This is the tested path. |
| **Windows without Python** | `build_exe.bat` installs Python for you | Yes |
| **macOS** | `sh build_app.sh` on the Mac | Only if you can get the game's save folder onto the Mac. There is no standard place, so the app asks you to paste the folder. Untested. |
| **Linux** | `sh build_app.sh` on Linux | Same as Mac: paste the folder (for example a copy from Steam Proton or a device). Untested. |
| **Android** | No app | The game keeps its files in a private area that normal apps and the phone's file manager cannot open. Without root you cannot reach them. With root (your own phone, your own risk) you can copy the files to a folder, or run the editor in Termux (see below). Untested. |
| **iPhone / iPad** | No app | iOS does not let any app read another app's files, and there is no way around that without a jailbreak. Not supported. |

## Making the app (no GitHub, no Python knowledge)
Double-click `build_exe.bat` (Windows) or run `sh build_app.sh` (Mac/Linux). It finds or installs Python, builds the app and puts it in `AB2-Editor-Ready`. Each system builds its own: a Windows .exe only on Windows, a Mac app only on a Mac, a Linux app only on Linux. To share a Windows .exe, build it yourself and upload it by hand to the Releases page.

## Android and APK
A real APK cannot be made from this project in a useful way: the game's files are in a private area an APK cannot open without root, and building an APK needs the Android toolchain. Use Termux (below) on a rooted phone instead.

## If you do run from source (Windows)
Double-click `start_app.bat`. It looks for `py`, then `python`, then `python3`, then the usual install folders, and ignores the Microsoft Store stub that opens a store page. If it finds nothing, it offers to install Python with winget, or opens python.org. If Windows just installed it, close the window and double-click again.

## macOS / Linux from source
`sh start_app.sh` (needs Python 3.8+). macOS blocks unsigned downloaded apps: right-click the file, choose Open once. On Linux run `chmod +x AB2-Save-Editor` first if needed.

## Android with Termux (advanced, rooted phone only)
```
pkg install python python-cryptography
python ab2_app.py --no-browser
```
Open the printed `http://127.0.0.1:...` link in the phone's browser, paste the folder holding your copied `index` and save. Termux cannot see the game's private folder by itself.


## Tutorial video
Put your video in the `tutorial` folder and name it `tut.mp4` (or `tut.webm`). The app's **View tutorial** button plays it with the written steps under it. `build_exe.bat` and `build_app.sh` copy the `tutorial` folder into `dist` and `AB2-Editor-Ready` next to the app, so it ships with every build. Keep it reasonably small if you upload it to GitHub (a normal repo file limit is 100 MB; 25 MB or less is easy).
