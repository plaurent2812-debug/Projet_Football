// ================================================================
//  ⚽ FOOTBALL IA — Affichage professionnel (Google Sheet)
// ================================================================

function refreshDisplay() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.toast("Chargement…", "📊", -1);

  var C = getColors_();

  // ── Données ────────────────────────────────────────────────────
  var today = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd");
  var fixtures    = supabaseSelect_("fixtures",    "status=eq.NS&date=gte." + today + "&select=*&order=date.asc");
  var predictions = supabaseSelect_("predictions", "select=*");
  var leagues     = supabaseSelect_("leagues",     "select=*");
  var oddsData    = supabaseSelect_("fixture_odds", "select=*");
  var predMap = {};
  for (var i = 0; i < predictions.length; i++) predMap[predictions[i].fixture_id] = predictions[i];
  var leagueMap = {};
  for (var i = 0; i < leagues.length; i++) leagueMap[leagues[i].api_id] = leagues[i];
  var flagMap = {};
  for (var i = 0; i < LEAGUES.length; i++) flagMap[LEAGUES[i].id] = LEAGUES[i].flag;
  var oddsMap = {};
  for (var i = 0; i < oddsData.length; i++) oddsMap[oddsData[i].fixture_api_id] = oddsData[i];

  // ── Blessures ──────────────────────────────────────────────────
  var fixtureApiIds = [];
  for (var i = 0; i < fixtures.length; i++) {
    if (fixtures[i].api_fixture_id) fixtureApiIds.push(fixtures[i].api_fixture_id);
  }
  var injuryByTeam = {};
  if (fixtureApiIds.length > 0) {
    var inFilter = "fixture_api_id=in.(" + fixtureApiIds.join(",") + ")";
    var injuriesData = supabaseSelect_("injuries", "select=player_name,team_api_id,reason,type&" + inFilter);
    for (var i = 0; i < injuriesData.length; i++) {
      var inj = injuriesData[i];
      var tid = inj.team_api_id;
      if (!injuryByTeam[tid]) injuryByTeam[tid] = [];
      var dominated = false;
      for (var k = 0; k < injuryByTeam[tid].length; k++) {
        if (injuryByTeam[tid][k].player_name === inj.player_name) { dominated = true; break; }
      }
      if (!dominated) injuryByTeam[tid].push(inj);
    }
  }

  var teamNameData = supabaseSelect_("teams", "select=api_id,name");
  var teamNameToId = {};
  for (var i = 0; i < teamNameData.length; i++) teamNameToId[teamNameData[i].name] = teamNameData[i].api_id;

  // ── Feuille ────────────────────────────────────────────────────
  var sheet = ss.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(SHEET_NAME, 0);
  } else {
    var filter = sheet.getFilter();
    if (filter) filter.remove();
    sheet.clear();
    sheet.clearFormats();
    sheet.clearConditionalFormatRules();
  }

  var HEADERS = ["", "Ligue", "Journée", "Date", "Heure",
                 "Domicile", "", "Extérieur",
                 "Favori", "Nul %",
                 "BTTS %", "O0.5 %", "O1.5 %", "O2.5 %",
                 "Score", "Buteur", "Pen %",
                 "🏥 Absents clés", "Pari", "Conf", "Analyse"];
  var numCols = HEADERS.length;

  // ── Titre ──────────────────────────────────────────────────────
  sheet.getRange(1, 1, 1, numCols).merge().setBackground(C.darkBg);
  sheet.getRange(1, 1)
    .setValue("⚽  FOOTBALL IA  —  Prédictions & Value Betting")
    .setFontSize(16).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(1, 52);

  // ── Barre info ─────────────────────────────────────────────────
  var now = Utilities.formatDate(new Date(), "Europe/Paris", "dd/MM/yyyy à HH:mm");
  var analyzed = 0;
  for (var i = 0; i < fixtures.length; i++) { if (predMap[fixtures[i].id]) analyzed++; }
  sheet.getRange(2, 1, 1, numCols).merge().setBackground(C.lightGray);
  sheet.getRange(2, 1)
    .setValue("  📅 " + now + "   |   📊 " + fixtures.length + " matchs   |   🧠 " + analyzed + " analysés   |   💰 VALUE = notre modèle > bookmaker + 5%")
    .setFontSize(10).setFontColor(C.textLight).setFontStyle("italic")
    .setVerticalAlignment("middle");
  sheet.setRowHeight(2, 30);

  sheet.setRowHeight(3, 6);
  sheet.getRange(3, 1, 1, numCols).setBackground(C.white);

  // ── En-têtes ───────────────────────────────────────────────────
  var hr = sheet.getRange(4, 1, 1, numCols);
  hr.setValues([HEADERS]);
  hr.setFontWeight("bold").setFontColor(C.white).setBackground(C.headerBg)
    .setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(4, 36);

  // ── Tri par ligue puis date ────────────────────────────────────
  var leagueOrder = {};
  for (var i = 0; i < LEAGUES.length; i++) leagueOrder[LEAGUES[i].id] = i;

  fixtures.sort(function(a, b) {
    var oa = leagueOrder[a.league_id] !== undefined ? leagueOrder[a.league_id] : 99;
    var ob = leagueOrder[b.league_id] !== undefined ? leagueOrder[b.league_id] : 99;
    if (oa !== ob) return oa - ob;
    return new Date(a.date) - new Date(b.date);
  });

  // ── Lignes de données ──────────────────────────────────────────
  var row = 5;
  var currentLeagueId = -1;

  for (var i = 0; i < fixtures.length; i++) {
    var fix  = fixtures[i];
    var pred = predMap[fix.id];
    var lg   = leagueMap[fix.league_id];
    var flag = flagMap[fix.league_id] || "⚽";
    var lName= lg ? lg.name : ("Ligue " + fix.league_id);
    var roundName = (fix.stats_json && fix.stats_json.round) ? fix.stats_json.round : "-";

    var d = new Date(fix.date);
    var dateStr = Utilities.formatDate(d, "Europe/Paris", "dd/MM/yyyy");
    var timeStr = Utilities.formatDate(d, "Europe/Paris", "HH:mm");

    var odds = oddsMap[fix.api_fixture_id] || null;

    // ── Bandeau ligue ────────────────────────────────────────────
    if (fix.league_id !== currentLeagueId) {
      currentLeagueId = fix.league_id;
      if (i > 0) { sheet.setRowHeight(row, 6); sheet.getRange(row, 1, 1, numCols).setBackground(C.white); row++; }

      sheet.getRange(row, 1, 1, numCols).merge().setBackground(C.accent);
      sheet.getRange(row, 1)
        .setValue("  " + flag + "  " + lName.toUpperCase() + "  —  " + roundName)
        .setFontSize(11).setFontWeight("bold").setFontColor(C.white)
        .setVerticalAlignment("middle");
      sheet.setRowHeight(row, 32);
      row++;
    }

    // ── Données du match ─────────────────────────────────────────
    var rowBg = (row % 2 === 0) ? C.lightGray : C.white;

    var scorerStr = "-";
    var scorerNote = "";
    var topScorers = (pred && pred.stats_json && pred.stats_json.top_scorers) ? pred.stats_json.top_scorers : null;

    if (topScorers && topScorers.length > 0) {
      var lines = [];
      var noteLines = [];
      for (var sc = 0; sc < topScorers.length && sc < 3; sc++) {
        var s = topScorers[sc];
        lines.push(s.name + " (" + s.proba + "%)");
        noteLines.push("⚽ " + s.name + " — " + s.proba + "% (" + s.team + ")\n" + (s.analysis || ""));
      }
      scorerStr = lines.join("\n");
      scorerNote = noteLines.join("\n\n");
    } else if (pred && pred.likely_scorer) {
      scorerStr = pred.likely_scorer;
      if (pred.likely_scorer_proba) scorerStr += " (" + pred.likely_scorer_proba + "%)";
    }

    var absentsStr = buildAbsentsStr_(fix.home_team, fix.away_team, teamNameToId, injuryByTeam);

    var favoriStr = "-";
    var favoriProba = 0;
    if (pred) {
      if (pred.proba_home >= pred.proba_away) {
        favoriStr = fix.home_team + " (" + pred.proba_home + "%)";
        favoriProba = pred.proba_home;
      } else {
        favoriStr = fix.away_team + " (" + pred.proba_away + "%)";
        favoriProba = pred.proba_away;
      }
    }

    var rowData = [
      "",
      flag + " " + lName,
      roundName,
      dateStr,
      timeStr,
      fix.home_team,
      "vs",
      fix.away_team,
      favoriStr,
      pred ? pred.proba_draw + "%"                               : "-",
      pred ? pred.proba_btts + "%"                               : "-",
      pred && pred.proba_over_05 != null ? pred.proba_over_05 + "%" : "-",
      pred && pred.proba_over_15 != null ? pred.proba_over_15 + "%" : "-",
      pred ? pred.proba_over_2_5 + "%"                          : "-",
      pred && pred.correct_score ? pred.correct_score + (pred.proba_correct_score ? " (" + pred.proba_correct_score + "%)" : "") : "-",
      scorerStr,
      pred && pred.proba_penalty != null ? pred.proba_penalty + "%" : "-",
      absentsStr,
      pred ? pred.recommended_bet                               : "⏳",
      pred ? (pred.confidence_score + "/10")                    : "-",
      pred ? pred.analysis_text                                 : ""
    ];

    var rng = sheet.getRange(row, 1, 1, numCols);
    rng.setValues([rowData]);
    rng.setBackground(rowBg).setFontSize(9).setVerticalAlignment("middle");

    sheet.getRange(row, 6).setFontWeight("bold").setFontSize(10);
    sheet.getRange(row, 7).setFontColor(C.textLight).setHorizontalAlignment("center");
    sheet.getRange(row, 8).setFontWeight("bold").setFontSize(10);

    sheet.getRange(row, 1, 1, 8).setHorizontalAlignment("left");
    sheet.getRange(row, 9).setFontWeight("bold").setFontSize(9);
    sheet.getRange(row, 10, 1, 5).setHorizontalAlignment("center").setFontWeight("bold");
    sheet.getRange(row, 15).setHorizontalAlignment("center").setFontWeight("bold").setFontColor(C.accent);
    var scorerCell = sheet.getRange(row, 16);
    scorerCell.setFontWeight("bold").setFontColor(C.purpleTx).setWrap(true).setFontSize(8);
    if (scorerNote) scorerCell.setNote(scorerNote);
    sheet.getRange(row, 17).setHorizontalAlignment("center").setFontWeight("bold");

    var absentsCell = sheet.getRange(row, 18);
    absentsCell.setFontSize(8).setWrap(true);
    if (absentsStr && absentsStr !== "—") {
      absentsCell.setBackground("#fff3e0").setFontColor("#d84315");
    }

    sheet.getRange(row, 20).setHorizontalAlignment("center");

    if (pred) {
      var implied = computeImplied_(odds);

      colorCell_(sheet, row, 9, favoriProba, C);
      if (favoriProba >= 55) {
        sheet.getRange(row, 9).setValue(favoriStr + " ✓").setBackground(C.greenBg).setFontColor(C.greenTx);
      } else if (favoriProba < 35) {
        sheet.getRange(row, 9).setBackground(C.orangeBg).setFontColor(C.orangeTx);
      }

      valueCell_(sheet, row, 10, pred.proba_draw,      implied.draw,     C);
      valueCell_(sheet, row, 11, pred.proba_btts,      implied.btts,     C);
      valueCell_(sheet, row, 12, pred.proba_over_05 || 0, implied.over05, C);
      valueCell_(sheet, row, 13, pred.proba_over_15 || 0, implied.over15, C);
      valueCell_(sheet, row, 14, pred.proba_over_2_5,  implied.over25,   C);

      var penCell = sheet.getRange(row, 17);
      if (pred.proba_penalty != null) {
        if (pred.proba_penalty >= 35) {
          penCell.setBackground(C.penBg).setFontColor(C.penTx);
        } else if (pred.proba_penalty >= 25) {
          penCell.setBackground(C.yellowBg).setFontColor(C.yellowTx);
        } else {
          penCell.setFontColor(C.textLight);
        }
      }

      var conf = pred.confidence_score;
      var cc = sheet.getRange(row, 20);
      cc.setFontWeight("bold");
      if (conf >= 7)      { cc.setBackground(C.greenBg).setFontColor(C.greenTx); }
      else if (conf >= 5) { cc.setBackground(C.yellowBg).setFontColor(C.yellowTx); }
      else                { cc.setBackground(C.redBg).setFontColor(C.redTx); }

      sheet.getRange(row, 19).setFontWeight("bold").setFontColor(C.blue);
    } else {
      sheet.getRange(row, 19).setFontColor(C.textLight).setFontStyle("italic");
    }

    sheet.setRowHeight(row, (topScorers && topScorers.length >= 2) ? 52 : 30);
    row++;
  }

  // ── Largeurs colonnes ──────────────────────────────────────────
  var widths = [30, 140, 155, 82, 48, 180, 26, 180, 175, 58, 58, 58, 58, 58, 72, 190, 48, 180, 155, 58, 340];
  for (var c = 0; c < widths.length && c < numCols; c++) sheet.setColumnWidth(c + 1, widths[c]);

  sheet.getRange(5, numCols, Math.max(row - 5, 1), 1).setWrap(true);
  sheet.setFrozenRows(4);

  var filterRange = sheet.getRange(4, 1, Math.max(row - 4, 1), numCols);
  filterRange.createFilter();

  sheet.hideColumns(1);
  ss.setActiveSheet(sheet);
  ss.toast("✅ Affichage mis à jour !", "📊 Football IA", 5);
}


// ── HELPERS AFFICHAGE ────────────────────────────────────────────

function computeImplied_(odds) {
  var result = { home: null, draw: null, away: null, btts: null, over05: null, over15: null, over25: null };
  if (!odds) return result;

  if (odds.home_win_odds && odds.draw_odds && odds.away_win_odds) {
    var rawH = 1 / odds.home_win_odds;
    var rawD = 1 / odds.draw_odds;
    var rawA = 1 / odds.away_win_odds;
    var overround = rawH + rawD + rawA;
    result.home = Math.round(rawH / overround * 100);
    result.draw = Math.round(rawD / overround * 100);
    result.away = Math.round(rawA / overround * 100);
  }

  if (odds.btts_yes_odds && odds.btts_no_odds) {
    var rawY = 1 / odds.btts_yes_odds;
    var rawN = 1 / odds.btts_no_odds;
    var ovBtts = rawY + rawN;
    result.btts = Math.round(rawY / ovBtts * 100);
  }

  if (odds.over_05_odds && odds.under_05_odds) {
    var rawO05 = 1 / odds.over_05_odds;
    var rawU05 = 1 / odds.under_05_odds;
    var ov05 = rawO05 + rawU05;
    result.over05 = Math.round(rawO05 / ov05 * 100);
  }

  if (odds.over_15_odds && odds.under_15_odds) {
    var rawO15 = 1 / odds.over_15_odds;
    var rawU15 = 1 / odds.under_15_odds;
    var ov15 = rawO15 + rawU15;
    result.over15 = Math.round(rawO15 / ov15 * 100);
  }

  if (odds.over_25_odds && odds.under_25_odds) {
    var rawO = 1 / odds.over_25_odds;
    var rawU = 1 / odds.under_25_odds;
    var ov = rawO + rawU;
    result.over25 = Math.round(rawO / ov * 100);
  }

  return result;
}

function valueCell_(sheet, row, col, modelProba, impliedProba, C) {
  var cell = sheet.getRange(row, col);
  colorCell_(sheet, row, col, modelProba, C);
  if (impliedProba != null && modelProba != null) {
    var edge = modelProba - impliedProba;
    if (edge >= 5) {
      cell.setValue(modelProba + "% ✓");
      cell.setBackground(C.valueBg).setFontColor(C.valueTx);
    } else if (edge <= -10) {
      cell.setValue(modelProba + "% ✗");
      cell.setBackground(C.avoidBg).setFontColor(C.avoidTx);
    }
  }
}

function colorCell_(sheet, row, col, value, C) {
  var cell = sheet.getRange(row, col);
  if (value >= 55)      { cell.setBackground(C.greenBg).setFontColor(C.greenTx); }
  else if (value >= 40) { cell.setBackground(C.yellowBg).setFontColor(C.yellowTx); }
  else if (value >= 25) { cell.setBackground(C.orangeBg).setFontColor(C.orangeTx); }
  else                  { cell.setBackground(C.redBg).setFontColor(C.redTx); }
}

function buildAbsentsStr_(homeTeam, awayTeam, teamNameToId, injuryByTeam) {
  var parts = [];
  var homeId = teamNameToId[homeTeam];
  var awayId = teamNameToId[awayTeam];

  if (homeId && injuryByTeam[homeId]) {
    var homeInj = injuryByTeam[homeId];
    var names = [];
    for (var j = 0; j < homeInj.length && j < 3; j++) {
      var name = homeInj[j].player_name || "?";
      var nameParts = name.split(" ");
      if (nameParts.length > 1) name = nameParts[0].charAt(0) + ". " + nameParts[nameParts.length - 1];
      names.push(name);
    }
    if (names.length > 0) {
      var extra = homeInj.length > 3 ? " +" + (homeInj.length - 3) : "";
      parts.push("🏠 " + names.join(", ") + extra);
    }
  }

  if (awayId && injuryByTeam[awayId]) {
    var awayInj = injuryByTeam[awayId];
    var names = [];
    for (var j = 0; j < awayInj.length && j < 3; j++) {
      var name = awayInj[j].player_name || "?";
      var nameParts = name.split(" ");
      if (nameParts.length > 1) name = nameParts[0].charAt(0) + ". " + nameParts[nameParts.length - 1];
      names.push(name);
    }
    if (names.length > 0) {
      var extra = awayInj.length > 3 ? " +" + (awayInj.length - 3) : "";
      parts.push("✈️ " + names.join(", ") + extra);
    }
  }

  return parts.length > 0 ? parts.join("\n") : "—";
}
