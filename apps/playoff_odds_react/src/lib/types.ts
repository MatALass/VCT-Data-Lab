export type Positions = Record<string, number>;
export interface MatchResult { group: string; match: string; result: string; winner?: string; }
export interface FinalStandingRow { rank: number; team: string; wins?: number; losses?: number; mapDiff?: number; roundDiff?: number; qualifyProb?: number; }
export interface ScenarioRecord { wins?: number; losses?: number; mapDiff?: number; roundDiff?: number; mapProfile?: string; roundProfile?: string; }
export interface ScenarioCase { kind: string; finalRank: number; finalRecord?: ScenarioRecord; matchResults: MatchResult[]; finalStandings: FinalStandingRow[]; note?: string; }
export interface ScenarioExtremes { bestCase?: ScenarioCase | null; worstCase?: ScenarioCase | null; }
export interface ScenarioPathMatch { match: string; winner: string; loser: string; }
export interface ScenarioPath { share: number; matches: ScenarioPathMatch[]; }
export interface ExactWinnerOnlyBounds { best: number; worst: number; }
export interface TeamData { team: string; qualifyProb: number; bestRankSeen: number; worstRankSeen: number; expectedRank?: number; positions: Positions; scenarioExtremes?: ScenarioExtremes; topQualificationPaths?: ScenarioPath[]; topEliminationPaths?: ScenarioPath[]; exactWinnerOnlyBounds?: ExactWinnerOnlyBounds; }
export interface GroupData { name: string; teams: TeamData[]; }
export interface TeamImpact { team: string; ifTeamAWins: number; ifTeamBWins: number; }
export interface MatchImpactItem { match: string; importance: number; teamImpacts: TeamImpact[]; }
export interface KeyMatchItem { group: string; match: string; importance: number; headline: string; }
export interface RemainingMatch { group: string; teamA: string; teamB: string; }
export interface DatasetNotes { method?: string; tiebreakApproximation?: string[]; officialTieBreakers?: string[]; sampleSize?: number; conditionalSampleSize?: number; scenarioExtremes?: string; exactWinnerOnlyBounds?: string; bundledSample?: boolean; analysisFeatures?: string[]; modelType?: string; whatIfMode?: string; }
export interface Dataset { league: string; season: string; qualificationSlots: number; groups: GroupData[]; remainingMatches?: RemainingMatch[]; matchImpacts?: Record<string, MatchImpactItem[]>; keyMatches?: KeyMatchItem[]; insights?: string[]; notes?: DatasetNotes; }
export interface TeamViewModel extends TeamData { group: string; expectedRankDerived: number; status: string; tone: "lock" | "veryLikely" | "favourable" | "bubble" | "outsider" | "nearlyOut"; }
