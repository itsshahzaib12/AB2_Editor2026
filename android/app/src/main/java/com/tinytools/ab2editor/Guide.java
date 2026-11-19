package com.tinytools.ab2editor;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;

/** The "How to" guide, shipped in several languages as text files in assets/guide. */
final class Guide {
    static final String[][] LANGS = {
            {"en", "English"}, {"ur", "اردو (Urdu)"}, {"hi", "हिन्दी (Hindi)"}, {"ar", "العربية (Arabic)"},
            {"es", "Español"}, {"pt", "Português"}, {"fr", "Français"}, {"ru", "Русский"},
            {"id", "Bahasa Indonesia"}, {"tr", "Türkçe"}};

    private Guide() {}

    static boolean rtl(String code) { return "ur".equals(code) || "ar".equals(code); }

    static String load(Context c, String code) {
        try (InputStream in = c.getAssets().open("guide/guide_" + code + ".txt")) {
            ByteArrayOutputStream b = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = in.read(buf)) > 0) b.write(buf, 0, n);
            return b.toString("UTF-8");
        } catch (Exception e) {
            return "Guide not found for '" + code + "'.";
        }
    }
}
