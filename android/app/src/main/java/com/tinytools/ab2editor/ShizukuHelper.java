package com.tinytools.ab2editor;

import android.app.Activity;
import android.content.pm.PackageManager;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.lang.reflect.Method;

import rikka.shizuku.Shizuku;

/** All Shizuku code lives here. If it will not build, delete this file and the two lines that use it in MainActivity. */
final class ShizukuHelper {
    static final int REQ = 1001;

    private ShizukuHelper() {}

    static boolean running() {
        try { return Shizuku.pingBinder(); } catch (Throwable t) { return false; }
    }

    static boolean granted() {
        try { return Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED; } catch (Throwable t) { return false; }
    }

    static void request() {
        try { Shizuku.requestPermission(REQ); } catch (Throwable ignored) { }
    }

    static Access.Runner runner() {
        return (cmd, out) -> {
            Method m = Shizuku.class.getDeclaredMethod("newProcess", String[].class, String[].class, String.class);
            m.setAccessible(true);
            Process p = (Process) m.invoke(null, new String[]{"sh", "-c", cmd}, null, null);
            out.append(read(p.getInputStream())).append(read(p.getErrorStream()));
            return p.waitFor();
        };
    }

    private static String read(InputStream in) throws Exception {
        ByteArrayOutputStream b = new ByteArrayOutputStream();
        byte[] buf = new byte[4096];
        int n;
        while ((n = in.read(buf)) > 0) b.write(buf, 0, n);
        return b.toString("UTF-8");
    }
}
