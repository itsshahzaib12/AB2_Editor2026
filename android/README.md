# AB2 Save Editor - Android (experimental, untested)

A phone app for editing your own Angry Birds 2 save. Made with ♥ by Shahzaib.
Use at your own risk. Editing game data can affect your account. Not affiliated with Rovio.

**Status:** the save-reading and editing code was tested on a desktop against the PC editor
(the encrypted output is byte-for-byte identical). The phone screens and the access methods
(root, Shizuku, folder picker) were **not** compiled or run on a phone yet.
Expect to fix a few build errors on the first build.

## What it does
1. **Reach the save.** The game's save is in `Android/data/com.rovio.baba/files/save/`. The app tries, in order:
   root, Shizuku, plain storage permission (Android 10 and older), folder picker (Android 11-12).
   Android 13+ without root needs Shizuku (free app, started with Wireless Debugging).
2. **Your key.** You paste your own key; it is stored only on the phone. No key is included in this project.
3. **Load, edit, install.** Same limits as the PC editor's locked mode: money up to 999,999,999,
   bird level up to 49, spells up to 20.
4. **Backups.** A backup of the game's files is saved every time you press "Check access".
   "Restore a backup" asks for the code 222.
5. **How to** button: guide in 10 languages (`app/src/main/assets/guide/`).

## Build the APK (no GitHub, no auto-build)
1. Install **Android Studio**.
2. *File > Open* and pick this folder. Let it sync (it downloads Gradle and the Android SDK).
3. *Build > Build Bundle(s) / APK(s) > Build APK(s)*.
4. The APK is in `app/build/outputs/apk/debug/`. Copy it to a phone and install it
   (allow "install unknown apps").

## If the build fails
- Shizuku lines will not resolve: delete the two `dev.rikka.shizuku` lines in `app/build.gradle`,
  delete `ShizukuHelper.java`, and remove the 3 lines that mention `ShizukuHelper` in `MainActivity.java`
  (the app then supports root, folder picker and Android 10 only).
- Anything else: copy the red error text and send it to whoever helps you with the code.

## Files
- `Ab2Core.java` encryption/decryption (tested)
- `SaveEditor.java` the edits (tested with a stand-in JSON library)
- `Access.java` the ways to reach the game's folder
- `ShizukuHelper.java` Shizuku support (optional)
- `MainActivity.java` the screens
- `Guide.java` + `assets/guide/*.txt` the multi-language guide
