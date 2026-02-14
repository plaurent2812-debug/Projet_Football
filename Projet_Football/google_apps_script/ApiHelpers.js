// ================================================================
//  ⚽ FOOTBALL IA — Helpers API (Supabase, API-Football, Anthropic)
// ================================================================

// ── SUPABASE REST API ────────────────────────────────────────────
function supabaseRequest_(method, table, options) {
  options = options || {};
  var config = getConfig_();
  var url = config.supabaseUrl + "/rest/v1/" + table;
  if (options.query) url += "?" + options.query;

  var fetchOpts = {
    method: method,
    headers: {
      "apikey":        config.supabaseKey,
      "Authorization": "Bearer " + config.supabaseKey,
      "Content-Type":  "application/json",
      "Prefer":        options.prefer || "return=minimal"
    },
    muteHttpExceptions: true
  };
  if (options.body) fetchOpts.payload = JSON.stringify(options.body);

  var resp = UrlFetchApp.fetch(url, fetchOpts);
  var text = resp.getContentText();
  if (!text || text === "") return [];
  return JSON.parse(text);
}

function supabaseSelect_(table, query) {
  return supabaseRequest_("GET", table, { query: query });
}

function supabaseUpsert_(table, data, onConflict) {
  return supabaseRequest_("POST", table, {
    body: data,
    query: "on_conflict=" + onConflict,
    prefer: "resolution=merge-duplicates,return=minimal"
  });
}

function supabaseInsert_(table, data) {
  return supabaseRequest_("POST", table, { body: data });
}

// ── API-FOOTBALL ─────────────────────────────────────────────────
function fetchApiFootball_(endpoint, params) {
  var config = getConfig_();
  var qs = Object.keys(params).map(function(k) { return k + "=" + params[k]; }).join("&");
  var url = "https://v3.football.api-sports.io/" + endpoint + "?" + qs;

  var resp = UrlFetchApp.fetch(url, {
    headers: {
      "x-rapidapi-host": "v3.football.api-sports.io",
      "x-rapidapi-key":  config.apiFootballKey
    },
    muteHttpExceptions: true
  });
  return JSON.parse(resp.getContentText());
}

// ── EFFECTIFS POUR LE PROMPT IA ──────────────────────────────────
function getSquadForPrompt_(homeTeam, awayTeam) {
  var homeTeamData = supabaseSelect_("teams", "name=eq." + encodeURIComponent(homeTeam) + "&select=api_id");
  var awayTeamData = supabaseSelect_("teams", "name=eq." + encodeURIComponent(awayTeam) + "&select=api_id");

  if (!homeTeamData.length || !awayTeamData.length) return "";

  var homeId = homeTeamData[0].api_id;
  var awayId = awayTeamData[0].api_id;

  var homePlayers = supabaseSelect_("players", "team_api_id=eq." + homeId + "&select=api_id,name,position,is_injured");
  var awayPlayers = supabaseSelect_("players", "team_api_id=eq." + awayId + "&select=api_id,name,position,is_injured");

  var homeStats = supabaseSelect_("player_season_stats", "team_api_id=eq." + homeId + "&season=eq." + SEASON + "&select=player_api_id,goals,assists,appearances,minutes_played,penalty_scored");
  var awayStats = supabaseSelect_("player_season_stats", "team_api_id=eq." + awayId + "&season=eq." + SEASON + "&select=player_api_id,goals,assists,appearances,minutes_played,penalty_scored");

  function formatTeam(players, stats, teamName) {
    var statsMap = {};
    for (var i = 0; i < stats.length; i++) {
      var s = stats[i];
      var pid = s.player_api_id;
      if (!statsMap[pid]) {
        statsMap[pid] = { goals: 0, assists: 0, apps: 0, mins: 0, pen: 0 };
      }
      statsMap[pid].goals  += (s.goals || 0);
      statsMap[pid].assists += (s.assists || 0);
      statsMap[pid].apps   += (s.appearances || 0);
      statsMap[pid].mins   += (s.minutes_played || 0);
      statsMap[pid].pen    += (s.penalty_scored || 0);
    }

    var list = [];
    for (var i = 0; i < players.length; i++) {
      var p = players[i];
      if (p.position === "Goalkeeper") continue;
      var st = statsMap[p.api_id] || { goals: 0, assists: 0, apps: 0, mins: 0, pen: 0 };
      if (st.mins < 45) continue;
      list.push({
        name: p.name,
        pos: p.position === "Attacker" ? "ATT" : (p.position === "Midfielder" ? "MIL" : "DEF"),
        goals: st.goals, assists: st.assists, apps: st.apps, pen: st.pen,
        injured: p.is_injured
      });
    }

    list.sort(function(a, b) { return (b.goals * 10 + b.assists * 3) - (a.goals * 10 + a.assists * 3); });
    list = list.slice(0, 12);

    var lines = [teamName + " :"];
    for (var i = 0; i < list.length; i++) {
      var p = list[i];
      var line = "- " + p.name + " (" + p.pos + ") " + p.goals + "G " + p.assists + "A en " + p.apps + " matchs";
      if (p.pen > 0) line += " (tireur penalty)";
      if (p.injured) line += " ⚠️BLESSÉ";
      lines.push(line);
    }
    return lines.join("\n");
  }

  return formatTeam(homePlayers, homeStats, homeTeam) + "\n\n" + formatTeam(awayPlayers, awayStats, awayTeam);
}

// ── ANTHROPIC (Claude) ───────────────────────────────────────────
function callAnthropic_(fixture, leagueName, config) {
  var squadInfo = getSquadForPrompt_(fixture.home_team, fixture.away_team);

  var systemPrompt =
    "Tu es un expert mondial en paris sportifs, modélisation statistique de football et analyse de buteurs.\n" +
    "IMPORTANT : Réponds UNIQUEMENT avec un objet JSON valide. Pas de texte, pas de commentaire, pas de bloc markdown, juste le JSON brut.\n" +
    'Structure exacte :\n' +
    '{"proba_home": 55, "proba_draw": 25, "proba_away": 20, "proba_btts": 50, ' +
    '"proba_over_05": 92, "proba_over_15": 75, "proba_over_2_5": 55, "proba_over_35": 30, ' +
    '"analysis_text": "Ton analyse ici.", "recommended_bet": "Victoire Domicile", "confidence_score": 6, ' +
    '"top_scorers": [' +
    '{"name": "Nom Joueur", "team": "Equipe", "proba": 25, "position": "Attaquant", "analysis": "Raisons courtes du choix"}, ' +
    '{"name": "Nom Joueur 2", "team": "Equipe", "proba": 18, "position": "Attaquant", "analysis": "Raisons courtes"}, ' +
    '{"name": "Nom Joueur 3", "team": "Equipe", "proba": 12, "position": "Milieu", "analysis": "Raisons courtes"}' +
    ']}';

  var userPrompt =
    "Analyse ce match de " + leagueName + " prévu le " + fixture.date + " :\n" +
    "Domicile : " + fixture.home_team + "\n" +
    "Extérieur : " + fixture.away_team + "\n\n" +
    "Base-toi sur la réputation historique, la forme supposée et l'avantage du terrain. Sois réaliste.\n\n";

  if (squadInfo) {
    userPrompt +=
      "EFFECTIFS ACTUELS (saison 2025-2026, données réelles issues de la base) :\n" +
      squadInfo + "\n\n" +
      "ATTENTION : Utilise UNIQUEMENT les joueurs listés ci-dessus. Ne propose JAMAIS un joueur absent de cette liste.\n\n";
  }

  userPrompt +=
    "Pour les top_scorers (3 buteurs les plus probables du match, des 2 équipes confondues) :\n" +
    "- Choisis parmi les joueurs listés ci-dessus (saison 2025-2026)\n" +
    "- Proba = probabilité que ce joueur marque au moins 1 but dans ce match (entre 5% et 45%)\n" +
    "- Position : Attaquant, Milieu ou Défenseur\n" +
    "- Analysis : courte explication (buts/90, forme, tireur de penalty, historique vs adversaire, etc.)\n" +
    "- Privilégie les meilleurs buteurs actuels de chaque équipe, la forme récente";

  var resp = UrlFetchApp.fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "x-api-key":          config.anthropicKey,
      "anthropic-version":  "2023-06-01",
      "Content-Type":       "application/json"
    },
    payload: JSON.stringify({
      model:       ANTHROPIC_MODEL,
      max_tokens:  1500,
      temperature: 0.2,
      system:      systemPrompt,
      messages:    [{ role: "user", content: userPrompt }]
    }),
    muteHttpExceptions: true
  });

  var result = JSON.parse(resp.getContentText());
  if (result.error) throw new Error(result.error.message);

  var raw = result.content[0].text;

  // Extraction robuste du JSON
  try { return JSON.parse(raw); } catch (_) {}
  var m = raw.match(/```(?:json)?\s*\n?([\s\S]*?)\n?```/);
  if (m) try { return JSON.parse(m[1].trim()); } catch (_) {}
  m = raw.match(/\{[\s\S]*\}/);
  if (m) try { return JSON.parse(m[0]); } catch (_) {}
  return null;
}
