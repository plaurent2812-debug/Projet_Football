// ================================================================
//  ⚽ FOOTBALL IA — Import des matchs (API-Football → Supabase)
// ================================================================

function importMatches() {
  var config = checkConfig_();
  if (!config) return;

  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ss.toast("Import en cours…", "📥 Football IA", -1);
  var total = 0;

  for (var i = 0; i < LEAGUES.length; i++) {
    var league = LEAGUES[i];
    try {
      var data = fetchApiFootball_("fixtures", { league: league.id, season: SEASON, next: 20 });
      if (!data.response || data.response.length === 0) {
        ss.toast(league.flag + " " + league.name + " : aucun match", "📥", 2);
        continue;
      }

      // Grouper par journée, garder la première (la plus proche)
      var byRound = {};
      var roundOrder = [];
      for (var j = 0; j < data.response.length; j++) {
        var roundName = data.response[j].league.round;
        if (!byRound[roundName]) { byRound[roundName] = []; roundOrder.push(roundName); }
        byRound[roundName].push(data.response[j]);
      }
      var firstRound = roundOrder[0];
      var fixtures = byRound[firstRound];

      // Upsert ligue
      supabaseUpsert_("leagues", {
        api_id:  league.id,
        name:    fixtures[0].league.name,
        country: fixtures[0].league.country,
        season:  fixtures[0].league.season
      }, "api_id");

      // Upsert matchs en batch
      var batch = [];
      for (var k = 0; k < fixtures.length; k++) {
        var item = fixtures[k];
        batch.push({
          api_fixture_id: item.fixture.id,
          date:           item.fixture.date,
          league_id:      league.id,
          home_team:      item.teams.home.name,
          away_team:      item.teams.away.name,
          status:         item.fixture.status.short,
          home_goals:     item.goals.home,
          away_goals:     item.goals.away,
          stats_json:     { venue: item.fixture.venue, status_short: item.fixture.status.short, round: firstRound }
        });
      }
      supabaseUpsert_("fixtures", batch, "api_fixture_id");
      total += fixtures.length;

      ss.toast(league.flag + " " + league.name + " : " + fixtures.length + " matchs (" + firstRound + ")", "📥", 3);
    } catch (e) {
      ss.toast("❌ " + league.name + " : " + e.message, "Erreur", 5);
    }
  }

  ss.toast("✅ " + total + " matchs importés !", "📥 Football IA", 5);
}
