class PeaceScoreService {
  static const List<String> conflictKeywords = [
    'war', 'attack', 'bomb', 'explosion', 'killed', 'dead', 'death', 'missile',
    'airstrike', 'shooting', 'violence', 'riot', 'clash', 'conflict', 'fighting',
    'troops', 'invasion', 'coup', 'protest', 'unrest', 'crisis', 'hostage',
    'terror', 'terrorist', 'genocide', 'massacre', 'casualties', 'wounded',
    'destroyed', 'refugee', 'siege', 'blockade', 'sanctions', 'nuclear',
    'chemical weapon', 'ethnic cleansing', 'displacement', 'insurgency',
    'militant', 'gunfire', 'shelling', 'artillery', 'drone strike', 'ambush',
    'kidnapping', 'execution', 'torture', 'war crime', 'famine', 'starvation'
  ];

  static const List<String> peaceKeywords = [
    'peace', 'ceasefire', 'agreement', 'treaty', 'diplomacy', 'talks',
    'negotiation', 'cooperation', 'aid', 'relief', 'reconstruction',
    'democracy', 'election', 'vote', 'freedom', 'human rights',
    'development', 'trade', 'partnership', 'alliance', 'reconciliation',
    'dialogue', 'humanitarian', 'donation', 'recovery', 'stability',
    'truce', 'resolution', 'accord', 'summit', 'bilateral', 'multilateral',
    'diplomatic', 'mediation', 'peacekeeping', 'solidarity', 'reform'
  ];

  static double calculateScore(String title, String description) {
    final text = '${title ?? ''} ${description ?? ''}'.toLowerCase();
    double score = 5.0;

    int conflictCount = 0;
    for (var kw in conflictKeywords) {
      if (text.contains(kw)) conflictCount++;
    }
    score -= (conflictCount * 0.4).clamp(0.0, 4.5);

    int peaceCount = 0;
    for (var kw in peaceKeywords) {
      if (text.contains(kw)) peaceCount++;
    }
    score += (peaceCount * 0.35).clamp(0.0, 4.0);

    final titleLower = (title ?? '').toLowerCase();
    for (var kw in conflictKeywords) {
      if (titleLower.contains(kw)) {
        score -= 0.5;
        break;
      }
    }
    for (var kw in peaceKeywords) {
      if (titleLower.contains(kw)) {
        score += 0.5;
        break;
      }
    }

    return double.parse((score.clamp(0.1, 9.9)).toStringAsFixed(1));
  }

  static Map<String, String> classifyScore(double score) {
    if (score >= 6.5) {
      return {'category': 'PEACE', 'color': '#1D9E75', 'cls': 'peace'};
    } else if (score >= 4.0) {
      return {'category': 'NEUTRAL', 'color': '#888888', 'cls': 'neutral'};
    } else {
      return {'category': 'CONFLICT', 'color': '#E24B4A', 'cls': 'conflict'};
    }
  }
}