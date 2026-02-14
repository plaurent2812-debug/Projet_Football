// ================================================================
//  ⚽ FOOTBALL IA — Performance & Analyse post-match
// ================================================================

function refreshPerformance() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var config = checkConfig_();
  if (!config) return;

  var C = getColors_();

  // ── Étape 1 : Scores réels ─────────────────────────────────────
  ss.toast("🔄 Mise à jour des scores réels…", "📈", -1);
  updateFinishedFixtures_(config);

  // ── Étape 2 : Évaluation ───────────────────────────────────────
  ss.toast("📊 Évaluation des pronostics…", "📈", -1);

  // Récupérer les fixtures des 90 derniers jours (évite la limite de 1000 lignes de Supabase)
  var tz = Session.getScriptTimeZone();
  var ninetyDaysAgo = new Date();
  ninetyDaysAgo.setDate(ninetyDaysAgo.getDate() - 90);
  var fromDate = Utilities.formatDate(ninetyDaysAgo, tz, "yyyy-MM-dd");

  var allFixtures = supabaseSelect_("fixtures",    "select=*&date=gte." + fromDate + "&order=date.desc&limit=2000");
  var predictions = supabaseSelect_("predictions", "select=*&limit=2000");
  var leagues     = supabaseSelect_("leagues",     "select=*");

  var predMap = {};
  for (var i = 0; i < predictions.length; i++) predMap[predictions[i].fixture_id] = predictions[i];
  var leagueMap = {};
  for (var i = 0; i < leagues.length; i++) leagueMap[leagues[i].api_id] = leagues[i];
  var flagMap = {};
  for (var i = 0; i < LEAGUES.length; i++) flagMap[LEAGUES[i].id] = LEAGUES[i].flag;

  var results = [];
  for (var i = 0; i < allFixtures.length; i++) {
    var fix = allFixtures[i];
    if (fix.status !== "FT" && fix.status !== "AET" && fix.status !== "PEN") continue;
    var pred = predMap[fix.id];
    if (!pred) continue;

    var ev = evaluateInline_(fix, pred);
    ev.fixture = fix;
    ev.prediction = pred;
    results.push(ev);
  }

  results.sort(function(a, b) { return new Date(b.fixture.date) - new Date(a.fixture.date); });

  // ── Étape 2b : Évaluation des tickets ─────────────────────────
  ss.toast("🎫 Évaluation des tickets…", "📈", -1);
  var ticketPicks = [];
  try {
    ticketPicks = supabaseSelect_("ticket_picks", "select=*");
  } catch (e) { /* table might not exist yet */ }
  var ticketStats = evaluateAndComputeTicketStats_(ticketPicks, allFixtures);

  // ── Étape 3 : Affichage ────────────────────────────────────────
  ss.toast("🎨 Création de l'affichage…", "📈", -1);

  var sheet = ss.getSheetByName(PERF_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(PERF_SHEET_NAME);
  } else {
    var filter = sheet.getFilter();
    if (filter) filter.remove();
    sheet.clear();
    sheet.clearFormats();
  }

  var row = 1;
  var maxCol = 12;

  // ── Titre ──────────────────────────────────────────────────────
  sheet.getRange(row, 1, 1, maxCol).merge().setBackground(C.darkBg);
  sheet.getRange(row, 1)
    .setValue("📈  PERFORMANCE DES PRONOSTICS  —  Football IA")
    .setFontSize(16).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 52);
  row++;

  var now = Utilities.formatDate(new Date(), "Europe/Paris", "dd/MM/yyyy à HH:mm");
  sheet.getRange(row, 1, 1, maxCol).merge().setBackground(C.lightGray);
  sheet.getRange(row, 1)
    .setValue("  📅 " + now + "   |   📊 " + results.length + " matchs évalués   |   🤖 Évaluation automatique depuis le Sheet")
    .setFontSize(10).setFontColor(C.textLight).setFontStyle("italic")
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 30);
  row++;

  sheet.setRowHeight(row, 8);
  row++;

  // ── Section 1 : Taux de réussite (prédictions + tickets) ──────

  // ── Titre gauche : Prédictions ──
  sheet.getRange(row, 1, 1, 5).merge().setBackground(C.accent);
  sheet.getRange(row, 1)
    .setValue("  🎯  TAUX DE RÉUSSITE PAR TYPE DE PARI")
    .setFontSize(12).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");

  // ── Titre droit : Tickets ──
  sheet.getRange(row, 7, 1, 6).merge().setBackground(C.accent);
  sheet.getRange(row, 7)
    .setValue("  🎫  TAUX DE RÉUSSITE DES TICKETS")
    .setFontSize(12).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 36);
  row++;

  // ── En-têtes gauche ──
  var perfHeaders = ["Type de pari", "Réussis", "Total", "Taux (%)", "Barre visuelle"];
  sheet.getRange(row, 1, 1, perfHeaders.length).setValues([perfHeaders]);
  sheet.getRange(row, 1, 1, perfHeaders.length)
    .setFontWeight("bold").setFontColor(C.white).setBackground(C.headerBg)
    .setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");

  // ── En-têtes droit ──
  var ticketHeaders = ["Ticket", "Picks OK", "Total", "Taux (%)", "Tkts OK", "Taux tkts"];
  sheet.getRange(row, 7, 1, ticketHeaders.length).setValues([ticketHeaders]);
  sheet.getRange(row, 7, 1, ticketHeaders.length)
    .setFontWeight("bold").setFontColor(C.white).setBackground(C.headerBg)
    .setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");

  // ── Colonne séparatrice ──
  sheet.getRange(row, 6).setBackground(C.white);
  sheet.setRowHeight(row, 32);
  row++;

  // ── Données gauche : types de pari ──
  var betMetrics = [
    { label: "📊 Résultat 1X2",    field: "r1x2" },
    { label: "⚽ BTTS",             field: "btts" },
    { label: "🎯 Over 0.5",        field: "o05" },
    { label: "🎯 Over 1.5",        field: "o15" },
    { label: "🎯 Over 2.5",        field: "o25" },
    { label: "💯 Score exact",      field: "score" },
    { label: "⚡ Buteur prédit",    field: "scorer" },
    { label: "💰 Pari recommandé", field: "bet" }
  ];

  // ── Données droit : tickets ──
  var ticketRows = [
    { label: "🛡️ SAFE",    type: "SAFE",    color: C.safeMain,  bg: C.safeBg },
    { label: "🎯 FUN",     type: "FUN",     color: C.funMain,   bg: C.funBg },
    { label: "🎰 JACKPOT", type: "JACKPOT", color: C.jpMain,    bg: C.jpBg },
    { label: "📊 TOTAL",   type: "TOTAL",   color: C.accent,    bg: C.lightGray }
  ];

  var maxRows = Math.max(betMetrics.length, ticketRows.length);

  for (var b = 0; b < maxRows; b++) {
    var rowBg = (row % 2 === 0) ? C.lightGray : C.white;

    // ── Gauche : type de pari ──
    if (b < betMetrics.length) {
      var bm = betMetrics[b];
      var ok = 0, tot = 0;
      for (var r = 0; r < results.length; r++) {
        var v = results[r][bm.field];
        if (v !== null && v !== undefined) { tot++; if (v) ok++; }
      }
      var pct = tot > 0 ? Math.round(ok / tot * 1000) / 10 : 0;
      var barLen = Math.round(pct / 5);
      var bar = "";
      for (var x = 0; x < barLen; x++) bar += "█";
      for (var x = barLen; x < 20; x++) bar += "░";

      sheet.getRange(row, 1, 1, 5).setValues([[bm.label, ok, tot, pct + "%", bar]]);
      sheet.getRange(row, 1, 1, 5).setBackground(rowBg).setFontSize(10).setVerticalAlignment("middle");
      sheet.getRange(row, 1).setFontWeight("bold").setHorizontalAlignment("left");
      sheet.getRange(row, 2, 1, 2).setHorizontalAlignment("center");
      sheet.getRange(row, 4).setHorizontalAlignment("center").setFontWeight("bold");
      sheet.getRange(row, 5).setFontFamily("Courier New").setFontSize(9);

      var pctCell = sheet.getRange(row, 4);
      if (pct >= 65)      { pctCell.setBackground(C.greenBg).setFontColor(C.greenTx); }
      else if (pct >= 50) { pctCell.setBackground(C.yellowBg).setFontColor(C.yellowTx); }
      else if (pct >= 35) { pctCell.setBackground(C.orangeBg).setFontColor(C.orangeTx); }
      else if (tot > 0)   { pctCell.setBackground(C.redBg).setFontColor(C.redTx); }
    } else {
      sheet.getRange(row, 1, 1, 5).setBackground(rowBg);
    }

    // ── Séparateur ──
    sheet.getRange(row, 6).setBackground(C.white);

    // ── Droit : ticket ──
    if (b < ticketRows.length) {
      var tk = ticketRows[b];
      var st = ticketStats[tk.type] || { evaluatedPicks: 0, wonPicks: 0, pickRate: 0, completedTickets: 0, wonTickets: 0, ticketRate: 0 };
      var tktStr = st.completedTickets > 0 ? (st.wonTickets + "/" + st.completedTickets) : "—";
      var tktPctStr = st.completedTickets > 0 ? (st.ticketRate + "%") : "—";
      var pickPctStr = st.evaluatedPicks > 0 ? (st.pickRate + "%") : "—";

      sheet.getRange(row, 7, 1, 6).setValues([[
        tk.label, st.wonPicks, st.evaluatedPicks, pickPctStr, tktStr, tktPctStr
      ]]);
      sheet.getRange(row, 7, 1, 6).setBackground(tk.bg).setFontSize(10).setVerticalAlignment("middle");
      sheet.getRange(row, 7).setFontWeight("bold").setFontColor(tk.color).setHorizontalAlignment("left");
      sheet.getRange(row, 8, 1, 2).setHorizontalAlignment("center");
      sheet.getRange(row, 10).setHorizontalAlignment("center").setFontWeight("bold");
      sheet.getRange(row, 11).setHorizontalAlignment("center").setFontWeight("bold");
      sheet.getRange(row, 12).setHorizontalAlignment("center").setFontWeight("bold");

      // Colorer le taux picks
      if (st.evaluatedPicks > 0) {
        colorPerfCell_(sheet, row, 10, st.pickRate, C);
      }
      // Colorer le taux tickets
      if (st.completedTickets > 0) {
        var tktPctCell = sheet.getRange(row, 12);
        tktPctCell.setFontWeight("bold");
        if (st.ticketRate >= 40)      { tktPctCell.setBackground(C.greenBg).setFontColor(C.greenTx); }
        else if (st.ticketRate >= 25) { tktPctCell.setBackground(C.yellowBg).setFontColor(C.yellowTx); }
        else if (st.ticketRate >= 10) { tktPctCell.setBackground(C.orangeBg).setFontColor(C.orangeTx); }
        else                          { tktPctCell.setBackground(C.redBg).setFontColor(C.redTx); }
      }
    } else {
      sheet.getRange(row, 7, 1, 6).setBackground(rowBg);
    }

    sheet.setRowHeight(row, 28);
    row++;
  }

  // ── Section 2 : Performance par ligue ──────────────────────────
  row++;
  sheet.setRowHeight(row, 8);
  row++;

  sheet.getRange(row, 1, 1, maxCol).merge().setBackground(C.accent);
  sheet.getRange(row, 1)
    .setValue("  🏆  PERFORMANCE PAR LIGUE")
    .setFontSize(12).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 36);
  row++;

  var lgHeaders = ["Ligue", "Matchs", "1X2 %", "BTTS %", "O0.5 %", "O1.5 %", "O2.5 %", "Score exact %"];
  sheet.getRange(row, 1, 1, lgHeaders.length).setValues([lgHeaders]);
  sheet.getRange(row, 1, 1, lgHeaders.length)
    .setFontWeight("bold").setFontColor(C.white).setBackground(C.headerBg)
    .setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(row, 32);
  row++;

  var byLeague = {};
  for (var i = 0; i < results.length; i++) {
    var lid = results[i].fixture.league_id;
    if (!lid) continue;
    if (!byLeague[lid]) byLeague[lid] = [];
    byLeague[lid].push(results[i]);
  }
  var leagueIds = Object.keys(byLeague).sort(function(a, b) { return byLeague[b].length - byLeague[a].length; });

  for (var li = 0; li < leagueIds.length; li++) {
    var lid = parseInt(leagueIds[li]);
    var lr = byLeague[lid];
    var lg = leagueMap[lid];
    var flag = flagMap[lid] || "⚽";
    var lName = lg ? lg.name : ("Ligue " + lid);

    var r1x2 = calcRateInline_(lr, "r1x2");
    var rBtts = calcRateInline_(lr, "btts");
    var rO05  = calcRateInline_(lr, "o05");
    var rO15  = calcRateInline_(lr, "o15");
    var rO25  = calcRateInline_(lr, "o25");
    var rCS   = calcRateInline_(lr, "score");

    sheet.getRange(row, 1, 1, 8).setValues([[flag + " " + lName, lr.length, r1x2 + "%", rBtts + "%", rO05 + "%", rO15 + "%", rO25 + "%", rCS + "%"]]);
    var rowBg = (row % 2 === 0) ? C.lightGray : C.white;
    sheet.getRange(row, 1, 1, 8).setBackground(rowBg).setFontSize(10).setVerticalAlignment("middle");
    sheet.getRange(row, 1).setFontWeight("bold").setHorizontalAlignment("left");
    sheet.getRange(row, 2, 1, 7).setHorizontalAlignment("center");
    colorPerfCell_(sheet, row, 3, r1x2, C);
    colorPerfCell_(sheet, row, 4, rBtts, C);
    colorPerfCell_(sheet, row, 5, rO05, C);
    colorPerfCell_(sheet, row, 6, rO15, C);
    colorPerfCell_(sheet, row, 7, rO25, C);
    sheet.setRowHeight(row, 28);
    row++;
  }

  // ── Section 3 : Analyse post-match ─────────────────────────────
  row++;
  sheet.setRowHeight(row, 8);
  row++;

  // Filtrer uniquement les matchs de la veille (matchs terminés hier)
  var yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  var tz = Session.getScriptTimeZone();
  var yStr = Utilities.formatDate(yesterday, tz, "yyyy-MM-dd");
  var yDisplay = Utilities.formatDate(yesterday, tz, "dd/MM/yyyy");

  var recent = [];
  for (var i = 0; i < results.length; i++) {
    var fixDateObj = new Date(results[i].fixture.date);
    var fixDateStr = Utilities.formatDate(fixDateObj, tz, "yyyy-MM-dd");
    if (fixDateStr === yStr) recent.push(results[i]);
  }

  sheet.getRange(row, 1, 1, maxCol).merge().setBackground(C.accent);
  sheet.getRange(row, 1)
    .setValue("  🔍  ANALYSE POST-MATCH  —  Matchs du " + yDisplay + "  (" + recent.length + " matchs)")
    .setFontSize(12).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 36);
  row++;

  var postHeaders = ["Match", "Score réel", "1X2", "BTTS", "O0.5", "O1.5", "O2.5", "Score exact", "Buteur", "Conf", "Analyse"];
  sheet.getRange(row, 1, 1, postHeaders.length).setValues([postHeaders]);
  sheet.getRange(row, 1, 1, postHeaders.length)
    .setFontWeight("bold").setFontColor(C.white).setBackground(C.headerBg)
    .setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(row, 32);
  row++;

  for (var i = 0; i < recent.length; i++) {
    var res = recent[i];
    var fix = res.fixture;
    var pred = res.prediction;
    var matchName = fix.home_team + " vs " + fix.away_team;
    var scoreStr = (fix.home_goals != null ? fix.home_goals : "?") + " - " + (fix.away_goals != null ? fix.away_goals : "?");

    var e1x2   = res.r1x2   ? "✅" : "❌";
    var eBtts  = res.btts    ? "✅" : "❌";
    var eO05   = res.o05     ? "✅" : "❌";
    var eO15   = res.o15     ? "✅" : "❌";
    var eO25   = res.o25     ? "✅" : "❌";
    var eScore = res.score   ? "✅" : "❌";
    var eScorer = res.scorer === true ? "✅" : (res.scorer === false ? "❌" : "—");
    var confStr = pred.confidence_score ? (pred.confidence_score + "/10") : "-";

    sheet.getRange(row, 1, 1, 11).setValues([[matchName, scoreStr, e1x2, eBtts, eO05, eO15, eO25, eScore, eScorer, confStr, res.analysis]]);

    var rowBg = (row % 2 === 0) ? C.lightGray : C.white;
    sheet.getRange(row, 1, 1, 11).setBackground(rowBg).setFontSize(9).setVerticalAlignment("middle");
    sheet.getRange(row, 1).setFontWeight("bold").setFontSize(10);
    sheet.getRange(row, 2).setHorizontalAlignment("center").setFontWeight("bold").setFontColor(C.accent);
    sheet.getRange(row, 3, 1, 7).setHorizontalAlignment("center").setFontSize(12);
    sheet.getRange(row, 10).setHorizontalAlignment("center").setFontWeight("bold");
    sheet.getRange(row, 11).setWrap(true).setFontSize(9);

    var conf = pred.confidence_score || 0;
    var cc = sheet.getRange(row, 10);
    if (conf >= 7)      { cc.setBackground(C.greenBg).setFontColor(C.greenTx); }
    else if (conf >= 5) { cc.setBackground(C.yellowBg).setFontColor(C.yellowTx); }
    else                { cc.setBackground(C.redBg).setFontColor(C.redTx); }

    if (res.r1x2 && res.btts && res.o25) sheet.getRange(row, 1).setBackground(C.greenBg);

    sheet.setRowHeight(row, res.analysis && res.analysis.length > 80 ? 55 : 32);
    row++;
  }

  if (recent.length === 0) {
    sheet.getRange(row, 1, 1, maxCol).merge();
    sheet.getRange(row, 1)
      .setValue("  ⏳ Aucun match terminé avec prédiction trouvé pour le " + yDisplay + ".")
      .setFontSize(11).setFontColor(C.textLight).setFontStyle("italic").setWrap(true)
      .setVerticalAlignment("middle");
    sheet.setRowHeight(row, 40);
    row++;
  }

  var widths = [200, 70, 60, 75, 150, 15, 130, 80, 75, 85, 85, 85];
  for (var c = 0; c < widths.length; c++) sheet.setColumnWidth(c + 1, widths[c]);

  sheet.setFrozenRows(3);
  ss.setActiveSheet(sheet);
  ss.toast("✅ Performance mise à jour ! (" + results.length + " matchs évalués)", "📈 Football IA", 5);
}


// ── HELPERS PERFORMANCE ──────────────────────────────────────────

function updateFinishedFixtures_(config) {
  // Récupérer TOUS les matchs non terminés (pas seulement NS)
  var allFix = supabaseSelect_("fixtures", "status=not.in.(FT,AET,PEN)&select=api_fixture_id,id,date,status");
  var now = new Date();
  var toCheck = [];
  for (var i = 0; i < allFix.length; i++) {
    var matchDate = new Date(allFix[i].date);
    // Vérifier les matchs dont le coup d'envoi est passé depuis > 2h
    if (now - matchDate > 2 * 60 * 60 * 1000) {
      toCheck.push(allFix[i]);
    }
  }

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (toCheck.length === 0) {
    ss.toast("Aucun match à mettre à jour.", "📈", 3);
    return;
  }

  ss.toast("🔄 Vérification de " + toCheck.length + " matchs…", "📈", -1);
  var updated = 0, errors = 0;

  for (var i = 0; i < toCheck.length; i++) {
    try {
      var data = fetchApiFootball_("fixtures", { id: toCheck[i].api_fixture_id });
      if (!data || !data.response || data.response.length === 0) continue;
      var f = data.response[0];
      var status = f.fixture.status.short;
      if (status === "FT" || status === "AET" || status === "PEN") {
        supabaseRequest_("PATCH", "fixtures", {
          query: "api_fixture_id=eq." + toCheck[i].api_fixture_id,
          body: { status: status, home_goals: f.goals.home, away_goals: f.goals.away }
        });
        updated++;
      }
      Utilities.sleep(300);
    } catch (e) {
      errors++;
      Logger.log("❌ Erreur mise à jour fixture " + toCheck[i].api_fixture_id + ": " + e.message);
    }
  }

  ss.toast("✅ " + updated + " matchs mis à jour" + (errors > 0 ? " (" + errors + " erreurs)" : ""), "📈", 5);
}

function evaluateInline_(fix, pred) {
  var hg = fix.home_goals || 0;
  var ag = fix.away_goals || 0;
  var total = hg + ag;

  var actualResult = hg > ag ? "H" : (hg === ag ? "D" : "A");

  var pH = pred.proba_home || 33;
  var pD = pred.proba_draw || 33;
  var pA = pred.proba_away || 33;
  var maxP = Math.max(pH, pD, pA);
  var predResult = maxP === pH ? "H" : (maxP === pA ? "A" : "D");
  var r1x2 = predResult === actualResult;

  var actualBtts = hg > 0 && ag > 0;
  var btts = ((pred.proba_btts || 50) >= 50) === actualBtts;

  var o05 = ((pred.proba_over_05 || 90) >= 50) === (total > 0);
  var o15 = ((pred.proba_over_15 || 70) >= 50) === (total > 1);
  var o25 = ((pred.proba_over_2_5 || 50) >= 50) === (total > 2);

  var scoreOk = false;
  if (pred.correct_score) {
    try {
      var parts = pred.correct_score.split("-");
      scoreOk = (parseInt(parts[0]) === hg && parseInt(parts[1]) === ag);
    } catch (e) {}
  }

  var scorerOk = null;
  if (pred.likely_scorer) {
    scorerOk = false;
  }

  var betOk = null;
  if (pred.recommended_bet) {
    var bt = pred.recommended_bet.toLowerCase();
    if (bt.indexOf("domicile") >= 0 || (bt.indexOf("victoire") >= 0 && bt.indexOf("ext") < 0)) betOk = actualResult === "H";
    else if (bt.indexOf("ext") >= 0 || bt.indexOf("visiteur") >= 0) betOk = actualResult === "A";
    else if (bt.indexOf("nul") >= 0) betOk = actualResult === "D";
    else if (bt.indexOf("btts") >= 0 || bt.indexOf("deux") >= 0) betOk = actualBtts;
    else if (bt.indexOf("2.5") >= 0 || bt.indexOf("plus de 2") >= 0) betOk = total > 2;
    else if (bt.indexOf("1.5") >= 0) betOk = total > 1;
  }

  var analysis = buildPostAnalysis_(fix, pred, actualResult, hg, ag, r1x2, btts, o25);

  return {
    r1x2: r1x2, btts: btts, o05: o05, o15: o15, o25: o25,
    score: scoreOk, scorer: scorerOk, bet: betOk,
    analysis: analysis
  };
}

function buildPostAnalysis_(fix, pred, actualResult, hg, ag, r1x2Ok, bttsOk, o25Ok) {
  var home = fix.home_team;
  var away = fix.away_team;
  var parts = [];

  parts.push(home + " " + hg + "-" + ag + " " + away + ".");

  var pH = pred.proba_home || 33;
  var pD = pred.proba_draw || 33;
  var pA = pred.proba_away || 33;

  if (r1x2Ok) {
    parts.push("✅ 1X2 correct (" + pH + "-" + pD + "-" + pA + "%).");
  } else {
    if (actualResult === "D") parts.push("❌ Nul non anticipé (" + pD + "% prédit).");
    else if (actualResult === "H") parts.push("❌ Victoire " + home + " ratée (" + pH + "% prédit).");
    else parts.push("❌ Victoire " + away + " ratée (" + pA + "% prédit).");
  }

  var pBtts = pred.proba_btts || 50;
  var actualBtts = hg > 0 && ag > 0;
  if (bttsOk) {
    parts.push("✅ BTTS correct (" + pBtts + "%).");
  } else {
    if (actualBtts) parts.push("❌ BTTS raté : les 2 ont marqué malgré " + pBtts + "% prédit.");
    else parts.push("❌ BTTS raté : une équipe n'a pas marqué (" + pBtts + "% prédit).");
  }

  var total = hg + ag;
  var pO25 = pred.proba_over_2_5 || 50;
  if (o25Ok) {
    parts.push("✅ O2.5 correct (" + total + " buts).");
  } else {
    if (total > 2) parts.push("❌ O2.5 raté : " + total + " buts mais " + pO25 + "% prédit.");
    else parts.push("❌ O2.5 raté : " + total + " buts seulement (" + pO25 + "% prédit).");
  }

  return parts.join(" ");
}

function calcRateInline_(results, field) {
  var ok = 0, tot = 0;
  for (var i = 0; i < results.length; i++) {
    var val = results[i][field];
    if (val !== null && val !== undefined) {
      tot++;
      if (val) ok++;
    }
  }
  return tot > 0 ? Math.round(ok / tot * 1000) / 10 : 0;
}

function colorPerfCell_(sheet, row, col, pct, C) {
  var cell = sheet.getRange(row, col);
  cell.setFontWeight("bold");
  if (pct >= 65)      { cell.setBackground(C.greenBg).setFontColor(C.greenTx); }
  else if (pct >= 50) { cell.setBackground(C.yellowBg).setFontColor(C.yellowTx); }
  else if (pct >= 35) { cell.setBackground(C.orangeBg).setFontColor(C.orangeTx); }
  else                { cell.setBackground(C.redBg).setFontColor(C.redTx); }
}


// ═══════════════════════════════════════════════════════════════════
//  ÉVALUATION DES TICKETS (SAFE / FUN / JACKPOT)
// ═══════════════════════════════════════════════════════════════════

function evaluateAndComputeTicketStats_(ticketPicks, allFixtures) {
  // Construire un map fixture_id → fixture pour les matchs terminés
  var fixMap = {};
  for (var i = 0; i < allFixtures.length; i++) {
    var f = allFixtures[i];
    if (f.status === "FT" || f.status === "AET" || f.status === "PEN") {
      fixMap[f.id] = f;
    }
  }

  // Évaluer les picks non encore évalués
  var updatedCount = 0;
  for (var i = 0; i < ticketPicks.length; i++) {
    var pick = ticketPicks[i];
    if (pick.is_won !== null && pick.is_won !== undefined) continue;

    var fixture = fixMap[pick.fixture_id];
    if (!fixture) continue;

    var isWon = evaluateSinglePick_(pick, fixture);
    pick.is_won = isWon;

    try {
      supabaseRequest_("PATCH", "ticket_picks", {
        query: "id=eq." + pick.id,
        body: { is_won: isWon, evaluated_at: new Date().toISOString() }
      });
      updatedCount++;
    } catch (e) { /* skip */ }
  }

  if (updatedCount > 0) {
    Logger.log("✅ " + updatedCount + " picks de tickets évalués");
  }

  // Calculer les statistiques par type de ticket
  var types = ["SAFE", "FUN", "JACKPOT"];
  var stats = {};

  for (var t = 0; t < types.length; t++) {
    var type = types[t];
    var typePicks = [];
    for (var i = 0; i < ticketPicks.length; i++) {
      if (ticketPicks[i].ticket_type === type) typePicks.push(ticketPicks[i]);
    }

    var evaluated = 0, won = 0;
    for (var i = 0; i < typePicks.length; i++) {
      if (typePicks[i].is_won !== null && typePicks[i].is_won !== undefined) {
        evaluated++;
        if (typePicks[i].is_won) won++;
      }
    }

    // Grouper par ticket_date pour les tickets complets
    var byDate = {};
    for (var i = 0; i < typePicks.length; i++) {
      var date = typePicks[i].ticket_date;
      if (!byDate[date]) byDate[date] = [];
      byDate[date].push(typePicks[i]);
    }

    var completedTickets = 0, wonTickets = 0;
    for (var date in byDate) {
      var datePicks = byDate[date];
      var allEvaluated = true;
      var allWon = true;
      for (var i = 0; i < datePicks.length; i++) {
        if (datePicks[i].is_won === null || datePicks[i].is_won === undefined) {
          allEvaluated = false;
          break;
        }
        if (!datePicks[i].is_won) allWon = false;
      }
      if (allEvaluated) {
        completedTickets++;
        if (allWon) wonTickets++;
      }
    }

    stats[type] = {
      evaluatedPicks:   evaluated,
      wonPicks:         won,
      pickRate:         evaluated > 0 ? Math.round(won / evaluated * 1000) / 10 : 0,
      completedTickets: completedTickets,
      wonTickets:       wonTickets,
      ticketRate:       completedTickets > 0 ? Math.round(wonTickets / completedTickets * 1000) / 10 : 0
    };
  }

  // Total global
  var totalEval = 0, totalWon = 0, totalCompleted = 0, totalWonTkt = 0;
  for (var t = 0; t < types.length; t++) {
    totalEval      += stats[types[t]].evaluatedPicks;
    totalWon       += stats[types[t]].wonPicks;
    totalCompleted += stats[types[t]].completedTickets;
    totalWonTkt    += stats[types[t]].wonTickets;
  }
  stats["TOTAL"] = {
    evaluatedPicks:   totalEval,
    wonPicks:         totalWon,
    pickRate:         totalEval > 0 ? Math.round(totalWon / totalEval * 1000) / 10 : 0,
    completedTickets: totalCompleted,
    wonTickets:       totalWonTkt,
    ticketRate:       totalCompleted > 0 ? Math.round(totalWonTkt / totalCompleted * 1000) / 10 : 0
  };

  return stats;
}


function evaluateSinglePick_(pick, fixture) {
  var hg = fixture.home_goals || 0;
  var ag = fixture.away_goals || 0;
  var total = hg + ag;
  var bet = pick.bet_type || "";
  var homeTeam = pick.home_team || fixture.home_team || "";
  var awayTeam = pick.away_team || fixture.away_team || "";

  // Victoire
  if (bet.indexOf("V ") === 0) {
    var team = bet.substring(2).trim();
    if (team === homeTeam) return hg > ag;
    if (team === awayTeam) return ag > hg;
    // Matching souple
    if (homeTeam.indexOf(team) >= 0 || team.indexOf(homeTeam) >= 0) return hg > ag;
    if (awayTeam.indexOf(team) >= 0 || team.indexOf(awayTeam) >= 0) return ag > hg;
    return false;
  }

  // Nul
  if (bet === "Nul") return hg === ag;

  // Double chance
  if (bet.indexOf("(1X)") >= 0) return hg >= ag;
  if (bet.indexOf("(X2)") >= 0) return ag >= hg;
  if (bet.indexOf("(12)") >= 0 || bet === "Pas de nul (12)") return hg !== ag;

  // BTTS
  if (bet === "BTTS Oui")  return hg > 0 && ag > 0;
  if (bet === "BTTS Non")  return !(hg > 0 && ag > 0);

  // Buts
  if (bet === "+0.5 buts") return total > 0;
  if (bet === "+1.5 buts") return total > 1;
  if (bet === "+2.5 buts") return total > 2;
  if (bet === "+3.5 buts") return total > 3;
  if (bet === "-2.5 buts") return total <= 2;
  if (bet === "-3.5 buts") return total <= 3;

  // Score exact
  if (bet.indexOf("Score ") === 0) {
    try {
      var parts = bet.replace("Score ", "").split("-");
      return parseInt(parts[0]) === hg && parseInt(parts[1]) === ag;
    } catch (e) { return false; }
  }

  // Buteur (évaluation simplifiée — nécessite match_events)
  if (bet.indexOf("buteur") >= 0) {
    // On essaie de vérifier via match_events si disponible
    try {
      var playerName = bet.replace("⚽ ", "").replace(" buteur", "").trim();
      var events = supabaseSelect_("match_events",
        "fixture_api_id=eq." + fixture.api_fixture_id + "&event_type=eq.Goal&select=player_name");
      for (var i = 0; i < events.length; i++) {
        var scorer = events[i].player_name || "";
        if (scorer.toLowerCase().indexOf(playerName.toLowerCase()) >= 0 ||
            playerName.toLowerCase().indexOf(scorer.toLowerCase()) >= 0) {
          return true;
        }
      }
    } catch (e) { /* skip */ }
    return false;
  }

  // Fallback pour picks legacy (Victoire Dom./Ext.)
  if (bet.indexOf("Dom") >= 0) return hg > ag;
  if (bet.indexOf("Ext") >= 0) return ag > hg;

  return false;
}
