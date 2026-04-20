import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/article.dart';
import 'peace_score_service.dart';
import '../config/config.dart';

class ApiService {
  static Future<List<Article>> fetchFromGdelt() async {
    try {
      final query = 'peace OR conflict OR war OR protest OR ceasefire OR diplomacy';
      final url = '${AppConfig.apis['gdelt']!.url}?query=$query&mode=ArtList&maxrecords=50&format=json&sourcelang=english&timespan=1month';
      final res = await http.get(Uri.parse(url));
      if (res.statusCode != 200) throw Exception('GDELT failed');
      
      final data = json.decode(res.body);
      final articles = data['articles'] as List? ?? [];
      return articles.map((a) => _parseArticle(a as Map<String, dynamic>, 'GDELT')).toList();
    } catch (e) {
      return _fallbackArticles();
    }
  }

  static Future<List<Article>> fetchFromRss() async {
    final rssConfig = AppConfig.apis['rss']!;
    final results = <Article>[];
    
    for (var feed in rssConfig.feeds ?? []) {
      try {
        final url = 'https://api.rss2json.com/v1/api.json?rss_url=${feed['url']}';
        final res = await http.get(Uri.parse(url));
        if (res.statusCode != 200) continue;
        
        final data = json.decode(res.body);
        final items = data['items'] as List? ?? [];
        for (var item in items.take(5)) {
          results.add(_parseArticle(item as Map<String, dynamic>, feed['name']!));
        }
      } catch (_) {
        continue;
      }
    }
    
    return results.isEmpty ? _fallbackArticles() : results;
  }

  static Future<List<Article>> fetchFromAll() async {
    final results = await Future.wait([
      fetchFromGdelt(),
      fetchFromRss(),
    ]);
    final combined = [...results[0], ...results[1]];
    
    final dedup = <String, Article>{};
    for (var a in combined) {
      final key = a.title.toLowerCase().trim();
      if (key.isNotEmpty && !dedup.containsKey(key)) {
        dedup[key] = a;
      }
    }
    
    return dedup.values.toList();
  }

  static Article _parseArticle(Map<String, dynamic> json, String apiSource) {
    final title = json['title']?.toString() ?? '';
    final description = json['description']?.toString() ?? '';
    final score = PeaceScoreService.calculateScore(title, description);
    final classification = PeaceScoreService.classifyScore(score);
    
    return Article(
      title: title,
      description: description,
      source: json['source']?.toString() ?? json['author']?.toString() ?? apiSource,
      country: _detectCountry(title),
      pubDate: _parseDate(json['pubDate']?.toString() ?? json['publishedAt']?.toString() ?? ''),
      link: json['url']?.toString() ?? json['link']?.toString() ?? '#',
      apiSource: apiSource,
      score: score,
      category: classification['category']!,
      color: classification['color']!,
      cls: classification['cls']!,
    );
  }

  static String _detectCountry(String text) {
    final t = text.toLowerCase();
    final map = <String, String>{
      'ukraine': 'ua', 'russia': 'ru', 'israel': 'il', 'gaza': 'ps', 'palestine': 'ps',
      'iran': 'ir', 'iraq': 'iq', 'syria': 'sy', 'yemen': 'ye', 'afghanistan': 'af',
      'china': 'cn', 'india': 'in', 'pakistan': 'pk', 'myanmar': 'mm', 'sudan': 'sd',
      'ethiopia': 'et', 'nigeria': 'ng', 'libya': 'ly', 'somalia': 'so', 'lebanon': 'lb',
      'usa': 'us', 'united states': 'us', 'america': 'us', 'uk': 'gb', 'britain': 'gb',
      'france': 'fr', 'germany': 'de', 'australia': 'au', 'canada': 'ca', 'japan': 'jp'
    };
    for (var entry in map.entries) {
      if (t.contains(entry.key)) return entry.value;
    }
    return 'us';
  }

  static DateTime _parseDate(String dateStr) {
    if (dateStr.isEmpty) return DateTime.now();
    return DateTime.tryParse(dateStr) ?? DateTime.now();
  }

  static List<Article> _fallbackArticles() {
    final samples = <Map<String, String>>[
      {'title': 'UN brokered ceasefire holds for third consecutive day in conflict region', 'description': 'Peace talks continue as diplomatic efforts show positive results', 'source': 'Reuters'},
      {'title': 'Missile strikes and artillery fire reported overnight killing dozens', 'description': 'Armed conflict escalates as international community condemns attacks', 'source': 'BBC'},
      {'title': 'G20 summit opens focusing on global economic cooperation and development', 'description': 'World leaders gather to discuss trade and climate', 'source': 'Al Jazeera'},
      {'title': 'Humanitarian aid convoy finally reaches conflict zone after negotiations', 'description': 'Relief organizations deliver food and medicine to displaced people', 'source': 'Guardian'},
    ];
    return samples.map((s) => _parseArticle(s, 'Sample')).toList();
  }
}