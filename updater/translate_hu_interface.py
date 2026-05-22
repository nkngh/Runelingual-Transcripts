"""
Applies Hungarian translations to transcript_hu_interface.xliff.
Uses: manual dict + pattern matching + Witcher 3 reference lookup as fallback.
Run: py translate_hu_interface.py
"""
import os, re, json
from lxml import etree

XLIFF_PATH = os.path.join(os.path.dirname(__file__), '..', 'draft', 'hu', 'transcript_hu_interface.xliff')
W3_PATH    = os.path.join(os.path.dirname(__file__), 'w3_hu_lookup.json')
NS = 'urn:oasis:names:tc:xliff:document:1.2'

with open(W3_PATH, encoding='utf-8') as f:
    W3 = json.load(f)

# ── Helpers ───────────────────────────────────────────────────────────────────

def w3(key):
    """Case-sensitive then case-insensitive W3 lookup."""
    if key in W3: return W3[key]
    kl = key.lower()
    return next((v for k, v in W3.items() if k.lower() == kl), None)

# ── Combat style component translations ──────────────────────────────────────
STYLE_PARTS = {
    "Defensive": "Védekező", "Aggressive": "Agresszív",
    "Accurate": "Pontos", "Controlled": "Irányított",
    "Longrange": "Hosszú hatótáv", "Rapid": "Gyors",
    "Light": "Könnyű", "Standard": "Normál", "Heavy": "Nehéz",
    "Stab": "Szúrás", "Slash": "Csapás", "Crush": "Zúzás",
    "Ranged": "Távolsági", "Magic": "Mágia",
    "Attack XP": "Támadás XP", "Strength XP": "Erő XP",
    "Defence XP": "Védelem XP", "Shared XP": "Megosztott XP",
    "Ranged XP": "Távolsági XP", "Magic XP": "Mágia XP",
    "Defence": "Védelem", "Attack": "Támadás", "Strength": "Erő",
}

def translate_combat_style(source):
    """Translates strings like '(Defensive) (Light) (Slash) (Attack XP)'."""
    parts = re.findall(r'\(([^)]+)\)', source)
    if not parts or len(parts) < 2:
        return None
    translated = [STYLE_PARTS.get(p, p) for p in parts]
    return ' '.join(f'({p})' for p in translated)

# ── Pattern translators ───────────────────────────────────────────────────────

def translate_members(source):
    """'Members: X' → 'Tagoknak: X'  (keeps X as-is)."""
    m = re.match(r'^Members: (.+)$', source)
    if not m: return None
    rest = m.group(1)
    inner = translate_any(rest) or rest
    return f"Tagoknak: {inner}"

def translate_smithing(source):
    """
    'X <Num0> bars'            → 'X – <Num0> rúd'
    'X <Num0> bar makes <Num1>'→ 'X – <Num0> rúdból <Num1> db'
    'X <Num0> bar, <Num1> Y'   → 'X – <Num0> rúd, <Num1> Y'
    """
    # bar makes N (bolts, arrowheads, etc.)
    m = re.match(r'^(.+?) <Num0> bars? makes <Num1>$', source)
    if m: return f"{m.group(1)} – <Num0> rúdból <Num1> db"
    # bar + extra material
    m = re.match(r'^(.+?) <Num0> bars?, <Num1> (.+)$', source)
    if m: return f"{m.group(1)} – <Num0> rúd, <Num1> {m.group(2)}"
    # plain bars
    m = re.match(r'^(.+?) <Num0> bars?$', source)
    if m: return f"{m.group(1)} – <Num0> rúd"
    return None

def translate_level_req(source):
    """
    'X (with <Num0> Skill)'              → 'X (<Num0> Skill szinttel)'
    'X (with <Num0> A and <Num1> B)'     → 'X (<Num0> A és <Num1> B szinttel)'
    'X (requires Quest)'                 → 'X (Quest szükséges)'
    'X (requires Quest and <Num0> Skill)'→ 'X (Quest és <Num0> Skill szükséges)'
    """
    # Members prefix + req - handled by Members translator calling us recursively
    m = re.match(r'^(.+?) \(with <Num0> (.+?) and <Num1> (.+?)\)$', source)
    if m:
        item = translate_any(m.group(1)) or m.group(1)
        return f"{item} (<Num0> {m.group(2)} és <Num1> {m.group(3)} szinttel)"
    m = re.match(r'^(.+?) \(with <Num0> (.+?)\)$', source)
    if m:
        item = translate_any(m.group(1)) or m.group(1)
        return f"{item} (<Num0> {m.group(2)} szinttel)"
    m = re.match(r'^(.+?) \(requires (.+?) and <Num0> (.+?)\)$', source)
    if m:
        item = translate_any(m.group(1)) or m.group(1)
        return f"{item} ({m.group(2)} és <Num0> {m.group(3)} szükséges)"
    m = re.match(r'^(.+?) \(requires (.+?)\)$', source)
    if m:
        item = translate_any(m.group(1)) or m.group(1)
        return f"{item} ({m.group(2)} szükséges)"
    return None

def translate_convert(source):
    """'Convert X' → 'X átalakítása'"""
    m = re.match(r'^Convert (.+)$', source)
    if m: return f"{m.group(1)} átalakítása"
    return None

def translate_weaponry_section(source):
    """'Weaponry - Members Only' → 'Felszerelés – Csak tagoknak'"""
    m = re.match(r'^(.+?) - Members Only$', source)
    if m: return f"{m.group(1)} – Csak tagoknak"
    return None

def translate_description(source):
    """'Description: <colNum0>text</col>' → 'Leírás: <colNum0>text</col>'"""
    m = re.match(r'^Description: (<colNum0>.+</col>)$', source, re.DOTALL)
    if m: return f"Leírás: {m.group(1)}"
    return None

def translate_rune_guide(source):
    """'<Num0> X runes per essence' → '<Num0> X rúna esszenciánként'"""
    m = re.match(r'^<Num0> (.+?) runes? per essence$', source)
    if m: return f"<Num0> {m.group(1)} rúna esszenciánként"
    return None

def translate_fletching_guide(source):
    """'<Num0> Arrow shafts (X logs)' → '<Num0> nyílvessző nyél (X rönk)'"""
    m = re.match(r'^<Num0> Arrow shafts \((.+?) [Ll]ogs?\)$', source)
    if m: return f"<Num0> nyílvessző nyél ({m.group(1)} rönk)"
    m = re.match(r'^<Num0> Arrow shafts \((.+?)\)$', source)
    if m: return f"<Num0> nyílvessző nyél ({m.group(1)})"
    return None

def translate_guide_step(source):
    """'<Num0>. Do something.' → '<Num0>. Do something.' (translates the text part)"""
    m = re.match(r'^(<Num0>\.) (.+)$', source)
    if not m: return None
    text = m.group(2)
    translated = translate_any(text) or text
    return f"{m.group(1)} {translated}"

def translate_skill_total(source):
    """'<Num0> skill total' etc."""
    patterns = [
        (r'^<Num0> skill totals?$', '<Num0> összes szint'),
        (r'^<Num0> skill t\.\.\.$', '<Num0> össz...'),
        (r'^<Num0> skill to\.\.\.$', '<Num0> össz...'),
        (r'^<Num0>v<Num1> Duels$', '<Num0>v<Num1> Párbaj'),
        (r'^<Num0>v<Num1> Tournament$', '<Num0>v<Num1> Torna'),
        (r'^<Num0>th Realm$', '<Num0>. Birodalmi szint'),
    ]
    for pattern, result in patterns:
        if re.match(pattern, source):
            return result
    return None

def translate_spell_level(source):
    """'Level <Num0>: Wind Blast' → '<Num0>. szint: Wind Blast'"""
    m = re.match(r'^Level <Num0>: (.+)$', source)
    if m: return f"<Num0>. szint: {m.group(1)}"
    return None

def translate_prayer_tooltip(source):
    """
    'Level <Num0><br>PrayerName<br>Description.<br>(Drain: <Num1>pt per <Num2>s)'
    → 'Szint: <Num0><br>PrayerName<br>Description.<br>(Fogyás: <Num1> pont / <Num2>s)'
    """
    if '<br>' not in source: return None
    # Replace structural English parts
    result = source
    result = result.replace('Level <Num0><br>', 'Szint: <Num0><br>', 1)
    # Drain pattern at end
    result = re.sub(r'\(Drain: (<Num\d+>)pt per (<Num\d+>)s\)',
                    r'(Fogyás: \1 pont / \2 mp)', result)
    # Common description phrases
    result = result.replace('Increases your attack by', 'Támadásodat')
    result = result.replace('Increases your strength by', 'Erődet')
    result = result.replace('Increases your defence by', 'Védelmedet')
    result = result.replace('Increases your Ranging by', 'Távolsági támadásodat')
    result = result.replace('Increases your magical attack and defence by', 'Varázslatos támadásodat és védelmedet')
    result = result.replace('also increases your magic strength by', ', varázslataid erejét')
    result = result.replace('and your defence by', 'és védelmedet')
    result = result.replace('Boosted stats last', 'A felturbózott statisztikák')
    result = result.replace('% longer.', '%-kal tovább tartanak.')
    result = result.replace('Protection from magical attacks.', 'Védelmet nyújt varázslatos támadások ellen.')
    result = result.replace('Protection from missile attacks.', 'Védelmet nyújt lövedékes támadások ellen.')
    result = result.replace('Protection from melee attacks.', 'Védelmet nyújt közelharcas támadások ellen.')
    result = result.replace('Keep <Num1> extra item if you die.',
                            '<Num1> extra tárgyat megtarthatsz halálod esetén.')
    result = result.replace('% increase to attack.', '%-kal növeli.')
    result = result.replace('%.', '%.')
    if result != source:
        return result
    return None

def translate_col_header(source):
    """'<colNum0>Skill:</col>' → '<colNum0>HuSkill:</col>'"""
    m = re.match(r'^(<colNum\d+>)(.+?):(</col>)$', source)
    if not m: return None
    tag_open, label, tag_close = m.groups()
    hu_label = translate_any(label) or label
    return f"{tag_open}{hu_label}:{tag_close}"

def translate_col_label(source):
    """'<colNum0>SomeLabel</col>' → '<colNum0>HuLabel</col>'"""
    m = re.match(r'^(<colNum\d+>)(.+?)(</col>)$', source)
    if not m: return None
    tag_open, label, tag_close = m.groups()
    hu_label = translate_any(label) or label
    if hu_label != label:
        return f"{tag_open}{hu_label}{tag_close}"
    return None

def translate_reward_template(source):
    """Common combAchvmt reward string patterns."""
    patterns = [
        (r'^<Num0>% bonus to tokens earned from <colNum0>(.+?)</col> activities$',
         lambda m: f"<Num0>% bónusz a <colNum0>{m.group(1)}</col> tevékenységekből szerzett zsetonokhoz"),
        (r'^<Num0> additional commendation points? from successful <colNum0>(.+?)</col> games?$',
         lambda m: f"<Num0> extra ajánlópont sikeres <colNum0>{m.group(1)}</col> játékokból"),
        (r'^<Num0>k XP lamp \(minimum skill requirement: <Num1>\)$',
         lambda m: "<Num0>k XP lámpa (minimum szintkövetelmény: <Num1>)"),
        (r'^<colNum0>Level:</col><colNum1> <Num0></col>$',
         lambda m: "<colNum0>Szint:</col><colNum1> <Num0></col>"),
        (r'^<colNum0>Level:</col><colNum1> N/A</col>$',
         lambda m: "<colNum0>Szint:</col><colNum1> N/A</col>"),
        (r"^<colNum0>Ghommal's hilt <Num0></col>$",
         lambda m: f"<colNum0>Ghommal csípője <Num0></col>"),
        (r'^<Num0>, <Num1>, <Num2> - Mage$',
         lambda m: "<Num0>, <Num1>, <Num2> – Mágus"),
        (r'^<Num0>, <Num1>, <Num2> - Range$',
         lambda m: "<Num0>, <Num1>, <Num2> – Távolsági"),
    ]
    for pattern, builder in patterns:
        m = re.match(pattern, source)
        if m:
            return builder(m)
    return None


# ── Main translation dictionary ───────────────────────────────────────────────
TRANSLATIONS = {
    # ── chatButtons ───────────────────────────────────────────────────────────
    "All":          "Minden",
    "Game ":        "Játék ",
    "Public ":      "Nyilvános ",
    "Private ":     "Privát ",
    " On":          " Be",
    "Channel ":     "Csatorna ",
    "Clan ":        "Klán ",
    "Trade ":       "Kereskedés ",
    "Group ":       "Csoport ",
    " <colNum0>Autochat</col>":  " <colNum0>Automatikus chat</col>",
    " <colNum0>Friends</col>":   " <colNum0>Barátok</col>",
    " <colNum0>Filtered</col>":  " <colNum0>Szűrt</col>",
    " <colNum0>Hide</col>":      " <colNum0>Elrejtés</col>",
    " <colNum0>Off</col>":       " <colNum0>Ki</col>",

    # ── loginScreen ───────────────────────────────────────────────────────────
    "Welcome to Old School RuneScape":
        "Üdvözlünk az Old School RuneScape-ben",
    "You last logged in a minute ago.":
        "Utoljára egy perce voltál bejelentkezve.",
    "You last logged in <Num0> minutes ago.":
        "Utoljára <Num0> perccel ezelőtt voltál bejelentkezve.",
    "You last logged in <Num0> hours ago.":
        "Utoljára <Num0> órával ezelőtt voltál bejelentkezve.",
    "You last logged in <Num0> hours, <Num1> minutes ago.":
        "Utoljára <Num0> órával és <Num1> perccel ezelőtt voltál bejelentkezve.",
    "You last logged in <Num0> days ago.":
        "Utoljára <Num0> nappal ezelőtt voltál bejelentkezve.",
    "You last logged in <Num0> days, <Num1> hours ago.":
        "Utoljára <Num0> nappal és <Num1> órával ezelőtt voltál bejelentkezve.",
    "You last logged in <Num0> days, <Num1> minutes ago.":
        "Utoljára <Num0> nappal és <Num1> perccel ezelőtt voltál bejelentkezve.",
    "You last logged in <Num0> days, <Num1> hours, <Num2> minutes ago.":
        "Utoljára <Num0> nappal, <Num1> órával és <Num2> perccel ezelőtt voltál bejelentkezve.",
    "You have <colNum0><Num0></col> days of membership left.":
        "Még <colNum0><Num0></col> napod van tagságodból.",
    "You have <colNum0><Num0></col> day of membership left.":
        "Még <colNum0><Num0></col> napod van tagságodból.",
    "You are not a member. Subscribe to access extra skills, areas, quests, and more.":
        "Nem vagy tag. Iratkozz fel, hogy hozzáférhess extra készségekhez, területekhez, küldetésekhez és egyebekhez.",
    "You have <Num0> unread messages in your inbox.":
        "<Num0> olvasatlan üzeneted van a postaládádban.",
    "CLICK HERE TO PLAY":
        "KATTINTS IDE A JÁTÉKHOZ",

    # ── mainTabs: friends / ignore / account ──────────────────────────────────
    "Friends - W<Num0> (<Num1>/<Num2>)":    "Barátok – W<Num0> (<Num1>/<Num2>)",
    "<colNum0>World <Num0>":                "<colNum0>Világ <Num0>",
    "World <Num0>":                         "Világ <Num0>",
    "Offline":                              "Offline",
    "Del Friend":                           "Barát törlése",
    "Ignores - W<Num0> (<Num1>/<Num2>)":    "Tiltólista – W<Num0> (<Num1>/<Num2>)",
    "Add Name":                             "Név hozzáadása",
    "Del Name":                             "Név törlése",
    "Add Friend":                           "Barát hozzáadása",
    "You may ignore users by using the button below, or by right-clicking on a message from them and selecting to add them to your ignore list.":
        "A lenti gombbal, vagy az üzenetükre jobb gombbal kattintva és a tiltólistára adás lehetőséget választva tudod figyelmen kívül hagyni a felhasználókat.",
    "You may add friends by using the button below, or by right-clicking on a message from them and selecting to add them as a friend.":
        "A lenti gombbal, vagy az üzenetükre jobb gombbal kattintva és a barátként való hozzáadás lehetőséget választva tudsz barátokat hozzáadni.",
    "Account":                              "Fiók",
    "Membership: <Num0> days left":         "Tagság: még <Num0> nap",
    "Open Store":                           "Bolt megnyitása",
    "Inbox: <Num0> unread messages":        "Beérkező: <Num0> olvasatlan üzenet",
    "View Inbox":                           "Beérkező megtekintése",
    "Name Changer":                         "Névváltás",
    "Membership: <colNum0>None</col>":      "Tagság: <colNum0>Nincs</col>",
    "Upgrade Now":                          "Frissítés most",
    "View Benefits":                        "Előnyök megtekintése",
    "Community":                            "Közösség",
    "Current Poll: <colNum0>Inactive</col>":"Aktuális szavazás: <colNum0>Inaktív</col>",
    "View Poll":                            "Szavazás megtekintése",
    "View History":                         "Előzmények megtekintése",
    "View Stats":                           "Statisztikák megtekintése",
    "View another clan":                    "Másik klán megtekintése",
    "Clan Settings":                        "Klán beállítások",
    "Clan Members":                         "Klán tagok",
    "Guest Clan":                           "Vendég klán",
    "Recruit":                              "Újonc",
    "Corporal":                             "Szakaszvezető",
    "Sergeant":                             "Őrmester",
    "Lieutenant":                           "Hadnagy",
    "Captain":                              "Kapitány",
    "General":                              "Tábornok",
    "Owner":                                "Tulajdonos",
    "Deputy Owner":                         "Helyettes tulajdonos",
    "Organiser":                            "Szervező",
    "Coordinator":                          "Koordinátor",
    "Overseer":                             "Felügyelő",
    "Deputy Owner (Unranked)":              "Helyettes tulajdonos (Rangon kívül)",
    "No Clan":                              "Nincs klán",
    "Join Clan":                            "Klánhoz csatlakozás",
    "Leave Clan":                           "Klán elhagyása",
    "Clan Chat":                            "Klán chat",
    "Friends Chat":                         "Barát chat",
    "Group Ironman":                        "Csoport Ironman",

    # ── mainTabs: world switcher ───────────────────────────────────────────────
    "Switch World":                         "Világ váltása",
    "Current World: <Num0>":               "Jelenlegi világ: <Num0>",
    "Free worlds":                          "Ingyenes világok",
    "Members worlds":                       "Tagok világa",
    "All worlds":                           "Minden világ",
    "PvP worlds":                           "PvP világok",
    "Skill total":                          "Összes szint",
    "High risk":                            "Magas kockázat",
    "Bounty Hunter":                        "Fejvadász",
    "Deadman":                              "Deadman",
    "Tournament":                           "Torna",
    "Last Man Standing":                    "Az utolsó megálló",
    "Fresh Start Worlds":                   "Kezdő világok",
    "Seasonal":                             "Szezonális",

    # ── mainTabs: combat options (non-pattern) ────────────────────────────────
    "Combat Options":                       "Harci lehetőségek",
    "Combat Style":                         "Harci stílus",
    "Attack Style":                         "Támadási stílus",
    "Weapon":                               "Fegyver",
    "Unarmed":                              "Fegyvertelen",
    "Auto retaliate":                       "Automatikus visszaütés",
    "XP":                                   "XP",

    # ── combAchvmt ────────────────────────────────────────────────────────────
    "Combat Achievements - Overview":       "Harci teljesítmények – Áttekintő",
    "Combat Achievements - Tasks":          "Harci teljesítmények – Feladatok",
    "Combat Achievements - Bosses":         "Harci teljesítmények – Főellenségek",
    "Combat Achievements - Rewards":        "Harci teljesítmények – Jutalmak",
    "Total Points: <Num0> - Next unlock in <Num1> points":
        "Összes pont: <Num0> – Következő feloldás: <Num1> pont múlva",
    "Difficulty Tiers":                     "Nehézségi szintek",
    "Combat Profile - <!PLAYER_NAME0>":     "Harci profil – <!PLAYER_NAME0>",
    "Easy":                                 "Könnyű",
    "Medium":                               "Közepes",
    "Hard":                                 "Nehéz",
    "Elite":                                "Elit",
    "Master":                               "Mester",
    "Grandmaster":                          "Nagymester",
    "Tasks Completed:":                     "Befejezett feladatok:",
    "Boss Kill Count:":                     "Főellenség ölések száma:",
    "Skilling Boss Kill Count:":            "Készség főellenség ölések száma:",
    "Raid Completions:":                    "Befejezett raidek:",
    "Top Boss:":                            "Legtöbb ölés:",
    "Top Skilling Boss:":                   "Legtöbb készség főellenség ölés:",
    "Top Raid:":                            "Legtöbb befejezett raid:",
    "<!ANY_TRANSLATED0> (<Num0>)":          "<!ANY_TRANSLATED0> (<Num0>)",
    "Nothing!":                             "Semmi!",
    "Overview":                             "Áttekintő",
    "Tasks":                                "Feladatok",
    "Bosses":                               "Főellenségek",
    "Rewards":                              "Jutalmak",
    "There are no tasks available to you that match your filters.":
        "Nincs a szűrőidnek megfelelő elérhető feladat.",
    "Points:":                              "Pontok:",
    "Tier Completed":                       "Szint teljesítve",
    "Tier Reward:":                         "Szint jutalom:",
    "Kill Count:":                          "Ölésszám:",
    "Personal Best:":                       "Személyes rekord:",
    "Not yet attempted":                    "Még nem próbálva",
    "Not completed":                        "Nem befejezett",
    "Completed":                            "Teljesített",
    "In Progress":                          "Folyamatban",
    "Locked":                               "Zárolt",
    "All":                                  "Mind",
    "Easy tasks":                           "Könnyű feladatok",
    "Medium tasks":                         "Közepes feladatok",
    "Hard tasks":                           "Nehéz feladatok",
    "Elite tasks":                          "Elit feladatok",
    "Master tasks":                         "Mester feladatok",
    "Grandmaster tasks":                    "Nagymester feladatok",
    "Show Completed":                       "Befejezettek mutatása",
    "Show Incomplete":                      "Befejezetlen feladatok mutatása",
    "Show All":                             "Összes mutatása",

    # ── generalUI: equipment guide ────────────────────────────────────────────
    "Attack":       "Támadás",
    "Weapons":      "Fegyverek",
    "Defence":      "Védelem",
    "Ranged":       "Távolsági",
    "Magic":        "Mágia",
    "Prayer":       "Ima",
    "Strength":     "Erő",
    "Hitpoints":    "Életerő",
    "Agility":      "Mozgékonyság",
    "Herblore":     "Gyógynövény",
    "Thieving":     "Lopás",
    "Crafting":     "Tárgy készítés",
    "Fletching":    "Nyílkészítés",
    "Slayer":       "Slayer",
    "Hunter":       "Vadászat",
    "Mining":       "Bányászat",
    "Smithing":     "Kovácsolás",
    "Fishing":      "Halászat",
    "Cooking":      "Főzés",
    "Firemaking":   "Tűzgyújtás",
    "Woodcutting":  "Favágás",
    "Runecraft":    "Rúnakészítés",
    "Construction": "Építészet",
    "Farming":      "Gazdálkodás",
    "Armour":       "Páncél",
    "Melee":        "Közelharc",
    "All styles":   "Minden stílus",
    "Weaponry - Members Only":              "Felszerelés – Csak tagoknak",
    "Members":                              "Tagok",
    "Members Only":                         "Csak tagoknak",
    "Free to play":                         "Ingyenes",
    "Free to play only":                    "Csak ingyenes játékosoknak",

    # ── generalUI: smithing section headers ───────────────────────────────────
    "Smelting":     "Olvasztás",
    "Smithing":     "Kovácsolás",
    "Smithing guide":               "Kovácsolási útmutató",
    "Smelting guide":               "Olvasztási útmutató",
    "Bars":                         "Rudak",
    "Bolts":                        "Lövedékek",
    "Cannonballs":                  "Ágyúgolyók",

    # ── generalUI: construction ───────────────────────────────────────────────
    "House Options":                "Ház beállítások",
    "Viewer":                       "Néző",
    "On":                           "Be",
    "Off":                          "Ki",
    "Building Mode":                "Építési mód",
    "Teleport Inside":              "Teleportálás belülre",
    "Default Building Mode":        "Alapértelmezett építési mód",
    "Doors":                        "Ajtók",
    "Expel Guests":                 "Vendégek elküldése",
    "Leave House":                  "Ház elhagyása",
    "Call Servant":                 "Szolga hívása",
    "Number of rooms: <Num0>":      "Szobák száma: <Num0>",
    "Toggle Building mode on and off, allowing construction within your house.":
        "Az építési mód be- és kikapcsolása, hogy a házadon belül építkezhess.",
    "Toggle teleport location inside (on) or outside (off) of the house.":
        "A teleport helyszín váltása a ház belsejébe (be) vagy kívülre (ki).",
    "Toggle Building mode by default when teleport inside the house.":
        "Az építési mód alapértelmezett bekapcsolása, amikor a házba teleportálsz.",
    "Render house doors as initially closed.":      "A ház ajtóit kezdetben zárva jeleníti meg.",
    "Render house doors as initially open.":        "A ház ajtóit kezdetben nyitva jeleníti meg.",
    "Do not render doors.":                         "Az ajtók megjelenítésének kikapcsolása.",

    # ── generalUI: skill guide text ───────────────────────────────────────────
    "Each animal you can hunt will typically be found in a specfic locale, and will require different gear. Make sure you come prepared!":
        "Minden vadászható állat általában egy meghatározott helyen található, és különböző felszerelést igényel. Győződj meg róla, hogy felkészülten érkezel!",
    "As your Hunter level improves, not only will you be able to hunt a wider variety of creatures, but you'll also be able to maintain more traps simultaneously, and they will successfully trap creatures more often.":
        "Ahogy a Vadászat szinted növekszik, nemcsak több fajta lényt tudsz majd vadászni, hanem egyszerre több csapdát is fenntarthatsz, és azok sikeresebben fogják be a lényeket.",

    # ── generalUI: common labels ──────────────────────────────────────────────
    "Level":        "Szint",
    "Levels":       "Szintek",
    "Experience":   "Tapasztalat",
    "XP":           "XP",
    "Total":        "Összesen",
    "Total level":  "Összes szint",
    "Points":       "Pontok",
    "Score":        "Pontszám",
    "Rank":         "Rang",
    "None":         "Nincs",
    "Unknown":      "Ismeretlen",
    "N/A":          "N/A",
    "Yes":          "Igen",
    "No":           "Nem",
    "OK":           "OK",
    "Cancel":       "Mégsem",
    "Close":        "Bezár",
    "Back":         "Vissza",
    "Next":         "Következő",
    "Previous":     "Előző",
    "Continue":     "Folytatás",
    "Confirm":      "Megerősítés",
    "Accept":       "Elfogadás",
    "Decline":      "Visszautasítás",
    "Apply":        "Alkalmaz",
    "Reset":        "Visszaállítás",
    "Default":      "Alapértelmezett",
    "Enable":       "Engedélyezés",
    "Disable":      "Letiltás",
    "Show":         "Megjelenítés",
    "Hide":         "Elrejtés",
    "Filter":       "Szűrő",
    "Sort":         "Rendezés",
    "Search":       "Keresés",
    "Loading":      "Betöltés",
    "Saving":       "Mentés",
    "Error":        "Hiba",
    "Warning":      "Figyelmeztetés",
    "Info":         "Információ",
    "Settings":     "Beállítások",
    "Options":      "Lehetőségek",
    "Controls":     "Vezérlés",
    "Help":         "Segítség",
    "Tutorial":     "Oktatóanyag",
    "Note":         "Feljegyzés",
    "Message":      "Üzenet",
    "Locked":       "Zárolva",
    "Unlocked":     "Feloldva",
    "Unlock":       "Feloldás",
    "Completed":    "Teljesítve",
    "Incomplete":   "Befejezetlen",
    "Active":       "Aktív",
    "Inactive":     "Inaktív",
    "Available":    "Elérhető",
    "Unavailable":  "Nem elérhető",
    "Required":     "Szükséges",
    "Optional":     "Választható",
    "Reward":       "Jutalom",
    "Rewards":      "Jutalmak",
    "Equip":        "Felszerelés",
    "Equipped":     "Használatban",
    "Unequip":      "Levetés",
    "Inventory":    "Felszerelés",
    "Equipment":    "Felszerelés",
    "Stats":        "Statisztikák",
    "Bonuses":      "Bónuszok",
    "Weight":       "Súly",
    "Value":        "Érték",
    "Quantity":     "Mennyiség",
    "Stack":        "Köteg",
    "Noted":        "Cédulázott",
    "Trade":        "Kereskedés",
    "Buy":          "Vásárlás",
    "Sell":         "Eladás",
    "Price":        "Ár",
    "Profit":       "Nyereség",
    "Loss":         "Veszteség",
    "Offer":        "Ajánlat",
    "Collect":      "Gyűjtés",
    "Deposit":      "Betét",
    "Withdraw":     "Kivétel",
    "Bank":         "Bank",
    "Chest":        "Láda",
    "Key":          "Kulcs",
    "Quest":        "Küldetés",
    "Quests":       "Küldetések",
    "Diary":        "Napló",
    "Achievement":  "Teljesítmény",
    "Achievements": "Teljesítmények",
    "Task":         "Feladat",
    "Objective":    "Cél",
    "Kill":         "Ölés",
    "Death":        "Halál",
    "Respawn":      "Újraélesztés",
    "Health":       "Egészség",
    "Max":          "Max",
    "Min":          "Min",
    "Current":      "Jelenlegi",
    "Remaining":    "Fennmaradó",
    "Map":          "Térkép",
    "Area":         "Terület",
    "World":        "Világ",
    "Server":       "Szerver",
    "Player":       "Játékos",
    "Players":      "Játékosok",
    "Online":       "Online",
    "Offline":      "Offline",
    "Friends":      "Barátok",
    "Ignore":       "Tiltólista",
    "Clan":         "Klán",
    "Group":        "Csoport",
    "Chat":         "Chat",
    "Public":       "Nyilvános",
    "Private":      "Privát",
    "Channel":      "Csatorna",
    "Mute":         "Némítás",
    "Unmute":       "Hang visszaállítása",
    "Report":       "Jelentés",
    "Block":        "Blokkolás",
    "Unblock":      "Blokkolás feloldása",

    # ── generalUI: membership ─────────────────────────────────────────────────
    "Member":                               "Tag",
    "Membership":                           "Tagság",
    "Subscribe":                            "Feliratkozás",
    "Subscription":                         "Előfizetés",
    "Members only":                         "Csak tagoknak",
    "Members area":                         "Tagok területe",

    # ── generalUI: misc UI ────────────────────────────────────────────────────
    "Examine":      "Vizsgálat",
    "Drop":         "Eldobás",
    "Use":          "Használat",
    "Take":         "Felvétel",
    "Wear":         "Felöltés",
    "Wield":        "Forgatás",
    "Eat":          "Evés",
    "Drink":        "Ivás",
    "Read":         "Olvasás",
    "Open":         "Megnyitás",
    "Walk here":    "Séta ide",
    "Loot":         "Zsákmányolás",
    "Prayer":       "Ima",
    "Spellbook":    "Varázskönyv",
    "Magic":        "Mágia",
    "Emotes":       "Emóciók",
    "Music":        "Zene",
    "Logout":       "Kijelentkezés",
    "Main Menu":    "Főmenü",
    "New Game":     "Új játék",

    # ── generalUI: STASH / Mahogany Homes / Achievement Diary ────────────────
    "Mahogany Homes (beginner)":    "Mahagóni Otthon (kezdő)",
    "Mahogany Homes (novice)":      "Mahagóni Otthon (újonc)",
    "Mahogany Homes (adept)":       "Mahagóni Otthon (haladó)",
    "Mahogany Homes (expert)":      "Mahagóni Otthon (szakértő)",
    "Mahogany Homes (master)":      "Mahagóni Otthon (mester)",
    "STASH units (beginner)":       "STASH egységek (kezdő)",
    "STASH units (novice)":         "STASH egységek (újonc)",
    "STASH units (adept)":          "STASH egységek (haladó)",
    "STASH units (expert)":         "STASH egységek (szakértő)",
    "STASH units (master)":         "STASH egységek (mester)",
    "Small storage unit":           "Kis tárolóegység",
    "Medium storage unit":          "Közepes tárolóegység",
    "Large storage unit":           "Nagy tárolóegység",
    "Massive storage unit":         "Hatalmas tárolóegység",

    # ── mainTabs: col-wrapped labels ──────────────────────────────────────────
    "<colNum0>Chat-channel</col>":  "<colNum0>Chat csatorna</col>",
    "<colNum0>Chat</col>":          "<colNum0>Chat</col>",
    "<colNum0>Discard</col>":       "<colNum0>Elvetés</col>",
    "<colNum0>Fetching data...</col>": "<colNum0>Adatok betöltése...</col>",
    "<colNum0>Find</col>":          "<colNum0>Keresés</col>",
    "<colNum0>Join</col>":          "<colNum0>Csatlakozás</col>",
    "<colNum0>Leave</col>":         "<colNum0>Elhagyás</col>",
    "<colNum0>Loading...</col>":    "<colNum0>Betöltés...</col>",
    "<colNum0>No current clan</col>":   "<colNum0>Nincs jelenlegi klán</col>",
    "<colNum0>Not in channel</col>":    "<colNum0>Nincs csatornán</col>",
    "<colNum0>Sign up</col>":       "<colNum0>Regisztráció</col>",
    "<colNum0>Sign up</col> to be invited to fights.":
        "<colNum0>Regisztrálj</col>, hogy meghívhassanak harcokba.",
    "<img=1> Official Group":       "<img=1> Hivatalos csoport",
    "(none)":                       "(nincs)",
    "<Num0>B/<Num1>":               "<Num0>B/<Num1>",
    "<Num0>K/<Num1>":               "<Num0>K/<Num1>",
    "<Num0>M<Num1>":                "<Num0>M<Num1>",
    "<colNum0><colNum1>Connecting...</col></col>": "<colNum0><colNum1>Csatlakozás...</col></col>",

    # ── mainTabs: spell tooltip single-line ────────────────────────────────────
    "A high level Air missile<br><colNum0>Members Only</col>":
        "Magas szintű levegő lövedék<br><colNum0>Csak tagoknak</col>",
    "A high level Earth missile<br><colNum0>Members Only</col>":
        "Magas szintű föld lövedék<br><colNum0>Csak tagoknak</col>",
    "A high level Fire missile<br><colNum0>Members Only</col>":
        "Magas szintű tűz lövedék<br><colNum0>Csak tagoknak</col>",
    "A high level Water missile<br><colNum0>Members Only</col>":
        "Magas szintű víz lövedék<br><colNum0>Csak tagoknak</col>",
    "A very high level Air missile<br><colNum0>Members Only</col>":
        "Nagyon magas szintű levegő lövedék<br><colNum0>Csak tagoknak</col>",
    "A very high level Earth missile<br><colNum0>Members Only</col>":
        "Nagyon magas szintű föld lövedék<br><colNum0>Csak tagoknak</col>",
    "A very high level Fire missile<br><colNum0>Members Only</col>":
        "Nagyon magas szintű tűz lövedék<br><colNum0>Csak tagoknak</col>",
    "A very high level Water missile<br><colNum0>Members Only</col>":
        "Nagyon magas szintű víz lövedék<br><colNum0>Csak tagoknak</col>",
    "A magic dart of slaying<br><colNum0>Members Only</col>":
        "Varázsló lövedék ölésre<br><colNum0>Csak tagoknak</col>",

    # ── combAchvmt: extra patterns ────────────────────────────────────────────
    "Combat Achievements - <!NPC_NAME0>":   "Harci teljesítmények – <!NPC_NAME0>",
    "Combat Level: <colNum0><Num0></col>":  "Harci szint: <colNum0><Num0></col>",
    "Combat Level: <colNum0>N/A</col>":     "Harci szint: <colNum0>N/A</col>",
    "Kill Count: <colNum0><Num0></col>":    "Ölésszám: <colNum0><Num0></col>",
    "Daily Mor Ul Rek teleports - <Num0>":  "Napi Mor Ul Rek teleportok – <Num0>",
    "Daily Trollheim teleports - <Num0>":   "Napi Trollheim teleportok – <Num0>",
    "Access to <colNum0>Ghommal's lucky penny</col>":
        "Hozzáférés: <colNum0>Ghommal szerencsés érméje</col>",
    "Item imbue rewards at <colNum0>Soul Wars</col> and the <colNum1>Nightmare Zone</col> are <Num0>% cheaper":
        "A <colNum0>Soul Wars</col> és a <colNum1>Nightmare Zone</colNum1> tárgy-feltöltési jutalmak <Num0>%-kal olcsóbbak",
    "Immunity from the prayer draining effect at <colNum0>Barrows</col> when one of <colNum1>Ghommal's hilts</col> is equipped":
        "Immunis vagy az ima-fogyasztó hatástól a <colNum0>Barrows</col>-ban, ha <colNum1>Ghommal markolata</col> van felszerelve",

    # ── loginScreen: news post (keep in English — changes with updates) ────────
    "It's been some time coming but this weeks update contains almost all of the QoL changes as proposed in <colNum0>Poll <Num0></col>! With a variety of changes, please check out the <colNum1>update post</col> for all the latest info!":
        "Egy ideje várt már rá, de a héten megjelenő frissítés szinte az összes életminőség-módosítást tartalmazza, amelyeket a <colNum0>Szavazás <Num0></col> javasolt! A változtatásokról az <colNum1>update posztban</colNum1> olvashatsz.",

    # ── generalUI: Grand Exchange ─────────────────────────────────────────────
    "Grand Exchange":               "Grand Exchange",
    "Offer":                        "Ajánlat",
    "Buy offer":                    "Vételi ajánlat",
    "Sell offer":                   "Eladási ajánlat",
    "Guide price":                  "Irányár",
    "Limit":                        "Limit",
    "Aborted":                      "Megszakítva",
    "Finished":                     "Befejezett",
    "Empty":                        "Üres",

    # ── generalUI: skill guide common phrases ─────────────────────────────────
    "What can I do with my <Num0> <col=ffffff><!ANY_TRANSLATED0></col>?":
        "Mit tehetek a <Num0> szintű <col=ffffff><!ANY_TRANSLATED0></col> készségemmel?",
    "Recommended equipment:":       "Ajánlott felszerelés:",
    "Recommended items:":           "Ajánlott tárgyak:",
    "Note:":                        "Megjegyzés:",
    "Tip:":                         "Tipp:",
    "Warning:":                     "Figyelmeztetés:",
    "Required items:":              "Szükséges tárgyak:",
    "Required level:":              "Szükséges szint:",
    "Experience per action:":       "Tapasztalat műveltenként:",
    "Experience per hour:":         "Tapasztalat óránként:",
    "Profit per hour:":             "Nyereség óránként:",
    "Profit per item:":             "Nyereség tárgyonként:",
}


def translate_any(source, subcat=""):
    """Try all translation strategies in order, return first match."""
    # 1. Exact dict match
    if source in TRANSLATIONS:
        return TRANSLATIONS[source]

    # 2. W3 exact match
    w3_result = w3(source)
    if w3_result:
        return w3_result

    # 3. Pattern: Members prefix
    result = translate_members(source)
    if result: return result

    # 4. Pattern: level/quest requirements
    result = translate_level_req(source)
    if result: return result

    # 5. Pattern: smithing (bars)
    result = translate_smithing(source)
    if result: return result

    # 6. Pattern: combat style XP combos
    result = translate_combat_style(source)
    if result: return result

    # 7. Pattern: "Convert X"
    result = translate_convert(source)
    if result: return result

    # 8. Pattern: "X - Members Only"
    result = translate_weaponry_section(source)
    if result: return result

    # 9. combAchvmt: Description prefix
    result = translate_description(source)
    if result: return result

    # 10. combAchvmt: reward templates
    result = translate_reward_template(source)
    if result: return result

    # 11. generalUI: runecrafting guide
    result = translate_rune_guide(source)
    if result: return result

    # 12. generalUI: fletching guide
    result = translate_fletching_guide(source)
    if result: return result

    # 13. generalUI: numbered guide steps
    result = translate_guide_step(source)
    if result: return result

    # 14. mainTabs: skill total / world switcher variants
    result = translate_skill_total(source)
    if result: return result

    # 15. mainTabs: magic spell level
    result = translate_spell_level(source)
    if result: return result

    # 16. mainTabs: prayer tooltips
    result = translate_prayer_tooltip(source)
    if result: return result

    # 17. Tagged column header "Label:"
    result = translate_col_header(source)
    if result: return result

    # 18. Tagged label "<colNum0>X</col>"
    result = translate_col_label(source)
    if result: return result

    # 19. Food restore pattern: "X: Restores <Num0> Hitpoints (Members)"
    m = re.match(r'^(.+?): Restores? <Num0> Hitpoints?(?: \(Members\))?$', source)
    if m: return f"{m.group(1)}: <Num0> életerőt állít vissza"
    m = re.match(r'^(.+?): Restores? <Num0> Hitpoints? \(Members\)$', source)
    if m: return f"{m.group(1)}: <Num0> életerőt állít vissza (tagoknak)"
    m = re.match(r'^(.+?): Restores? Hitpoints? based on your Hitpoints? level up to a maximum of <Num0> - can boost beyond your level \(Members\)$', source)
    if m: return f"{m.group(1)}: Az életerő szintedtől függően állít vissza életerőt, max. <Num0>-ig – túl is emelheti a szintedet (tagoknak)"

    # 20. Farming payment: "X Payment: Y x<Num0>"
    m = re.match(r'^(.+?) Payment: (.+?) ?x?<Num0>$', source)
    if m: return f"{m.group(1)} – fizetség: {m.group(2)} x<Num0>"
    m = re.match(r'^(.+?) Payment: (.+?)\(<Num0>\)$', source)
    if m: return f"{m.group(1)} – fizetség: {m.group(2)} (<Num0>)"

    # 21. Root harvest: "<Num0>x X roots"
    m = re.match(r'^<Num0>x (.+?) roots?$', source)
    if m: return f"<Num0>x {m.group(1)} gyökér"

    # 22. combAchvmt: "Mandatory requirements: ..." multi-line string
    if source.startswith('Mandatory requirements:'):
        result = source.replace('Mandatory requirements:', 'Kötelező követelmények:', 1)
        result = result.replace('Combat Achievement task difficulty:', 'Harci teljesítmény nehézség:')
        return result

    # 23. Chambers speed run patterns
    m = re.match(r'^(Chambers of Xeric(?:: CM)?) \(<Num0>-Scale\) Speed-(Chaser|Runner)$', source)
    if m:
        label = "Gyors teljesítő" if m.group(2) == "Runner" else "Gyors vadász"
        return f"{m.group(1)} (<Num0> fős) – {label}"

    # 24. "As with any skill..." restore message
    m = re.match(r'^As with any skill, you will restore <Num0> missing Hitpoint every minute', source)
    if m:
        return source.replace(
            'As with any skill, you will restore <Num0> missing Hitpoint every minute, but the best way of recovering Hitpoints is by eating food.',
            'Mint bármely készségnél, percenként <Num0> életerőpontot regenerálsz, de a legjobb módja az életerő visszaszerzésének az evés.'
        )

    # 19. Keep-English heuristics for proper nouns
    no_tags = '<' not in source and '>' not in source
    if no_tags:
        # combAchvmt task names (e.g. "A Demon's Best Friend")
        if subcat == 'combAchvmt':
            return source
        # mainTabs music track names: title-case, no leading '(', not a known label
        if subcat == 'mainTabs' and not source.startswith('(') and not source.startswith('['):
            return source
        # generalUI item names (construction furniture, etc.)
        if subcat == 'generalUI':
            return source

    return None


def get_subcat(unit):
    note = unit.find(f'{{{NS}}}note')
    if note is not None and note.text:
        for line in note.text.split('\n'):
            if line.startswith('sub_category:'):
                return line.split(': ', 1)[1].strip()
    return ''


def apply_translations():
    tree = etree.parse(XLIFF_PATH)
    body = tree.find(f'.//{{{NS}}}body')

    translated = 0
    skipped_existing = 0
    missing = []

    for unit in body.findall(f'.//{{{NS}}}trans-unit'):
        source_el = unit.find(f'{{{NS}}}source')
        target_el = unit.find(f'{{{NS}}}target')
        if source_el is None or target_el is None:
            continue

        source = source_el.text or ""

        if target_el.text and target_el.text.strip():
            skipped_existing += 1
            continue

        subcat = get_subcat(unit)
        result = translate_any(source, subcat)
        if result:
            target_el.text = result
            translated += 1
        else:
            missing.append((subcat, source))

    tree.write(XLIFF_PATH, pretty_print=True, xml_declaration=True, encoding='UTF-8')

    print(f"Done: {translated} translated, {skipped_existing} already had translation, {len(missing)} still missing.")
    print(f"\nMissing by subcategory:")
    from collections import Counter
    by_cat = Counter(cat for cat, _ in missing)
    for cat, count in by_cat.most_common():
        print(f"  {cat}: {count}")

    # Save missing list for review
    missing_path = os.path.join(os.path.dirname(__file__), 'hu_interface_missing.txt')
    with open(missing_path, 'w', encoding='utf-8') as f:
        current_cat = None
        for cat, src in sorted(missing):
            if cat != current_cat:
                f.write(f'\n=== {cat} ===\n')
                current_cat = cat
            f.write(f'{src}\n')
    print(f"\nMissing strings saved to: hu_interface_missing.txt")


if __name__ == '__main__':
    apply_translations()
