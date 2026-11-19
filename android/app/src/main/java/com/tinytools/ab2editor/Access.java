package com.tinytools.ab2editor;

import android.content.Context;
import android.net.Uri;

import androidx.documentfile.provider.DocumentFile;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * Ways to reach the game's save folder. Every method copies the save and 'index' into a
 * staging folder (pull), and copies the edited save back (push). The editing itself always
 * happens on the staging copy.
 */
public abstract class Access {
    public static final String PKG = "com.rovio.baba";
    public static final String SRC = "/storage/emulated/0/Android/data/" + PKG + "/files/save";
    private static final String SAVE_PREFIX = Ab2Core.SAVE_NAME.substring(0, 40).toUpperCase();

    public abstract String name();
    public abstract void pull(File stage) throws Exception;
    public abstract void push(File stage) throws Exception;

    static boolean isSave(String n) { return n != null && n.toUpperCase().startsWith(SAVE_PREFIX); }
    static boolean isWanted(String n) { return isSave(n) || Ab2Core.INDEX_NAME.equals(n); }

    public static File findSave(File dir) {
        File[] fs = dir.listFiles();
        if (fs != null) for (File f : fs) if (isSave(f.getName())) return f;
        return null;
    }

    static void copy(InputStream in, OutputStream out) throws IOException {
        byte[] buf = new byte[16384];
        int n;
        while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
        out.flush();
    }

    static void copyFile(File a, File b) throws IOException {
        try (InputStream in = new FileInputStream(a); OutputStream out = new FileOutputStream(b, false)) { copy(in, out); }
    }

    static byte[] readAll(File f) throws IOException {
        try (InputStream in = new FileInputStream(f)) {
            java.io.ByteArrayOutputStream b = new java.io.ByteArrayOutputStream();
            copy(in, b);
            return b.toByteArray();
        }
    }

    static void writeAll(File f, byte[] data) throws IOException {
        try (OutputStream out = new FileOutputStream(f, false)) { out.write(data); out.flush(); }
    }

    static void clean(File stage) {
        stage.mkdirs();
        File[] fs = stage.listFiles();
        if (fs != null) for (File f : fs) f.delete();
    }

    // ----- Android 10 and older: plain storage permission -------------------------------
    public static class Direct extends Access {
        public String name() { return "Storage permission (Android 10 and older)"; }

        public void pull(File stage) throws Exception {
            File dir = new File(SRC);
            File[] fs = dir.listFiles();
            if (fs == null) throw new IOException("Cannot read " + SRC + ". Is the storage permission allowed, and has the game been opened once?");
            clean(stage);
            for (File f : fs) if (f.isFile() && isWanted(f.getName())) copyFile(f, new File(stage, f.getName()));
        }

        public void push(File stage) throws Exception {
            File s = findSave(stage);
            if (s == null) throw new IOException("Nothing to install: the staging save is missing.");
            copyFile(s, new File(SRC, s.getName()));
        }
    }

    // ----- Android 11 and 12: the folder picker (SAF) -----------------------------------
    public static class Saf extends Access {
        private final Context ctx;
        private final Uri tree;

        public Saf(Context ctx, Uri tree) { this.ctx = ctx; this.tree = tree; }

        public String name() { return "Folder picker (Android 11 and 12)"; }

        private static DocumentFile find(DocumentFile d, int depth) {
            if (d == null || depth > 5) return null;
            if ("save".equals(d.getName()) && d.isDirectory()) return d;
            for (DocumentFile c : d.listFiles()) {
                String n = c.getName();
                if (c.isDirectory() && ("save".equals(n) || "files".equals(n) || PKG.equals(n) || "data".equals(n) || "Android".equals(n))) {
                    DocumentFile r = find(c, depth + 1);
                    if (r != null) return r;
                }
            }
            return null;
        }

        private DocumentFile saveDir() throws IOException {
            DocumentFile r = find(DocumentFile.fromTreeUri(ctx, tree), 0);
            if (r == null) throw new IOException("The picked folder does not contain the game's 'save' folder. Pick Android > data > " + PKG + " (or its 'files' / 'save' folder).");
            return r;
        }

        public void pull(File stage) throws Exception {
            DocumentFile dir = saveDir();
            clean(stage);
            for (DocumentFile f : dir.listFiles()) {
                if (f.isFile() && isWanted(f.getName())) {
                    try (InputStream in = ctx.getContentResolver().openInputStream(f.getUri());
                         OutputStream out = new FileOutputStream(new File(stage, f.getName()))) { copy(in, out); }
                }
            }
        }

        public void push(File stage) throws Exception {
            File s = findSave(stage);
            if (s == null) throw new IOException("Nothing to install: the staging save is missing.");
            DocumentFile target = null;
            for (DocumentFile f : saveDir().listFiles()) if (s.getName().equals(f.getName())) target = f;
            if (target == null) throw new IOException("The game's save file was not found in the picked folder.");
            try (InputStream in = new FileInputStream(s); OutputStream out = ctx.getContentResolver().openOutputStream(target.getUri(), "wt")) { copy(in, out); }
        }
    }

    // ----- Root or Shizuku: run shell commands ------------------------------------------
    public interface Runner { int run(String cmd, StringBuilder out) throws Exception; }

    public static class Shell extends Access {
        private final Runner runner;
        private final String label;

        public Shell(String label, Runner runner) { this.label = label; this.runner = runner; }

        public String name() { return label; }

        private void sh(String cmd) throws Exception {
            StringBuilder out = new StringBuilder();
            int code = runner.run(cmd, out);
            if (code != 0) throw new IOException("Command failed (" + code + "): " + out.toString().trim());
        }

        public void pull(File stage) throws Exception {
            clean(stage);
            String s = stage.getAbsolutePath();
            sh("mkdir -p '" + s + "' && cp -f '" + SRC + "'/* '" + s + "'/ && chmod -R 666 '" + s + "'/*");
        }

        public void push(File stage) throws Exception {
            File sv = findSave(stage);
            if (sv == null) throw new IOException("Nothing to install: the staging save is missing.");
            String n = sv.getName();
            // 'cat >' overwrites the existing file in place, so its owner and permissions stay as the game made them
            sh("am force-stop " + PKG + "; cat '" + stage.getAbsolutePath() + "/" + n + "' > '" + SRC + "/" + n + "'");
        }
    }
}
