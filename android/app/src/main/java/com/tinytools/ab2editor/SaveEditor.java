package com.tinytools.ab2editor;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Random;

/** Edits the decrypted save text. Same rules as the PC editor in locked mode. */
public final class SaveEditor {
    public static final long MAX_CURRENCY = 999_999_999L;
    public static final int MAX_BIRD_LEVEL = 49;
    public static final int MAX_SPELLS = 20;
    public static final int MAX_CAMPAIGN = 3800;

    private static final int[] LEVEL_TOKENS = {0, 100, 350, 900, 1850, 3250, 4850, 6650, 8550, 10650, 12950, 15350,
            17950, 20850, 23950, 27250, 30750, 34450, 38350, 43350, 49350, 56350, 65350, 77350, 92350, 109350,
            127350, 146350, 169350, 199350, 234350, 274350, 324350, 374350, 424350, 474350, 524350, 574350,
            624350, 674350, 724350, 774350, 824350, 874350, 924350, 974350, 1024350, 1094350, 1124350, 1194350};
    private static final String[] CORE_BIRDS = {"RedBird", "BlueBird", "YellowBird", "BlackBird", "WhiteBird",
            "TerenceBird", "PurpleBird", "SilverBird", "MelodyBird"};
    private static final String[] SPELLS = {"MagicDuck", "Blizzard", "Chili"};

    /** A null field means "keep what the save already has". */
    public static class Request {
        public Long gems, secondary, freeTokens, express, entry, arena;
        public Integer campaign, birdLevel, spells;
    }

    private SaveEditor() {}

    private static JSONObject nested(JSONObject top, Map<String, JSONObject> cache, String key, boolean createIfMissing)
            throws JSONException {
        JSONObject c = cache.get(key);
        if (c != null) return c;
        if (!top.has(key)) {
            if (!createIfMissing) throw new JSONException("This save has no '" + key + "' part.");
            c = new JSONObject();
        } else {
            Object raw = top.get(key);
            c = (raw instanceof String) ? new JSONObject((String) raw) : (JSONObject) raw;
        }
        cache.put(key, c);
        return c;
    }

    private static void checkMoney(String label, Long v) {
        if (v != null && (v < 0 || v > MAX_CURRENCY))
            throw new IllegalArgumentException(label + " must be 0 to " + MAX_CURRENCY);
    }

    private static void upsertCard(JSONArray cards, String name, int level, int tokens) throws JSONException {
        for (int i = 0; i < cards.length(); i++) {
            JSONObject c = cards.getJSONObject(i);
            if (name.equals(c.optString("CardTemplateName"))) {
                c.put("Level", level);
                c.put("Tokens", tokens);
                if (!c.has("DeckNames")) c.put("DeckNames", new JSONArray().put("DefaultDeck"));
                return;
            }
        }
        JSONObject n = new JSONObject();
        n.put("CardTemplateName", name);
        n.put("Level", level);
        n.put("Tokens", tokens);
        n.put("DeckNames", new JSONArray().put("DefaultDeck"));
        cards.put(n);
    }

    public static String apply(String text, Request r) throws JSONException {
        checkMoney("Gems", r.gems); checkMoney("Secondary currency", r.secondary);
        checkMoney("Free bird tokens", r.freeTokens); checkMoney("Express tickets", r.express);
        checkMoney("Entry tickets", r.entry); checkMoney("Arena tickets", r.arena);
        if (r.campaign != null && (r.campaign < 1 || r.campaign > MAX_CAMPAIGN))
            throw new IllegalArgumentException("Campaign level must be 1 to " + MAX_CAMPAIGN);
        if (r.birdLevel != null && (r.birdLevel < 1 || r.birdLevel > MAX_BIRD_LEVEL))
            throw new IllegalArgumentException("Bird level must be 1 to " + MAX_BIRD_LEVEL);
        if (r.spells != null && (r.spells < 0 || r.spells > MAX_SPELLS))
            throw new IllegalArgumentException("Spells must be 0 to " + MAX_SPELLS);

        JSONObject top = new JSONObject(text);
        Map<String, JSONObject> cache = new LinkedHashMap<>();

        JSONObject wallet = nested(top, cache, "PD_Wallet", true);
        if (r.gems != null) wallet.put("Gems", r.gems.longValue());
        if (r.secondary != null) wallet.put("SecondaryCurrency", r.secondary.longValue());
        if (r.freeTokens != null) wallet.put("FreeBirdTokens", r.freeTokens.longValue());
        if (r.express != null) wallet.put("TOFExpressTickets", r.express.longValue());
        if (r.entry != null) wallet.put("TOFEntryTickets", r.entry.longValue());
        if (r.arena != null) wallet.put("ArenaTickets", r.arena.longValue());

        JSONObject prog = nested(top, cache, "PD_PlayerProgress", false);
        if (r.campaign != null) {
            for (String k : new String[]{"LastRunUnlocked", "LastLevelUnlocked", "LevelPlayerIsAt",
                    "TotalLevelCountDuringLastSession"}) prog.put(k, r.campaign.intValue());
        }

        if (r.birdLevel != null) {
            JSONObject coll = nested(top, cache, "PD_CardSpecCollection", true);
            if (!coll.has("CardSpecifications")) coll.put("CardSpecifications", new JSONArray());
            JSONArray cards = coll.getJSONArray("CardSpecifications");
            Random rnd = new Random();
            for (String b : CORE_BIRDS)
                upsertCard(cards, b, r.birdLevel, LEVEL_TOKENS[r.birdLevel] + rnd.nextInt(41));
        }

        if (r.spells != null) {
            JSONObject sc = nested(top, cache, "PD_NewSpellCollection", true);
            if (!sc.has("Spells")) sc.put("Spells", new JSONArray());
            JSONArray list = sc.getJSONArray("Spells");
            if (!prog.has("UnlockedSpells")) prog.put("UnlockedSpells", new JSONArray());
            JSONArray unlocked = prog.getJSONArray("UnlockedSpells");
            for (String name : SPELLS) {
                JSONObject found = null;
                for (int i = 0; i < list.length(); i++)
                    if (name.equals(list.getJSONObject(i).optString("Name"))) found = list.getJSONObject(i);
                if (found != null) found.put("Count", r.spells.intValue());
                else list.put(new JSONObject().put("Name", name).put("Count", r.spells.intValue())
                        .put("LastChangeUtc", "1970-01-01T00:00:00Z"));
                boolean has = false;
                for (int i = 0; i < unlocked.length(); i++) if (name.equals(unlocked.optString(i))) has = true;
                if (!has) unlocked.put(name);
            }
        }

        for (Map.Entry<String, JSONObject> e : cache.entrySet()) top.put(e.getKey(), e.getValue().toString());
        return top.toString();
    }

    /** Short human-readable summary of the values the app can change. */
    public static String summary(String text) {
        try {
            JSONObject top = new JSONObject(text);
            Map<String, JSONObject> cache = new LinkedHashMap<>();
            JSONObject w = nested(top, cache, "PD_Wallet", true);
            StringBuilder sb = new StringBuilder();
            sb.append("Gems: ").append(w.optLong("Gems", 0)).append('\n');
            sb.append("Feathers and coins: ").append(w.optLong("SecondaryCurrency", 0)).append('\n');
            sb.append("Bird tokens: ").append(w.optLong("FreeBirdTokens", 0)).append('\n');
            sb.append("Tickets (express / entry / arena): ").append(w.optLong("TOFExpressTickets", 0)).append(" / ")
                    .append(w.optLong("TOFEntryTickets", 0)).append(" / ").append(w.optLong("ArenaTickets", 0)).append('\n');
            if (top.has("PD_PlayerProgress")) {
                JSONObject p = nested(top, cache, "PD_PlayerProgress", false);
                sb.append("Campaign level: ").append(p.optInt("LevelPlayerIsAt", 0));
            }
            return sb.toString();
        } catch (JSONException e) {
            return "Could not read the save: " + e.getMessage();
        }
    }
}
