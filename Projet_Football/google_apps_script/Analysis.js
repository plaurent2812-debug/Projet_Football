// ================================================================
//  ⚽ FOOTBALL IA — Analyse IA (Claude) & Reanalyse par ligue
// ================================================================

function runAnalysis() {
  var config = checkConfig_();
  if (!config) return;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.toast("Chargement des matchs…", "🧠 Football IA", -1);

  var today = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd");
  var fixtures   = supabaseSelect_("fixtures",    "status=eq.NS&date=gte." + today + "&select=*&order=date.asc");
  var predictions= supabaseSelect_("predictions", "select=fixture_id");
  var leagues    = supabaseSelect_("leagues",      "select=api_id,name");

  var predictedIds = {};
  for (var i = 0; i < predictions.length; i++) predictedIds[predictions[i].fixture_id] = true;

  var leagueMap = {};
  for (var i = 0; i < leagues.length; i++) leagueMap[leagues[i].api_id] = leagues[i].name;

  var toAnalyze = fixtures.filter(function(f) { return !predictedIds[f.id]; });

  if (toAnalyze.length === 0) {
    ss.toast("Tous les matchs sont déjà analysés !", "✅", 5);
    refreshDisplay();
    return;
  }

  var ok = 0, ko = 0;
  ss.toast("Analyse de " + toAnalyze.length + " matchs…", "🧠", -1);

  for (var i = 0; i < toAnalyze.length; i++) {
    var fix = toAnalyze[i];
    var lName = leagueMap[fix.league_id] || ("Ligue " + fix.league_id);

    ss.toast("(" + (i + 1) + "/" + toAnalyze.length + ") " + fix.home_team + " vs " + fix.away_team, "🧠 " + lName, -1);

    try {
      var pred = callAnthropic_(fix, lName, config);
      if (pred) {
        var insertData = {
          fixture_id:       fix.id,
          analysis_text:    pred.analysis_text,
          proba_home:       pred.proba_home,
          proba_draw:       pred.proba_draw,
          proba_away:       pred.proba_away,
          proba_btts:       pred.proba_btts,
          proba_over_05:    pred.proba_over_05,
          proba_over_15:    pred.proba_over_15,
          proba_over_2_5:   pred.proba_over_2_5,
          proba_over_35:    pred.proba_over_35,
          recommended_bet:  pred.recommended_bet,
          confidence_score: pred.confidence_score
        };

        if (pred.top_scorers && pred.top_scorers.length > 0) {
          insertData.likely_scorer       = pred.top_scorers[0].name;
          insertData.likely_scorer_proba = pred.top_scorers[0].proba;
          insertData.stats_json          = { top_scorers: pred.top_scorers };
        }

        supabaseInsert_("predictions", insertData);
        ok++;
      } else { ko++; }
    } catch (e) { ko++; }

    Utilities.sleep(600);
  }

  ss.toast("✅ " + ok + " analyses réussies" + (ko > 0 ? ", " + ko + " erreurs" : ""), "🧠 Football IA", 10);
  refreshDisplay();
}


// ================================================================
//  🔄 RELANCER L'ANALYSE PAR LIGUE
// ================================================================

function reanalyze_61()  { forceReanalysisLeague_(61,  "🇫🇷 Ligue 1"); }
function reanalyze_62()  { forceReanalysisLeague_(62,  "🇫🇷 Ligue 2"); }
function reanalyze_39()  { forceReanalysisLeague_(39,  "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League"); }
function reanalyze_140() { forceReanalysisLeague_(140, "🇪🇸 La Liga"); }
function reanalyze_135() { forceReanalysisLeague_(135, "🇮🇹 Serie A"); }
function reanalyze_78()  { forceReanalysisLeague_(78,  "🇩🇪 Bundesliga"); }
function reanalyze_2()   { forceReanalysisLeague_(2,   "🏆 Champions League"); }
function reanalyze_3()   { forceReanalysisLeague_(3,   "🏆 Europa League"); }

function forceReanalysisLeague_(leagueId, leagueName) {
  var config = checkConfig_();
  if (!config) return;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.toast("📋 Chargement " + leagueName + "…", "🔄", -1);

  var today = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd");
  var allFixtures = supabaseSelect_("fixtures", "status=eq.NS&league_id=eq." + leagueId + "&date=gte." + today + "&select=*&order=date.asc");

  if (allFixtures.length === 0) {
    ss.toast("Aucun match à analyser pour " + leagueName, "🔄", 5);
    return;
  }

  // Garder uniquement la prochaine journée
  var firstRound = null;
  for (var i = 0; i < allFixtures.length; i++) {
    var r = (allFixtures[i].stats_json && allFixtures[i].stats_json.round) ? allFixtures[i].stats_json.round : null;
    if (r) { firstRound = r; break; }
  }

  var fixtures = [];
  if (firstRound) {
    for (var i = 0; i < allFixtures.length; i++) {
      var r = (allFixtures[i].stats_json && allFixtures[i].stats_json.round) ? allFixtures[i].stats_json.round : null;
      if (r === firstRound) fixtures.push(allFixtures[i]);
    }
  } else {
    var firstDate = Utilities.formatDate(new Date(allFixtures[0].date), "Europe/Paris", "yyyy-MM-dd");
    for (var i = 0; i < allFixtures.length; i++) {
      var d = Utilities.formatDate(new Date(allFixtures[i].date), "Europe/Paris", "yyyy-MM-dd");
      if (Math.abs(new Date(d) - new Date(firstDate)) <= 3 * 24 * 60 * 60 * 1000) {
        fixtures.push(allFixtures[i]);
      }
    }
  }

  var roundLabel = firstRound ? (" — " + firstRound) : "";
  ss.toast("🗑️ " + leagueName + roundLabel + " : " + fixtures.length + " matchs. Suppression…", "🔄", -1);

  var deleted = 0;
  for (var i = 0; i < fixtures.length; i++) {
    try {
      supabaseRequest_("DELETE", "predictions", { query: "fixture_id=eq." + fixtures[i].id });
      deleted++;
    } catch (e) { /* skip */ }
  }

  var leagues = supabaseSelect_("leagues", "select=api_id,name");
  var leagueMap = {};
  for (var i = 0; i < leagues.length; i++) leagueMap[leagues[i].api_id] = leagues[i].name;

  ss.toast("🧠 Analyse de " + fixtures.length + " matchs " + leagueName + roundLabel + "…", "🔄", -1);
  var ok = 0, ko = 0;

  for (var i = 0; i < fixtures.length; i++) {
    var fix = fixtures[i];
    var lName = leagueMap[fix.league_id] || leagueName;
    ss.toast("(" + (i + 1) + "/" + fixtures.length + ") " + fix.home_team + " vs " + fix.away_team, "🧠 " + leagueName, -1);

    try {
      var pred = callAnthropic_(fix, lName, config);
      if (pred) {
        var insertData = {
          fixture_id:       fix.id,
          analysis_text:    pred.analysis_text,
          proba_home:       pred.proba_home,
          proba_draw:       pred.proba_draw,
          proba_away:       pred.proba_away,
          proba_btts:       pred.proba_btts,
          proba_over_05:    pred.proba_over_05,
          proba_over_15:    pred.proba_over_15,
          proba_over_2_5:   pred.proba_over_2_5,
          proba_over_35:    pred.proba_over_35,
          recommended_bet:  pred.recommended_bet,
          confidence_score: pred.confidence_score
        };
        if (pred.top_scorers && pred.top_scorers.length > 0) {
          insertData.likely_scorer       = pred.top_scorers[0].name;
          insertData.likely_scorer_proba = pred.top_scorers[0].proba;
          insertData.stats_json          = { top_scorers: pred.top_scorers };
        }
        supabaseInsert_("predictions", insertData);
        ok++;
      } else { ko++; }
    } catch (e) { ko++; }

    Utilities.sleep(600);
  }

  ss.toast("✅ " + leagueName + roundLabel + " : " + ok + "/" + fixtures.length + " analysés !", "🔄 Football IA", 10);
  refreshDisplay();
}
