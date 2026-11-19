package com.tinytools.ab2editor;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import java.io.File;
import java.io.InputStream;
import java.text.SimpleDateFormat;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int RC_PERM = 1, RC_TREE = 2;
    private final ExecutorService bg = Executors.newSingleThreadExecutor();

    private SharedPreferences prefs;
    private File stage, backups;
    private Access access;
    private String plain;       // decrypted save text, once loaded
    private byte[] indexBytes;

    private TextView statusAccess, statusKey, statusLoad, statusEdit;
    private EditText keyBox, fGems, fSecondary, fFree, fExpress, fEntry, fArena, fCampaign, fBird, fSpells;

    // ------------------------------------------------------------------ UI
    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences("ab2", MODE_PRIVATE);
        File base = getExternalFilesDir(null);
        if (base == null) base = getFilesDir();
        stage = new File(base, "stage");
        backups = new File(base, "backups");

        ScrollView sv = new ScrollView(this);
        sv.setBackgroundColor(Color.parseColor("#DFF1FF"));
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(14), dp(18), dp(14), dp(30));
        sv.addView(root);
        setContentView(sv);

        TextView title = text("🐦 AB2 Save Editor", 26, true);
        title.setTextColor(Color.parseColor("#1E3A5F"));
        root.addView(title);
        TextView sub = text("Made with ♥ by Shahzaib · Android (experimental)", 13, false);
        sub.setTextColor(Color.parseColor("#4A6A8A"));
        root.addView(sub);
        root.addView(button("📖 How to (10 languages)", v -> showGuide()));

        // 1. access
        LinearLayout c1 = card(root, "1 · Reach the game's save");
        statusAccess = note(c1, "Not checked yet. Close Angry Birds 2 first.");
        c1.addView(button("🔍 Check access", v -> checkAccess()));
        c1.addView(button("📂 Pick folder (Android 11–12)", v -> pickFolder()));
        c1.addView(button("🔓 Allow Shizuku (Android 13+, no root)", v -> {
            if (!ShizukuHelper.running()) statusAccess.setText("Shizuku is not running. Install it, start it with Wireless Debugging, then try again.");
            else { ShizukuHelper.request(); statusAccess.setText("Allow the prompt, then press Check access."); }
        }));

        // 2. key
        LinearLayout c2 = card(root, "2 · Your key");
        statusKey = note(c2, prefs.getString("key", null) != null ? "✔ A key is saved on this phone." : "Paste your key below (512 characters).");
        keyBox = new EditText(this);
        keyBox.setHint("Key (512 hex characters)");
        keyBox.setTextSize(11);
        keyBox.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        c2.addView(keyBox);
        c2.addView(button("💾 Save key", v -> saveKey()));

        // 3. load
        LinearLayout c3 = card(root, "3 · Read my save");
        statusLoad = note(c3, "Nothing loaded yet.");
        c3.addView(button("📥 Load my save", v -> loadSave()));

        // 4. edit
        LinearLayout c4 = card(root, "4 · Choose your changes (empty = keep)");
        fGems = field(c4, "Gems (0–999,999,999)");
        fSecondary = field(c4, "Feathers and coins");
        fFree = field(c4, "Bird tokens");
        fExpress = field(c4, "Express tickets");
        fEntry = field(c4, "Entry tickets");
        fArena = field(c4, "Arena tickets");
        fCampaign = field(c4, "Campaign level (1–" + SaveEditor.MAX_CAMPAIGN + ")");
        fBird = field(c4, "Main bird level (1–" + SaveEditor.MAX_BIRD_LEVEL + ")");
        fSpells = field(c4, "Spells each (0–" + SaveEditor.MAX_SPELLS + ")");
        statusEdit = note(c4, "");
        c4.addView(button("✏️ Apply changes", v -> applyEdit()));

        // 5. install + restore
        LinearLayout c5 = card(root, "5 · Put it in the game");
        note(c5, "Close the game first. A backup of the original is saved automatically.");
        c5.addView(button("🚀 Install to game", v -> confirmInstall()));
        c5.addView(button("♻️ Restore a backup", v -> pickBackup()));

        TextView foot = note(root, "Use at your own risk. Editing game data can affect your account, so keep a backup. Not affiliated with Rovio.");
        foot.setPadding(0, dp(16), 0, 0);
    }

    private int dp(int v) { return (int) (v * getResources().getDisplayMetrics().density + 0.5f); }

    private TextView text(String s, int sp, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(sp);
        t.setTextColor(Color.parseColor("#22364D"));
        if (bold) t.setTypeface(t.getTypeface(), android.graphics.Typeface.BOLD);
        return t;
    }

    private TextView note(LinearLayout parent, String s) {
        TextView t = text(s, 13, false);
        t.setPadding(0, dp(4), 0, dp(4));
        parent.addView(t);
        return t;
    }

    private Button button(String label, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setOnClickListener(l);
        return b;
    }

    private LinearLayout card(LinearLayout parent, String title) {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setPadding(dp(14), dp(12), dp(14), dp(12));
        GradientDrawable g = new GradientDrawable();
        g.setColor(Color.WHITE);
        g.setCornerRadius(dp(16));
        c.setBackground(g);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        lp.topMargin = dp(12);
        parent.addView(c, lp);
        c.addView(text(title, 17, true));
        return c;
    }

    private EditText field(LinearLayout parent, String hint) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setInputType(InputType.TYPE_CLASS_NUMBER);
        parent.addView(e);
        return e;
    }

    private void ui(Runnable r) { runOnUiThread(r); }

    private void say(TextView t, String s) { ui(() -> t.setText(s)); }

    // ------------------------------------------------------------------ access
    private Access.Runner rootRunner() {
        return (cmd, out) -> {
            Process p = new ProcessBuilder("su", "-c", cmd).redirectErrorStream(true).start();
            try (InputStream in = p.getInputStream()) {
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) > 0) out.append(new String(buf, 0, n, "UTF-8"));
            }
            return p.waitFor();
        };
    }

    private Access detect() {
        try {   // 1) root
            StringBuilder o = new StringBuilder();
            if (rootRunner().run("id", o) == 0 && o.toString().contains("uid=0")) return new Access.Shell("Root", rootRunner());
        } catch (Throwable ignored) { }
        if (ShizukuHelper.running() && ShizukuHelper.granted()) return new Access.Shell("Shizuku", ShizukuHelper.runner());
        if (Build.VERSION.SDK_INT <= 29) return new Access.Direct();
        if (Build.VERSION.SDK_INT <= 32) {
            String u = prefs.getString("tree", null);
            if (u != null) return new Access.Saf(this, Uri.parse(u));
        }
        return null;
    }

    private String noAccessText() {
        if (Build.VERSION.SDK_INT <= 32)
            return "Press “Pick folder” and choose Android › data › " + Access.PKG + ", then press “Check access” again. (Or use root / Shizuku.)";
        return "Android 13 and newer blocks apps from the game's folder. Use root, or install Shizuku, start it with Wireless Debugging, press “Allow Shizuku”, then “Check access”. See How to.";
    }

    private void checkAccess() {
        if (Build.VERSION.SDK_INT >= 23 && Build.VERSION.SDK_INT <= 29
                && checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.READ_EXTERNAL_STORAGE, Manifest.permission.WRITE_EXTERNAL_STORAGE}, RC_PERM);
            say(statusAccess, "Please allow storage access in the prompt.");
            return;
        }
        say(statusAccess, "Checking… (a root prompt may appear)");
        bg.execute(() -> {
            Access a = detect();
            if (a == null) { say(statusAccess, noAccessText()); return; }
            try {
                a.pull(stage);
                File s = Access.findSave(stage);
                if (s == null) throw new Exception("The game's save file was not found. Open the game once, then close it.");
                File bk = new File(backups, "game_" + new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date()));
                bk.mkdirs();
                for (File f : stage.listFiles()) Access.copyFile(f, new File(bk, f.getName()));
                access = a;
                plain = null;
                say(statusAccess, "✔ " + a.name() + ": save found (" + s.length() + " bytes). Backup saved.");
            } catch (Exception e) {
                say(statusAccess, "✖ " + a.name() + ": " + e.getMessage());
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int rc, String[] perms, int[] res) {
        super.onRequestPermissionsResult(rc, perms, res);
        if (rc == RC_PERM) checkAccess();
    }

    private void pickFolder() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION | Intent.FLAG_GRANT_PREFIX_URI_PERMISSION);
        if (Build.VERSION.SDK_INT >= 26)
            i.putExtra("android.provider.extra.INITIAL_URI",
                    Uri.parse("content://com.android.externalstorage.documents/document/primary%3AAndroid%2Fdata%2F" + Access.PKG));
        try { startActivityForResult(i, RC_TREE); }
        catch (Exception e) { say(statusAccess, "This phone has no folder picker."); }
    }

    @Override
    protected void onActivityResult(int rc, int res, Intent data) {
        super.onActivityResult(rc, res, data);
        if (rc == RC_TREE && res == RESULT_OK && data != null && data.getData() != null) {
            Uri u = data.getData();
            try {
                getContentResolver().takePersistableUriPermission(u, Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
            } catch (Exception ignored) { }
            prefs.edit().putString("tree", u.toString()).apply();
            checkAccess();
        }
    }

    // ------------------------------------------------------------------ key / load / edit
    private void saveKey() {
        byte[] k = Ab2Core.cleanHex(keyBox.getText().toString());
        if (k == null) { statusKey.setText("✖ That is not a valid key: it must be exactly 512 characters (0–9, a–f)."); return; }
        prefs.edit().putString("key", keyBox.getText().toString().replaceAll("\\s+", "")).apply();
        keyBox.setText("");
        statusKey.setText("✔ Key saved on this phone.");
    }

    private byte[] readAll(File f) throws Exception { return Access.readAll(f); }

    private void loadSave() {
        bg.execute(() -> {
            try {
                if (access == null) throw new Exception("Do step 1 first (Check access).");
                byte[] key = Ab2Core.cleanHex(prefs.getString("key", ""));
                if (key == null) throw new Exception("Do step 2 first (save your key).");
                indexBytes = readAll(new File(stage, Ab2Core.INDEX_NAME));
                plain = Ab2Core.decrypt(readAll(Access.findSave(stage)), indexBytes, key);
                say(statusLoad, "✔ Loaded.\n" + SaveEditor.summary(plain));
            } catch (Exception e) {
                plain = null;
                say(statusLoad, "✖ " + e.getMessage());
            }
        });
    }

    private Long lng(EditText e) {
        String s = e.getText().toString().trim();
        if (s.isEmpty()) return null;
        try { return Long.parseLong(s); } catch (NumberFormatException x) { throw new IllegalArgumentException("Not a number: " + s); }
    }

    private Integer integer(EditText e) {
        Long l = lng(e);
        if (l == null) return null;
        if (l > Integer.MAX_VALUE) throw new IllegalArgumentException("Number too big: " + l);
        return l.intValue();
    }

    private void applyEdit() {
        final SaveEditor.Request r = new SaveEditor.Request();
        try {
            r.gems = lng(fGems); r.secondary = lng(fSecondary); r.freeTokens = lng(fFree);
            r.express = lng(fExpress); r.entry = lng(fEntry); r.arena = lng(fArena);
            r.campaign = integer(fCampaign); r.birdLevel = integer(fBird); r.spells = integer(fSpells);
        } catch (IllegalArgumentException e) { statusEdit.setText("✖ " + e.getMessage()); return; }
        bg.execute(() -> {
            try {
                if (plain == null) throw new Exception("Do step 3 first (Load my save).");
                byte[] key = Ab2Core.cleanHex(prefs.getString("key", ""));
                String edited = SaveEditor.apply(plain, r);
                byte[] enc = Ab2Core.encrypt(edited, indexBytes, key);
                if (!Ab2Core.decrypt(enc, indexBytes, key).equals(edited)) throw new Exception("Safety check failed. Nothing was changed.");
                Access.writeAll(Access.findSave(stage), enc);
                plain = edited;
                say(statusEdit, "✔ Changed (not in the game yet; do step 5).\n" + SaveEditor.summary(plain));
            } catch (IllegalArgumentException e) {
                say(statusEdit, "✖ " + e.getMessage());
            } catch (Exception e) {
                say(statusEdit, "✖ " + e.getMessage());
            }
        });
    }

    // ------------------------------------------------------------------ install / restore
    private void confirmInstall() {
        new AlertDialog.Builder(this).setTitle("Install to game?")
                .setMessage("Is Angry Birds 2 closed? This replaces the save in the game. The original is already backed up.")
                .setPositiveButton("Install", (d, w) -> install())
                .setNegativeButton("Cancel", null).show();
    }

    private void install() {
        bg.execute(() -> {
            try {
                if (access == null) throw new Exception("Do step 1 first.");
                access.push(stage);
                say(statusEdit, "✔ Installed. Open the game (it needs internet to load).");
            } catch (Exception e) {
                say(statusEdit, "✖ " + e.getMessage());
            }
        });
    }

    private void pickBackup() {
        File[] dirs = backups.listFiles();
        if (dirs == null || dirs.length == 0) { statusEdit.setText("No backups yet."); return; }
        Arrays.sort(dirs, Collections.reverseOrder());
        final File[] list = dirs;
        String[] names = new String[list.length];
        for (int i = 0; i < list.length; i++) names[i] = list[i].getName();
        new AlertDialog.Builder(this).setTitle("Restore which backup?")
                .setItems(names, (d, i) -> askCode(list[i])).show();
    }

    private void askCode(File backup) {
        final EditText code = new EditText(this);
        code.setHint("222");
        code.setInputType(InputType.TYPE_CLASS_NUMBER);
        new AlertDialog.Builder(this).setTitle("Type 222 to restore")
                .setMessage("This puts the backup " + backup.getName() + " back into the game.")
                .setView(code)
                .setPositiveButton("Restore", (d, w) -> {
                    if (!"222".equals(code.getText().toString().trim())) { statusEdit.setText("Wrong code. Nothing was restored."); return; }
                    restore(backup);
                }).setNegativeButton("Cancel", null).show();
    }

    private void restore(File backup) {
        bg.execute(() -> {
            try {
                if (access == null) throw new Exception("Do step 1 first.");
                Access.clean(stage);
                for (File f : backup.listFiles()) Access.copyFile(f, new File(stage, f.getName()));
                access.push(stage);
                plain = null;
                say(statusEdit, "✔ Restored " + backup.getName() + ". Load your save again before editing.");
            } catch (Exception e) {
                say(statusEdit, "✖ " + e.getMessage());
            }
        });
    }

    // ------------------------------------------------------------------ how-to
    private void showGuide() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(14), dp(8), dp(14), dp(8));
        Spinner sp = new Spinner(this);
        String[] labels = new String[Guide.LANGS.length];
        for (int i = 0; i < labels.length; i++) labels[i] = Guide.LANGS[i][1];
        sp.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, labels));
        box.addView(sp);
        final TextView tv = text("", 15, false);
        tv.setPadding(0, dp(10), 0, 0);
        ScrollView s = new ScrollView(this);
        s.addView(tv);
        box.addView(s, new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(380)));
        sp.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            @Override public void onItemSelected(AdapterView<?> p, View v, int pos, long id) {
                String code = Guide.LANGS[pos][0];
                tv.setText(Guide.load(MainActivity.this, code));
                boolean rtl = Guide.rtl(code);
                tv.setTextDirection(rtl ? View.TEXT_DIRECTION_RTL : View.TEXT_DIRECTION_LTR);
                tv.setGravity(rtl ? Gravity.END : Gravity.START);
            }
            @Override public void onNothingSelected(AdapterView<?> p) { }
        });
        new AlertDialog.Builder(this).setTitle("📖 How to").setView(box).setPositiveButton("Close", null).show();
    }
}
