import { useParams } from 'react-router-dom';
import type { FixtureId } from '../../types/v2/common';

export default function MatchDetailV2() {
  const { fixtureId } = useParams<{ fixtureId: FixtureId }>();
  return (
    <main aria-label="Match detail V2">
      <h1>MatchDetailV2 WIP</h1>
      <p>fixture: {fixtureId}</p>
    </main>
  );
}
