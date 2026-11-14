# AB2 Save Editor

A guided, friendly editor for your **own, local** *Angry Birds 2* save on Windows (Microsoft Store version).
Open it, follow five steps, done: **Check, Load, Edit, Review, Install**.

Made by **Shahzaib**

> ## Read this first
> * **Use at your own risk.** Editing a save can break it and may break the game's Terms of Service. The game checks
>   accounts against Rovio's servers, so an edited account can be reset, flagged or banned. **Nothing here makes an
>   account undetectable, and no number is "safe".**
> * Every step makes backups. Make your own copy of the save folder too.
> * This project does **not** swap account IDs, bypass bans, hide edits, or touch servers, and won't be extended to do that.
> * Never edit with memory tools (Cheat Engine etc.) while the game runs: the game logs altered values in the save.
> * Your account data (`index`, the save, `decrypted_save.json`, backups) is private. Never upload it. `.gitignore` blocks it.
> * Not affiliated with or endorsed by Rovio or Sega.

## What you get
* **A window (runs in your browser, on your PC only)** with a flight-path stepper:
  1. **Check**: game closed? save folder found? key present?
  2. **Load**: copies the *whole* save folder to `game_backups/`, then reads your save
  3. **Edit**: currency, campaign level, bird levels (up to the game's own table, 49), spells, hat tiers; "Undo last edit"
  4. **Review**: encrypts, verifies it decrypts back identically, shows a before/after table
  5. **Install**: re-checks everything, backs up again, replaces **only** the save file
* **Backups tab**: restore any numbered backup in one click (your current files are backed up first).
* **Safety checks**: refuses to install if the game is running or if the game's `index` changed (it would not be readable).
* **Command line too**: `run_all.py` (everything in one go), `run_decrypt.py`, `json_editor.py`, `run_encrypt.py`, `restore.py`, `show_birds.py`.
* Handles both save formats (old and the newer 36-byte-header one) automatically. No other tool needed.

## Start it
* **.exe:** double-click `build_exe.bat` once. It finds or installs Python, builds the app and puts it in
  `AB2-Editor-Ready`. Mac/Linux: `sh build_app.sh`. Nothing is built on GitHub; you build on your own computer.
  Windows SmartScreen may warn about an unsigned program you built yourself; that's expected.
* **Python:** install Python 3.9+, run `pip install -r requirements.txt`, then double-click `start_app.bat`
  (or `py ab2_app.py`).

### The XOR key
The save is locked with a 256-byte key that is **not included** in this project (the original AB2E project doesn't
include it either), and this project doesn't explain how to extract it. The first screen of the app asks for your
key file (`xor_key.bin`, 256 raw bytes, or `xor_key.hex`, 512 hex characters). It is stored next to the program. Never commit it.

## Using it
1. Close Angry Birds 2 completely (check Task Manager).
2. Start the app and follow the steps. The game's save folder is found automatically:
   `%LOCALAPPDATA%\Packages\1ED5AEA5.4160926B82DB_p2gbknwb5d8r2\LocalState\save`
3. Start the game (this version needs the internet to pass the loading screen). If it resets or hangs: close it and
   use the **Backups** tab (or `py restore.py`) to put the backup back.

## Troubleshooting
| Problem | Cause / fix |
|---|---|
| "Key missing" | Add your key file on the first screen. |
| "not a matching pair" | The game made a new `index`. Use step 2 (**Load**) again. |
| "game seems to be running" | Close the game fully; check Task Manager. |
| Game shows a fresh account | The save wasn't accepted. Restore a backup (Backups tab). |
| "Select file encoding" box when uploading saves to a website | Zip the save files first; never upload binary files as text. |

## Notes
* Tested with the Microsoft Store build **3.17.12**.
* Only save data is changed. Slingshot, hatchling and energy are **not** stored in the save file, so they can't be edited. Extra birds like *Shade* are not handled yet.

## Credits
* **Shahzaib**: idea, testing, project owner.
* **Claude** (Anthropic): wrote and iterated the code with Shahzaib.
* **AB2E, "Angry Birds 2 Editor"**: the community tool that documented how these saves are encrypted. This project has its own implementation and includes none of AB2E's code. Release thread: https://gbatemp.net/threads/release-ab2e-angry-birds-2-editor.485651/
* *Angry Birds 2* is a trademark of Rovio Entertainment / Sega. This is an unofficial fan tool.

## License
MIT (see `LICENSE`).


## Close the game button
If Angry Birds is still open, step 1 shows a **Close Angry Birds** button. It force-closes every process with "angrybirds" in its name, then re-checks. (Unsaved game progress is lost.)

## Unrestricted mode ("not allowed")
Normal mode lets you set any amount of currency, but bird levels stop at 49 and spells at 20; going higher asks you to type `its on my own`. The red **Unrestricted mode (not allowed)** button lifts those limits (any amount of items or levels) but only after three warnings; the third requires typing `its on my own`. Rovio's game logs altered values, so this can get an account flagged or banned. You do it entirely at your own risk. Nothing here helps with bans, other people's accounts, or hiding the game's log.


## Backups and restore code
Every load and install makes a full copy of the save folder in `game_backups`. In the **Backups** tab pick one and press Restore; the app asks you to type **222** to confirm. A restore puts the folder back exactly as it was in that backup (index and save together), checks every file byte for byte, backs up what was there first, and clears this program's working copies so an edited file can never be mixed with a restored one.

## Other devices
See [PLATFORMS.md](PLATFORMS.md): Windows (no Python needed), macOS, Linux, and what is and is not possible on Android and iOS.

Made with love by Shahzaib.
