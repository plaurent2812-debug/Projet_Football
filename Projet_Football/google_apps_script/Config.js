// ================================================================
//  ⚽ FOOTBALL IA — Configuration & Menu
// ================================================================

// ── CONSTANTES ───────────────────────────────────────────────────
const LEAGUES = [
  { id: 61,  name: "Ligue 1",           flag: "🇫🇷" },
  { id: 62,  name: "Ligue 2",           flag: "🇫🇷" },
  { id: 39,  name: "Premier League",    flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿" },
  { id: 140, name: "La Liga",           flag: "🇪🇸" },
  { id: 135, name: "Serie A",           flag: "🇮🇹" },
  { id: 78,  name: "Bundesliga",        flag: "🇩🇪" },
  { id: 2,   name: "Champions League",  flag: "🏆" },
  { id: 3,   name: "Europa League",     flag: "🏆" },
];
const SEASON = 2025;
const ANTHROPIC_MODEL = "claude-sonnet-4-20250514";
const SHEET_NAME = "⚽ Prédictions";
const PERF_SHEET_NAME = "📈 Performance";
const PRONOS_SHEET_NAME = "🎰 Pronos";

// ── PALETTE DE COULEURS PARTAGÉE ─────────────────────────────────
function getColors_() {
  return {
    darkBg:    "#1a1a2e",
    headerBg:  "#16213e",
    accent:    "#0f3460",
    white:     "#ffffff",
    lightGray: "#f4f4f8",
    midGray:   "#e8e8ee",
    textDark:  "#222222",
    textLight: "#888888",
    blue:      "#1a73e8",
    greenBg:   "#e6f4ea", greenTx: "#1e7e34",
    yellowBg:  "#fff8e1", yellowTx:"#e67c00",
    orangeBg:  "#fff3e0", orangeTx:"#d84315",
    redBg:     "#fce8e6", redTx:   "#c62828",
    valueBg:   "#c8e6c9", valueTx: "#1b5e20",
    avoidBg:   "#ffcdd2", avoidTx: "#b71c1c",
    purpleTx:  "#6a1b9a",
    purpleBg:  "#f3e5f5", penTx: "#7b1fa2",
    penBg:     "#f3e5f5",
    cyanBg:    "#e0f7fa", cyanTx:  "#00695c",
    goldTx:    "#e65100", blueTx:  "#1a73e8",
    safeMain:  "#1b5e20", safeBg:  "#e8f5e9", safeLight: "#c8e6c9", safeBorder: "#2e7d32",
    funMain:   "#0d47a1", funBg:   "#e3f2fd", funLight:  "#bbdefb", funBorder:  "#1565c0",
    jpMain:    "#4a148c", jpBg:    "#f3e5f5", jpLight:   "#e1bee7", jpBorder:   "#6a1b9a"
  };
}

// ── MENU ─────────────────────────────────────────────────────────
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("⚽ Football IA")
    .addItem("① 📥  Importer les matchs",        "importMatches")
    .addItem("② 🧠  Lancer l'analyse IA",         "runAnalysis")
    .addItem("③ 📊  Rafraîchir l'affichage",      "refreshDisplay")
    .addItem("④ 🎰  Générer les Pronos du jour",  "refreshPronos")
    .addSeparator()
    .addSubMenu(ui.createMenu("🔄 Relancer une analyse (écraser)")
      .addItem("🇫🇷  Ligue 1",          "reanalyze_61")
      .addItem("🇫🇷  Ligue 2",          "reanalyze_62")
      .addItem("🏴󠁧󠁢󠁥󠁮󠁧󠁿  Premier League",   "reanalyze_39")
      .addItem("🇪🇸  La Liga",          "reanalyze_140")
      .addItem("🇮🇹  Serie A",          "reanalyze_135")
      .addItem("🇩🇪  Bundesliga",       "reanalyze_78")
      .addItem("🏆  Champions League",  "reanalyze_2")
      .addItem("🏆  Europa League",     "reanalyze_3")
    )
    .addItem("📈  Performance post-match",         "refreshPerformance")
    .addSeparator()
    .addItem("⚙️  Configurer les clés API",       "showConfigDialog")
    .addToUi();
}

// ── CONFIGURATION ────────────────────────────────────────────────
function getConfig_() {
  var props = PropertiesService.getScriptProperties();
  return {
    supabaseUrl:    props.getProperty("SUPABASE_URL")       || "",
    supabaseKey:    props.getProperty("SUPABASE_KEY")       || "",
    apiFootballKey: props.getProperty("API_FOOTBALL_KEY")   || "",
    anthropicKey:   props.getProperty("ANTHROPIC_API_KEY")  || ""
  };
}

function checkConfig_() {
  var c = getConfig_();
  if (!c.supabaseUrl || !c.supabaseKey || !c.apiFootballKey || !c.anthropicKey) {
    SpreadsheetApp.getUi().alert(
      "⚠️ Configuration incomplète",
      "Va dans ⚽ Football IA → ⚙️ Configurer les clés API pour renseigner tes clés.",
      SpreadsheetApp.getUi().ButtonSet.OK
    );
    return null;
  }
  return c;
}

// ── DIALOG : CONFIGURATION DES CLES ─────────────────────────────
function showConfigDialog() {
  var html = HtmlService.createHtmlOutput(CONFIG_HTML_)
    .setWidth(520)
    .setHeight(480);
  SpreadsheetApp.getUi().showModalDialog(html, "⚙️ Configuration des clés API");
}

function getConfigForDialog() {
  var c = getConfig_();
  return {
    supabaseUrl:    c.supabaseUrl,
    supabaseKey:    c.supabaseKey    ? "••••••••" : "",
    apiFootballKey: c.apiFootballKey ? "••••••••" : "",
    anthropicKey:   c.anthropicKey   ? "••••••••" : ""
  };
}

function saveConfig(cfg) {
  var props = PropertiesService.getScriptProperties();
  if (cfg.supabaseUrl)                               props.setProperty("SUPABASE_URL",      cfg.supabaseUrl);
  if (cfg.supabaseKey    && cfg.supabaseKey !== "••••••••")    props.setProperty("SUPABASE_KEY",      cfg.supabaseKey);
  if (cfg.apiFootballKey && cfg.apiFootballKey !== "••••••••") props.setProperty("API_FOOTBALL_KEY",   cfg.apiFootballKey);
  if (cfg.anthropicKey   && cfg.anthropicKey !== "••••••••")   props.setProperty("ANTHROPIC_API_KEY",  cfg.anthropicKey);
}

var CONFIG_HTML_ = '\
<style>\
  * { box-sizing: border-box; }\
  body { font-family: "Google Sans", Arial, sans-serif; padding: 24px; margin: 0; background: #fafafa; }\
  h3 { margin: 0 0 8px; color: #1a1a2e; }\
  p  { color: #666; font-size: 13px; margin: 0 0 16px; }\
  label { display: block; margin-top: 12px; font-weight: 600; font-size: 13px; color: #333; }\
  input { width: 100%; padding: 10px; margin-top: 4px; border: 1px solid #ddd; border-radius: 6px; font-size: 13px; }\
  input:focus { border-color: #1a73e8; outline: none; box-shadow: 0 0 0 2px rgba(26,115,232,.15); }\
  .btn { margin-top: 24px; padding: 12px 28px; background: #1a73e8; color: #fff; border: none; border-radius: 6px; font-size: 14px; font-weight: 600; cursor: pointer; }\
  .btn:hover { background: #1558b0; }\
</style>\
<h3>⚙️ Clés API</h3>\
<p>Stockées de manière sécurisée dans les propriétés du script Google.</p>\
<label>SUPABASE_URL</label>\
<input id="f1" placeholder="https://xxx.supabase.co">\
<label>SUPABASE_KEY</label>\
<input id="f2" type="password" placeholder="eyJ...">\
<label>API_FOOTBALL_KEY</label>\
<input id="f3" type="password" placeholder="Clé RapidAPI / API-Sports">\
<label>ANTHROPIC_API_KEY</label>\
<input id="f4" type="password" placeholder="sk-ant-...">\
<button class="btn" onclick="save()">💾 Sauvegarder</button>\
<script>\
google.script.run.withSuccessHandler(function(c){\
  if(c.supabaseUrl)    document.getElementById("f1").value=c.supabaseUrl;\
  if(c.supabaseKey)    document.getElementById("f2").value=c.supabaseKey;\
  if(c.apiFootballKey) document.getElementById("f3").value=c.apiFootballKey;\
  if(c.anthropicKey)   document.getElementById("f4").value=c.anthropicKey;\
}).getConfigForDialog();\
function save(){\
  google.script.run.withSuccessHandler(function(){\
    alert("✅ Configuration sauvegardée !");\
    google.script.host.close();\
  }).saveConfig({\
    supabaseUrl:    document.getElementById("f1").value,\
    supabaseKey:    document.getElementById("f2").value,\
    apiFootballKey: document.getElementById("f3").value,\
    anthropicKey:   document.getElementById("f4").value\
  });\
}\
</script>';
