package com.tinytools.ab2editor;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/** Reads and writes the game's save format: AES-256-CBC, key and IV come from the 'index' file. */
public final class Ab2Core {
    public static final String SAVE_NAME = "B4F59D3E9582F13D98B85102B4003E377A9434837B71846F44C05637D2613FA1";
    public static final String INDEX_NAME = "index";
    private static final int HEADER_LEN = 36; // newer game builds prefix files with 36 bytes

    public static class CoreException extends Exception {
        public CoreException(String m) { super(m); }
    }

    private static final class Parsed {
        byte[] header; byte[] iv; byte[] key;
    }

    private Ab2Core() {}

    /** Returns the 256-byte XOR key from 512 hex characters, or null if the text is not valid. */
    public static byte[] cleanHex(String s) {
        if (s == null) return null;
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) if (!Character.isWhitespace(c)) sb.append(c);
        String h = sb.toString();
        if (h.length() != 512) return null;
        byte[] out = new byte[256];
        for (int i = 0; i < 256; i++) {
            int hi = Character.digit(h.charAt(2 * i), 16), lo = Character.digit(h.charAt(2 * i + 1), 16);
            if (hi < 0 || lo < 0) return null;
            out[i] = (byte) ((hi << 4) | lo);
        }
        return out;
    }

    private static Parsed parseIndex(byte[] index, byte[] xor) throws CoreException {
        for (int off : new int[]{0, HEADER_LEN}) {
            if (index.length >= off + 8 && (index[off] & 0xff) == 0xab && (index[off + 1] & 0xff) == 0xba) {
                byte[] body = Arrays.copyOfRange(index, off, index.length);
                for (int i = 4; i < body.length; i++) body[i] ^= xor[(i - 4) % xor.length];
                int num = (short) ((body[2] & 0xff) | (body[3] << 8));
                int c1 = (short) ((body[4] & 0xff) | (body[5] << 8));
                int c2 = (short) ((body[6] & 0xff) | (body[7] << 8));
                if (num == 1 && c1 > 0 && c2 > 0 && c1 + c2 + 8 == body.length) {
                    Parsed p = new Parsed();
                    p.header = Arrays.copyOfRange(index, 0, off);
                    p.iv = Arrays.copyOfRange(body, 8, 8 + c1);
                    p.key = Arrays.copyOfRange(body, 8 + c1, 8 + c1 + c2);
                    return p;
                }
            }
        }
        throw new CoreException("The 'index' file is not valid (or the key is wrong).");
    }

    private static byte[] aes(byte[] key, byte[] iv, byte[] data, boolean encrypt) throws CoreException {
        try {
            Cipher c = Cipher.getInstance("AES/CBC/NoPadding");
            c.init(encrypt ? Cipher.ENCRYPT_MODE : Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), new IvParameterSpec(iv));
            return c.doFinal(data);
        } catch (Exception e) {
            throw new CoreException("Crypto error: " + e.getMessage());
        }
    }

    private static boolean startsWith(byte[] a, byte[] prefix) {
        if (a.length < prefix.length) return false;
        for (int i = 0; i < prefix.length; i++) if (a[i] != prefix[i]) return false;
        return true;
    }

    public static String decrypt(byte[] save, byte[] index, byte[] xor) throws CoreException {
        Parsed p = parseIndex(index, xor);
        byte[] data = (p.header.length > 0 && startsWith(save, p.header)) ? Arrays.copyOfRange(save, p.header.length, save.length) : save;
        if (data.length == 0 || data.length % 16 != 0)
            throw new CoreException("The save file is not the expected size. Copy 'index' and the save again, at the same time.");
        byte[] raw = aes(p.key, p.iv, data, false);
        int pad = raw[raw.length - 1] & 0xff;
        if (pad < 1 || pad > 16) throw new CoreException("Decryption failed: 'index' and the save are not a matching pair, or the key is wrong.");
        for (int i = raw.length - pad; i < raw.length; i++)
            if ((raw[i] & 0xff) != pad) throw new CoreException("Decryption failed: 'index' and the save are not a matching pair, or the key is wrong.");
        String text = new String(raw, 0, raw.length - pad, StandardCharsets.UTF_8).replace("\u0000", "");
        return text;
    }

    public static byte[] encrypt(String text, byte[] index, byte[] xor) throws CoreException {
        Parsed p = parseIndex(index, xor);
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        for (int i = 0; i < text.length(); ) {
            int cp = text.codePointAt(i);
            i += Character.charCount(cp);
            byte[] b = new String(Character.toChars(cp)).getBytes(StandardCharsets.UTF_8);
            bo.write(b, 0, b.length);
            bo.write(0);
        }
        int n = 16 - (bo.size() % 16);
        for (int i = 0; i < n; i++) bo.write(n);
        byte[] enc = aes(p.key, p.iv, bo.toByteArray(), true);
        byte[] out = new byte[p.header.length + enc.length];
        System.arraycopy(p.header, 0, out, 0, p.header.length);
        System.arraycopy(enc, 0, out, p.header.length, enc.length);
        return out;
    }
}
