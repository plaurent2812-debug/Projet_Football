// ================================================================
//  ⚽ FOOTBALL IA — Pronos / Tickets Combinés (Bet Builder)
// ================================================================

function refreshPronos() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var config = checkConfig_();
  if (!config) return;

  var C = getColors_();

  ss.toast("📊 Chargement des données…", "🎰 Pronos", -1);

  var today = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd");
  var fixtures    = supabaseSelect_("fixtures",     "status=eq.NS&date=gte." + today + "&select=*&order=date.asc");
  var predictions = supabaseSelect_("predictions",  "select=*");
  var leagues     = supabaseSelect_("leagues",      "select=*");
  var oddsData    = supabaseSelect_("fixture_odds", "select=*");

  var predMap = {}, leagueMap = {}, flagMap = {}, oddsMap = {};
  for (var i = 0; i < predictions.length; i++) predMap[predictions[i].fixture_id] = predictions[i];
  for (var i = 0; i < leagues.length; i++)     leagueMap[leagues[i].api_id] = leagues[i];
  for (var i = 0; i < LEAGUES.length; i++)     flagMap[LEAGUES[i].id] = LEAGUES[i].flag;
  for (var i = 0; i < oddsData.length; i++)    oddsMap[oddsData[i].fixture_api_id] = oddsData[i];

  var targetDate = null;
  var todayMatches = [];

  for (var i = 0; i < fixtures.length; i++) {
    var fix = fixtures[i];
    var pred = predMap[fix.id];
    if (!pred) continue;
    var matchDate = Utilities.formatDate(new Date(fix.date), "Europe/Paris", "yyyy-MM-dd");
    if (matchDate < today) continue;
    if (!targetDate) targetDate = matchDate;
    if (matchDate !== targetDate) continue;
    todayMatches.push({
      fixture: fix, prediction: pred,
      league: leagueMap[fix.league_id],
      flag: flagMap[fix.league_id] || "⚽",
      odds: oddsMap[fix.api_fixture_id] || null
    });
  }

  if (todayMatches.length === 0) {
    ss.toast("❌ Aucun match analysé trouvé", "🎰 Pronos", 5);
    return;
  }

  ss.toast("🧮 Génération des tickets (" + todayMatches.length + " matchs)…", "🎰 Pronos", -1);

  var matchBetsData = [];
  for (var i = 0; i < todayMatches.length; i++) {
    var m = todayMatches[i];
    matchBetsData.push({ match: m, bets: buildBetCandidates_(m) });
  }

  var safeTicket    = buildSafeTicket_(matchBetsData);
  var funTicket     = buildFunTicket_(matchBetsData);
  var jackpotTicket = buildJackpotTicket_(matchBetsData);

  // ── Sauvegarder les tickets en base Supabase ──
  ss.toast("💾 Sauvegarde des tickets en base…", "🎰 Pronos", -1);
  saveTicketsToSupabase_(safeTicket, funTicket, jackpotTicket, targetDate, todayMatches);

  renderPronosSheet_(ss, todayMatches, safeTicket, funTicket, jackpotTicket, targetDate, C);

  ss.toast("✅ 3 tickets de paris générés et sauvegardés !", "🎰 Pronos", 5);
}


// ── CONSTRUCTION DES PARIS POUR UN MATCH ─────────────────────────
function buildBetCandidates_(match) {
  var fix  = match.fixture;
  var pred = match.prediction;
  var odds = match.odds;
  var flag = match.flag;
  var lg   = match.league;
  var lName = lg ? lg.name : "Ligue";

  var matchLabel  = fix.home_team + " vs " + fix.away_team;
  var leagueLabel = flag + " " + lName;
  var time = Utilities.formatDate(new Date(fix.date), "Europe/Paris", "HH:mm");
  var conf = pred.confidence_score || 5;

  var pH  = pred.proba_home     || 0;
  var pD  = pred.proba_draw     || 0;
  var pA  = pred.proba_away     || 0;
  var pBt = pred.proba_btts     || 0;
  var pO05 = pred.proba_over_05  != null ? pred.proba_over_05  : null;
  var pO15 = pred.proba_over_15  != null ? pred.proba_over_15  : null;
  var pO25 = pred.proba_over_2_5 || 0;
  var pO35 = pred.proba_over_35  != null ? pred.proba_over_35  : null;

  var pDC1X = pred.proba_dc_1x || (pH + pD);
  var pDCX2 = pred.proba_dc_x2 || (pD + pA);
  var pDC12 = pred.proba_dc_12 || (pH + pA);

  var bets = [];

  function fair(p) { return (p && p > 0) ? Math.round(10000 / p) / 100 : 99; }
  function bookOrFair(bk, p) { return (bk && bk > 1) ? Math.round(bk * 100) / 100 : fair(p); }
  function isVal(p, bk) { return (bk && bk > 1 && p) ? (p > (100 / bk) + 5) : false; }

  function addBet(type, label, proba, bookOdds, grp) {
    if (!proba || proba <= 0) return;
    bets.push({
      matchId: fix.id, matchLabel: matchLabel, league: leagueLabel, time: time,
      betType: type, betLabel: label,
      proba: Math.round(proba * 10) / 10,
      odds: bookOrFair(bookOdds, proba),
      confidence: conf, isValue: isVal(proba, bookOdds),
      group: grp
    });
  }

  addBet("home",  "V " + fix.home_team,          pH,  odds ? odds.home_win_odds : null, "issue");
  addBet("draw",  "Nul",                          pD,  odds ? odds.draw_odds     : null, "issue");
  addBet("away",  "V " + fix.away_team,          pA,  odds ? odds.away_win_odds : null, "issue");
  addBet("dc1x",  fix.home_team + " ou Nul (1X)", Math.min(pDC1X, 98), null, "issue");
  addBet("dcx2",  fix.away_team + " ou Nul (X2)", Math.min(pDCX2, 98), null, "issue");
  addBet("dc12",  "Pas de nul (12)",              Math.min(pDC12, 98), null, "issue");

  addBet("btts_y", "BTTS Oui",  pBt,       odds ? odds.btts_yes_odds : null, "btts");
  addBet("btts_n", "BTTS Non",  100 - pBt,  odds ? odds.btts_no_odds  : null, "btts");

  if (pO05 != null) addBet("o05", "+0.5 buts",  pO05, odds ? odds.over_05_odds  : null, "goals");
  if (pO15 != null) addBet("o15", "+1.5 buts",  pO15, odds ? odds.over_15_odds  : null, "goals");
  addBet("o25", "+2.5 buts",                    pO25,  odds ? odds.over_25_odds  : null, "goals");
  addBet("u25", "-2.5 buts",                    100 - pO25, odds ? odds.under_25_odds : null, "goals");
  if (pO35 != null) {
    addBet("o35", "+3.5 buts", pO35,       null, "goals");
    addBet("u35", "-3.5 buts", 100 - pO35, null, "goals");
  }

  if (pred.likely_scorer && pred.likely_scorer_proba) {
    addBet("scorer", "⚽ " + pred.likely_scorer + " buteur", pred.likely_scorer_proba, null, "scorer");
  }

  if (pred.correct_score && pred.proba_correct_score) {
    addBet("score", "Score " + pred.correct_score, pred.proba_correct_score, null, "exact");
  }

  return bets;
}


// ── QUALITÉ & REDONDANCE ─────────────────────────────────────────
function betQuality_(bet) {
  var score = bet.proba;
  if (bet.isValue) score += 10;
  return score;
}

function isRedundant_(selected, newBet) {
  for (var i = 0; i < selected.length; i++) {
    var s = selected[i].betType;
    var n = newBet.betType;
    if (s === "btts_y" && (n === "o05" || n === "o15")) return true;
    if (n === "btts_y" && (s === "o05" || s === "o15")) return true;
    if (s === "o25" && (n === "o05" || n === "o15")) return true;
    if (n === "o25" && (s === "o05" || s === "o15")) return true;
    if (s === "o35" && (n === "o05" || n === "o15" || n === "o25")) return true;
    if (n === "o35" && (s === "o05" || s === "o15" || s === "o25")) return true;
  }
  return false;
}


// ── COMBO PAR MATCH ──────────────────────────────────────────────
function buildMatchCombo_(matchBets, groupsToUse, requiredGroups, minProba) {
  var byGroup = {};
  for (var i = 0; i < matchBets.length; i++) {
    var b = matchBets[i];
    if (!byGroup[b.group]) byGroup[b.group] = [];
    byGroup[b.group].push(b);
  }

  for (var g in byGroup) {
    byGroup[g].sort(function(a, b) { return betQuality_(b) - betQuality_(a); });
  }

  var selected = [];
  var matchInfo = matchBets.length > 0 ? matchBets[0] : null;
  if (!matchInfo) return null;

  if (requiredGroups) {
    for (var r = 0; r < requiredGroups.length; r++) {
      var rg = requiredGroups[r];
      if (!byGroup[rg] || byGroup[rg].length === 0) return null;
      var best = null;
      for (var j = 0; j < byGroup[rg].length; j++) {
        if (byGroup[rg][j].proba >= Math.max(minProba, 1) && !isRedundant_(selected, byGroup[rg][j])) {
          best = byGroup[rg][j];
          break;
        }
      }
      if (!best) return null;
      selected.push(best);
    }
  }

  for (var g = 0; g < groupsToUse.length; g++) {
    var grp = groupsToUse[g];
    var alreadyCovered = false;
    for (var s = 0; s < selected.length; s++) {
      if (selected[s].group === grp) { alreadyCovered = true; break; }
    }
    if (alreadyCovered) continue;
    if (!byGroup[grp] || byGroup[grp].length === 0) continue;

    for (var j = 0; j < byGroup[grp].length; j++) {
      var bet = byGroup[grp][j];
      if (bet.proba < minProba) continue;
      if (isRedundant_(selected, bet)) continue;
      selected.push(bet);
      break;
    }
  }

  if (selected.length < 2) return null;

  var comboOdds = 1;
  var comboProba = 1;
  var labels = [];
  var hasValue = false;
  for (var i = 0; i < selected.length; i++) {
    comboOdds  *= selected[i].odds;
    comboProba *= selected[i].proba / 100;
    labels.push(selected[i].betLabel + " (" + selected[i].odds.toFixed(2) + ")");
    if (selected[i].isValue) hasValue = true;
  }

  var avgSelProba = 0;
  for (var i = 0; i < selected.length; i++) avgSelProba += selected[i].proba;
  avgSelProba /= selected.length;
  var valueBonus = hasValue ? 0.5 : 0;

  // Confiance basée sur la proba combinée réelle (pas la moyenne des sélections)
  var cpPct = Math.round(comboProba * 10000) / 100;
  var realConf;
  if (cpPct >= 65) realConf = 9;
  else if (cpPct >= 50) realConf = 8;
  else if (cpPct >= 40) realConf = 7;
  else if (cpPct >= 30) realConf = 6;
  else if (cpPct >= 20) realConf = 5;
  else if (cpPct >= 12) realConf = 4;
  else if (cpPct >= 5) realConf = 3;
  else realConf = 2;
  realConf = Math.min(10, realConf + valueBonus);

  return {
    matchId:    matchInfo.matchId,
    matchLabel: matchInfo.matchLabel,
    league:     matchInfo.league,
    time:       matchInfo.time,
    confidence: realConf,
    avgSelProba: avgSelProba,
    selections: selected,
    comboOdds:  Math.round(comboOdds * 100) / 100,
    comboProba: Math.round(comboProba * 10000) / 100,
    comboLabel: labels.join(" + "),
    hasValue:   hasValue
  };
}

function comboScore_(combo) {
  var score = combo.comboProba * 10;
  score += combo.confidence * 3;
  if (combo.hasValue) score += 15;
  score += combo.selections.length * 2;
  return score;
}


// ── TICKET SAFE ──────────────────────────────────────────────────
// 3 matchs  •  V ou Nul meilleure équipe + O0.5 buts par match
function buildSafeTicket_(matchBetsData) {
  var combos = [];

  for (var i = 0; i < matchBetsData.length; i++) {
    var bets = matchBetsData[i].bets;
    if (!bets || bets.length === 0) continue;

    // Trouver les paris disponibles
    var dc1x = null, dcx2 = null, o05 = null, o15 = null;
    for (var j = 0; j < bets.length; j++) {
      if (bets[j].betType === "dc1x") dc1x = bets[j];
      if (bets[j].betType === "dcx2") dcx2 = bets[j];
      if (bets[j].betType === "o05")  o05  = bets[j];
      if (bets[j].betType === "o15")  o15  = bets[j];
    }

    // V ou Nul de la meilleure équipe (double chance)
    var bestDC = null;
    if (dc1x && dcx2) bestDC = dc1x.proba >= dcx2.proba ? dc1x : dcx2;
    else if (dc1x) bestDC = dc1x;
    else if (dcx2) bestDC = dcx2;

    // +0.5 buts (fallback +1.5 si indisponible)
    var goalsBet = o05 || o15;

    if (!bestDC || !goalsBet) continue;

    var selected = [bestDC, goalsBet];
    var comboOdds = bestDC.odds * goalsBet.odds;
    var comboProba = (bestDC.proba / 100) * (goalsBet.proba / 100);
    var cpPct = Math.round(comboProba * 10000) / 100;

    var realConf;
    if (cpPct >= 85) realConf = 9;
    else if (cpPct >= 75) realConf = 8;
    else if (cpPct >= 65) realConf = 7;
    else if (cpPct >= 55) realConf = 6;
    else if (cpPct >= 45) realConf = 5;
    else realConf = 4;
    if (bestDC.isValue || goalsBet.isValue) realConf = Math.min(10, realConf + 0.5);

    combos.push({
      matchId:    bets[0].matchId,
      matchLabel: bets[0].matchLabel,
      league:     bets[0].league,
      time:       bets[0].time,
      confidence: realConf,
      avgSelProba: (bestDC.proba + goalsBet.proba) / 2,
      selections: selected,
      comboOdds:  Math.round(comboOdds * 100) / 100,
      comboProba: cpPct,
      hasValue:   bestDC.isValue || goalsBet.isValue
    });
  }

  // Trier par proba combinée décroissante (les plus sûrs d'abord)
  combos.sort(function(a, b) { return b.comboProba - a.comboProba; });

  // Prendre les 3 meilleurs matchs
  var selected = combos.slice(0, 3);

  return buildComboTicketResult_(selected);
}


// ── TICKET FUN ───────────────────────────────────────────────────
// 3-5 matchs  •  V meilleure équipe + nombre de buts + BTTS par match
function buildFunTicket_(matchBetsData) {
  var combos = [];

  for (var i = 0; i < matchBetsData.length; i++) {
    var bets = matchBetsData[i].bets;
    if (!bets || bets.length === 0) continue;

    // Trouver les paris disponibles
    var home = null, away = null, bttsY = null, bttsN = null;
    var goalsBets = [];
    for (var j = 0; j < bets.length; j++) {
      if (bets[j].betType === "home")   home  = bets[j];
      if (bets[j].betType === "away")   away  = bets[j];
      if (bets[j].betType === "btts_y") bttsY = bets[j];
      if (bets[j].betType === "btts_n") bttsN = bets[j];
      // Lignes de buts intéressantes (O/U 2.5, 3.5) — exclure O0.5/O1.5 trop évidents
      if (bets[j].betType === "o25" || bets[j].betType === "u25" ||
          bets[j].betType === "o35" || bets[j].betType === "u35") {
        goalsBets.push(bets[j]);
      }
    }

    // V meilleure équipe (victoire sèche, pas double chance)
    var bestWin = null;
    if (home && away) bestWin = home.proba >= away.proba ? home : away;
    else if (home) bestWin = home;
    else if (away) bestWin = away;

    // Nombre de buts le plus probable (O/U 2.5 ou 3.5)
    var bestGoals = null;
    if (goalsBets.length > 0) {
      goalsBets.sort(function(a, b) { return b.proba - a.proba; });
      bestGoals = goalsBets[0];
    }

    // BTTS Oui ou Non selon le plus probable
    var bestBtts = null;
    if (bttsY && bttsN) bestBtts = bttsY.proba >= bttsN.proba ? bttsY : bttsN;
    else if (bttsY) bestBtts = bttsY;
    else if (bttsN) bestBtts = bttsN;

    if (!bestWin || !bestGoals || !bestBtts) continue;

    var selected = [bestWin, bestGoals, bestBtts];
    var comboOdds = bestWin.odds * bestGoals.odds * bestBtts.odds;
    var comboProba = (bestWin.proba / 100) * (bestGoals.proba / 100) * (bestBtts.proba / 100);
    var cpPct = Math.round(comboProba * 10000) / 100;

    var realConf;
    if (cpPct >= 40) realConf = 9;
    else if (cpPct >= 30) realConf = 8;
    else if (cpPct >= 20) realConf = 7;
    else if (cpPct >= 15) realConf = 6;
    else if (cpPct >= 10) realConf = 5;
    else if (cpPct >= 5) realConf = 4;
    else realConf = 3;
    if (bestWin.isValue) realConf = Math.min(10, realConf + 0.5);

    combos.push({
      matchId:    bets[0].matchId,
      matchLabel: bets[0].matchLabel,
      league:     bets[0].league,
      time:       bets[0].time,
      confidence: realConf,
      avgSelProba: (bestWin.proba + bestGoals.proba + bestBtts.proba) / 3,
      selections: selected,
      comboOdds:  Math.round(comboOdds * 100) / 100,
      comboProba: cpPct,
      hasValue:   bestWin.isValue || bestGoals.isValue || bestBtts.isValue
    });
  }

  // Trier par score (proba + confiance + value)
  combos.sort(function(a, b) { return comboScore_(b) - comboScore_(a); });

  // 3 à 5 matchs
  var selected = [];
  var totalOdds = 1;
  for (var i = 0; i < combos.length; i++) {
    selected.push(combos[i]);
    totalOdds *= combos[i].comboOdds;
    // Arrêter si cote ≥ 10 ET au moins 3 matchs
    if (selected.length >= 3 && totalOdds >= 10) break;
    if (selected.length >= 5) break;
  }

  return buildComboTicketResult_(selected);
}


// ── TICKET JACKPOT ───────────────────────────────────────────────
// 3-6 matchs  •  V meilleure équipe + buteur le plus probable par match
function buildJackpotTicket_(matchBetsData) {
  var combos = [];

  for (var i = 0; i < matchBetsData.length; i++) {
    var bets = matchBetsData[i].bets;
    if (!bets || bets.length === 0) continue;

    // Trouver les paris disponibles
    var home = null, away = null, scorer = null;
    for (var j = 0; j < bets.length; j++) {
      if (bets[j].betType === "home")   home   = bets[j];
      if (bets[j].betType === "away")   away   = bets[j];
      if (bets[j].betType === "scorer") scorer = bets[j];
    }

    // V meilleure équipe (victoire sèche)
    var bestWin = null;
    if (home && away) bestWin = home.proba >= away.proba ? home : away;
    else if (home) bestWin = home;
    else if (away) bestWin = away;

    // Buteur obligatoire pour le JACKPOT
    if (!bestWin || !scorer) continue;

    var selected = [bestWin, scorer];
    var comboOdds = bestWin.odds * scorer.odds;
    var comboProba = (bestWin.proba / 100) * (scorer.proba / 100);
    var cpPct = Math.round(comboProba * 10000) / 100;

    var realConf;
    if (cpPct >= 20) realConf = 9;
    else if (cpPct >= 15) realConf = 8;
    else if (cpPct >= 10) realConf = 7;
    else if (cpPct >= 7) realConf = 6;
    else if (cpPct >= 4) realConf = 5;
    else if (cpPct >= 2) realConf = 4;
    else realConf = 3;

    combos.push({
      matchId:    bets[0].matchId,
      matchLabel: bets[0].matchLabel,
      league:     bets[0].league,
      time:       bets[0].time,
      confidence: realConf,
      avgSelProba: (bestWin.proba + scorer.proba) / 2,
      selections: selected,
      comboOdds:  Math.round(comboOdds * 100) / 100,
      comboProba: cpPct,
      hasValue:   bestWin.isValue || scorer.isValue
    });
  }

  // Trier par score (proba + confiance + value)
  combos.sort(function(a, b) { return comboScore_(b) - comboScore_(a); });

  // 3 à 6 matchs
  var selected = [];
  var totalOdds = 1;
  for (var i = 0; i < combos.length; i++) {
    selected.push(combos[i]);
    totalOdds *= combos[i].comboOdds;
    // Arrêter si cote ≥ 30 ET au moins 3 matchs
    if (selected.length >= 3 && totalOdds >= 30) break;
    if (selected.length >= 6) break;
  }

  return buildComboTicketResult_(selected);
}


// ── TICKET RESULT ────────────────────────────────────────────────
function buildComboTicketResult_(combos) {
  var totalOdds = 1;
  var totalProba = 1;
  for (var i = 0; i < combos.length; i++) {
    totalOdds  *= combos[i].comboOdds;
    totalProba *= combos[i].comboProba / 100;
  }
  return {
    combos:        combos,
    combinedOdds:  Math.round(totalOdds * 100) / 100,
    combinedProba: Math.round(totalProba * 10000) / 100
  };
}


// ── CONFIANCE DU TICKET ──────────────────────────────────────────
// Basée sur la confiance moyenne des combos individuels
function buildTicketConfidence_(ticket, type) {
  if (ticket.combos.length === 0) return "—";

  var avgConf = 0;
  for (var i = 0; i < ticket.combos.length; i++) {
    avgConf += ticket.combos[i].confidence;
  }
  avgConf /= ticket.combos.length;

  var stars;
  if (avgConf >= 8)      stars = 5;
  else if (avgConf >= 7) stars = 4;
  else if (avgConf >= 6) stars = 3;
  else if (avgConf >= 5) stars = 2;
  else                   stars = 1;

  var starStr = "";
  for (var i = 0; i < 5; i++) starStr += (i < stars ? "⭐" : "☆");
  return starStr;
}


function countTotalSelections_(ticket) {
  var n = 0;
  for (var i = 0; i < ticket.combos.length; i++) {
    n += ticket.combos[i].selections.length;
  }
  return n;
}


// ── RENDU PRONOS SHEET ───────────────────────────────────────────
function renderPronosSheet_(ss, todayMatches, safeTicket, funTicket, jackpotTicket, dateStr, C) {
  var sheet = ss.getSheetByName(PRONOS_SHEET_NAME);
  if (!sheet) {
    sheet = ss.insertSheet(PRONOS_SHEET_NAME);
  } else {
    var filter = sheet.getFilter();
    if (filter) filter.remove();
    sheet.clear();
    sheet.clearFormats();
    sheet.clearConditionalFormatRules();
  }

  var numCols = 9;
  var row = 1;

  // ── Titre ──────────────────────────────────────────────────────
  sheet.getRange(row, 1, 1, numCols).merge().setBackground(C.darkBg);
  sheet.getRange(row, 1)
    .setValue("🎰  PRONOS DU JOUR  —  Tickets Combinés (Bet Builder)")
    .setFontSize(16).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 52);
  row++;

  var displayDate = dateStr;
  try { var p = dateStr.split("-"); displayDate = p[2] + "/" + p[1] + "/" + p[0]; } catch(e) {}
  sheet.getRange(row, 1, 1, numCols).merge().setBackground(C.lightGray);
  sheet.getRange(row, 1)
    .setValue("  📅 " + displayDate + "   |   ⚽ " + todayMatches.length + " matchs   |   🎯 3 tickets combinés   |   📌 Plusieurs paris par match pour booster les cotes")
    .setFontSize(10).setFontColor(C.textLight).setFontStyle("italic")
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 30);
  row++;
  sheet.setRowHeight(row, 10); row++;

  // ── Tickets ────────────────────────────────────────────────────
  var safeConf = buildTicketConfidence_(safeTicket, "safe");
  var safeSels = countTotalSelections_(safeTicket);
  row = renderTicket_(sheet, row, numCols, C, safeTicket,
    "🔒  TICKET SAFE",
    "3 matchs  •  " + safeSels + " sélections  •  V ou Nul meilleure équipe + O0.5 buts",
    safeConf, C.safeMain, C.safeBg, C.safeLight, C.safeBorder);
  row++; sheet.setRowHeight(row, 12); row++;

  var funConf = buildTicketConfidence_(funTicket, "fun");
  var funSels = countTotalSelections_(funTicket);
  row = renderTicket_(sheet, row, numCols, C, funTicket,
    "🎲  TICKET FUN",
    funTicket.combos.length + " matchs  •  " + funSels + " sélections  •  V meilleure équipe + buts + BTTS  •  Cote visée ≥ 10",
    funConf, C.funMain, C.funBg, C.funLight, C.funBorder);
  row++; sheet.setRowHeight(row, 12); row++;

  var jpConf = buildTicketConfidence_(jackpotTicket, "jackpot");
  var jpSels = countTotalSelections_(jackpotTicket);
  row = renderTicket_(sheet, row, numCols, C, jackpotTicket,
    "💎  TICKET JACKPOT — Buteur inclus",
    jackpotTicket.combos.length + " matchs  •  " + jpSels + " sélections  •  V meilleure équipe + ⚽ buteur probable  •  Cote visée ≥ 30",
    jpConf, C.jpMain, C.jpBg, C.jpLight, C.jpBorder);

  // ── Résumé comparatif ──────────────────────────────────────────
  row += 2;
  sheet.getRange(row, 1, 1, numCols).merge().setBackground(C.accent);
  sheet.getRange(row, 1)
    .setValue("  📋  RÉSUMÉ DES 3 TICKETS")
    .setFontSize(12).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 36);
  row++;

  var summH = ["Ticket", "Matchs", "Cote combinée", "Probabilité", "Gain 10€", "Gain 20€", "Gain 50€", "Confiance", ""];
  sheet.getRange(row, 1, 1, numCols).setValues([summH]);
  sheet.getRange(row, 1, 1, numCols)
    .setFontWeight("bold").setFontColor(C.white).setBackground(C.headerBg)
    .setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(row, 32);
  row++;

  var tix = [
    { n: "🔒 SAFE",    t: safeTicket,    bg: C.safeBg,  tx: C.safeMain,  r: safeConf },
    { n: "🎲 FUN",     t: funTicket,     bg: C.funBg,   tx: C.funMain,   r: funConf },
    { n: "💎 JACKPOT", t: jackpotTicket, bg: C.jpBg,    tx: C.jpMain,    r: jpConf }
  ];
  for (var t = 0; t < tix.length; t++) {
    var tk = tix[t];
    sheet.getRange(row, 1, 1, numCols).setValues([[
      tk.n, tk.t.combos.length + " matchs",
      tk.t.combinedOdds.toFixed(2), tk.t.combinedProba + "%",
      (tk.t.combinedOdds * 10).toFixed(2) + "€",
      (tk.t.combinedOdds * 20).toFixed(2) + "€",
      (tk.t.combinedOdds * 50).toFixed(2) + "€",
      tk.r, ""
    ]]);
    sheet.getRange(row, 1, 1, numCols).setBackground(tk.bg).setFontSize(10)
      .setHorizontalAlignment("center").setVerticalAlignment("middle");
    sheet.getRange(row, 1).setFontWeight("bold").setFontColor(tk.tx).setHorizontalAlignment("left");
    sheet.getRange(row, 3).setFontWeight("bold").setFontSize(12).setFontColor(tk.tx);
    sheet.getRange(row, 5, 1, 3).setFontWeight("bold").setFontColor(C.goldTx);
    sheet.getRange(row, 8).setFontWeight("bold");
    sheet.setRowHeight(row, 32);
    row++;
  }

  // ── Disclaimer ─────────────────────────────────────────────────
  row++; sheet.setRowHeight(row, 8); row++;
  sheet.getRange(row, 1, 1, numCols).merge();
  sheet.getRange(row, 1)
    .setValue("⚠️ AVERTISSEMENT : Pronostics générés par modèle statistique + IA + ML. Jouez de manière responsable.")
    .setFontSize(9).setFontColor(C.textLight).setFontStyle("italic").setWrap(true)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 50);

  var widths = [160, 200, 260, 80, 80, 75, 75, 70, 80];
  for (var c = 0; c < widths.length; c++) sheet.setColumnWidth(c + 1, widths[c]);
  sheet.setFrozenRows(3);
  ss.setActiveSheet(sheet);
}


// ── RENDU D'UN TICKET ────────────────────────────────────────────
function renderTicket_(sheet, row, numCols, C, ticket, title, subtitle, confidence, mainColor, bgColor, lightColor, borderColor) {
  sheet.getRange(row, 1, 1, numCols).merge().setBackground(mainColor);
  sheet.getRange(row, 1)
    .setValue("  " + title)
    .setFontSize(14).setFontWeight("bold").setFontColor(C.white)
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 44);
  row++;

  sheet.getRange(row, 1, 1, numCols).merge().setBackground(lightColor);
  sheet.getRange(row, 1)
    .setValue("  " + subtitle + "  •  Confiance : " + confidence)
    .setFontSize(10).setFontColor(mainColor).setFontStyle("italic")
    .setVerticalAlignment("middle");
  sheet.setRowHeight(row, 28);
  row++;

  if (ticket.combos.length === 0) {
    sheet.getRange(row, 1, 1, numCols).merge().setBackground(bgColor);
    sheet.getRange(row, 1)
      .setValue("  ⏳ Pas assez de matchs analysés pour générer ce ticket")
      .setFontSize(11).setFontColor(C.textLight).setFontStyle("italic")
      .setVerticalAlignment("middle");
    sheet.setRowHeight(row, 36);
    return row + 1;
  }

  var headers = ["Ligue", "Match", "Sélections combinées", "Cote match", "Proba match", "Conf.", "Value", "Heure", ""];
  sheet.getRange(row, 1, 1, numCols).setValues([headers]);
  sheet.getRange(row, 1, 1, numCols)
    .setFontWeight("bold").setFontColor(C.white).setBackground(borderColor)
    .setFontSize(10).setHorizontalAlignment("center").setVerticalAlignment("middle");
  sheet.setRowHeight(row, 30);
  row++;

  for (var i = 0; i < ticket.combos.length; i++) {
    var combo = ticket.combos[i];
    var rowBg = (i % 2 === 0) ? bgColor : C.white;

    var selectionsStr = "";
    for (var s = 0; s < combo.selections.length; s++) {
      if (s > 0) selectionsStr += "  +  ";
      selectionsStr += combo.selections[s].betLabel;
    }
    var valueCount = 0;
    for (var s = 0; s < combo.selections.length; s++) {
      if (combo.selections[s].isValue) valueCount++;
    }

    sheet.getRange(row, 1, 1, numCols).setValues([[
      combo.league, combo.matchLabel, selectionsStr,
      combo.comboOdds.toFixed(2), combo.comboProba + "%",
      combo.confidence + "/10",
      valueCount > 0 ? valueCount + " VALUE" : "—",
      combo.time, ""
    ]]);
    sheet.getRange(row, 1, 1, numCols).setBackground(rowBg).setFontSize(10)
      .setVerticalAlignment("middle");

    sheet.getRange(row, 1).setFontSize(9);
    sheet.getRange(row, 2).setFontWeight("bold").setFontSize(10);
    sheet.getRange(row, 3).setFontWeight("bold").setFontColor(mainColor).setWrap(true);
    sheet.getRange(row, 4).setHorizontalAlignment("center").setFontWeight("bold").setFontSize(12).setFontColor(C.blueTx);
    sheet.getRange(row, 5).setHorizontalAlignment("center").setFontWeight("bold");
    sheet.getRange(row, 6).setHorizontalAlignment("center");
    sheet.getRange(row, 7).setHorizontalAlignment("center").setFontWeight("bold");
    sheet.getRange(row, 8).setHorizontalAlignment("center").setFontColor(C.textLight);

    var probaCell = sheet.getRange(row, 5);
    if      (combo.comboProba >= 40) { probaCell.setBackground(C.greenBg).setFontColor(C.greenTx); }
    else if (combo.comboProba >= 25) { probaCell.setBackground(C.yellowBg).setFontColor(C.yellowTx); }
    else if (combo.comboProba >= 10) { probaCell.setBackground(C.orangeBg).setFontColor(C.orangeTx); }
    else                             { probaCell.setBackground(C.redBg).setFontColor(C.redTx); }

    if (valueCount > 0) {
      sheet.getRange(row, 7).setFontColor(C.greenTx).setBackground(C.greenBg);
    } else {
      sheet.getRange(row, 7).setFontColor(C.textLight);
    }

    sheet.setRowHeight(row, 34);
    row++;

    var detailParts = [];
    for (var s = 0; s < combo.selections.length; s++) {
      var sel = combo.selections[s];
      detailParts.push(sel.betLabel + " @ " + sel.odds.toFixed(2) + " (" + sel.proba + "%)");
    }
    sheet.getRange(row, 1, 1, numCols).setBackground(rowBg);
    sheet.getRange(row, 2, 1, 7).merge();
    sheet.getRange(row, 2)
      .setValue("    ↳ " + detailParts.join("   •   "))
      .setFontSize(8).setFontColor(C.textLight).setFontStyle("italic")
      .setVerticalAlignment("middle").setWrap(true);
    sheet.setRowHeight(row, 24);
    row++;
  }

  // ── Résumé ─────────────────────────────────────────────────────
  sheet.getRange(row, 1, 1, numCols).setBackground(lightColor);
  sheet.getRange(row, 1, 1, 2).merge();
  sheet.getRange(row, 1)
    .setValue("  📊 TOTAL DU TICKET (" + ticket.combos.length + " matchs)")
    .setFontWeight("bold").setFontSize(11).setFontColor(mainColor)
    .setVerticalAlignment("middle");

  sheet.getRange(row, 3)
    .setValue("Cote combinée →")
    .setFontWeight("bold").setFontSize(10).setFontColor(C.textDark)
    .setHorizontalAlignment("right").setVerticalAlignment("middle");

  sheet.getRange(row, 4)
    .setValue(ticket.combinedOdds.toFixed(2))
    .setFontWeight("bold").setFontSize(14).setFontColor(mainColor)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");

  sheet.getRange(row, 5)
    .setValue(ticket.combinedProba + "%")
    .setFontWeight("bold").setFontSize(11).setFontColor(mainColor)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");

  sheet.getRange(row, 6).setValue("");

  sheet.getRange(row, 7, 1, 2).merge();
  sheet.getRange(row, 7)
    .setValue("💰 10€ → " + (ticket.combinedOdds * 10).toFixed(2) + "€")
    .setFontWeight("bold").setFontSize(12).setFontColor(C.goldTx)
    .setHorizontalAlignment("center").setVerticalAlignment("middle");

  sheet.setRowHeight(row, 42);
  row++;

  return row;
}


// ── SAUVEGARDE DES TICKETS EN SUPABASE ────────────────────────
function saveTicketsToSupabase_(safeTicket, funTicket, jackpotTicket, targetDate, todayMatches) {
  // Construire un map matchId → fixture pour récupérer la date
  var matchDateMap = {};
  for (var i = 0; i < todayMatches.length; i++) {
    var m = todayMatches[i];
    matchDateMap[m.fixture.id] = m.fixture.date;
  }

  var tickets = [
    { type: "SAFE",    ticket: safeTicket },
    { type: "FUN",     ticket: funTicket },
    { type: "JACKPOT", ticket: jackpotTicket }
  ];

  var records = [];

  for (var t = 0; t < tickets.length; t++) {
    var tType  = tickets[t].type;
    var tData  = tickets[t].ticket;

    for (var c = 0; c < tData.combos.length; c++) {
      var combo = tData.combos[c];
      var matchParts = combo.matchLabel.split(" vs ");
      var homeTeam = matchParts[0] ? matchParts[0].trim() : "?";
      var awayTeam = matchParts.length > 1 ? matchParts[1].trim() : "?";
      var matchDate = matchDateMap[combo.matchId] || null;

      for (var s = 0; s < combo.selections.length; s++) {
        var sel = combo.selections[s];
        records.push({
          ticket_type: tType,
          ticket_date: targetDate,
          fixture_id:  combo.matchId,
          home_team:   homeTeam,
          away_team:   awayTeam,
          match_date:  matchDate,
          bet_type:    sel.betLabel,
          confidence:  Math.round(sel.proba),
          odds_est:    sel.odds
        });
      }
    }
  }

  // Upsert par lots de 20
  for (var i = 0; i < records.length; i += 20) {
    var batch = records.slice(i, i + 20);
    try {
      supabaseUpsert_("ticket_picks", batch, "ticket_type,ticket_date,fixture_id,bet_type");
    } catch (e) {
      // En cas d'erreur, essayer un par un
      for (var j = 0; j < batch.length; j++) {
        try {
          supabaseUpsert_("ticket_picks", batch[j], "ticket_type,ticket_date,fixture_id,bet_type");
        } catch (e2) { /* skip */ }
      }
    }
  }
}
