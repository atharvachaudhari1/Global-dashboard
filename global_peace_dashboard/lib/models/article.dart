class Article {
  final String title;
  final String description;
  final String source;
  final String country;
  final DateTime pubDate;
  final String link;
  final String apiSource;
  final double score;
  final String category;
  final String color;
  final String cls;

  Article({
    required this.title,
    required this.description,
    required this.source,
    required this.country,
    required this.pubDate,
    required this.link,
    required this.apiSource,
    required this.score,
    required this.category,
    required this.color,
    required this.cls,
  });

  factory Article.fromJson(Map<String, dynamic> json, double score, String category, String color, String cls) {
    return Article(
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      source: json['source'] ?? '',
      country: json['country'] ?? 'us',
      pubDate: DateTime.tryParse(json['pubDate'] ?? '') ?? DateTime.now(),
      link: json['link'] ?? '#',
      apiSource: json['apiSource'] ?? '',
      score: score,
      category: category,
      color: color,
      cls: cls,
    );
  }

  Map<String, dynamic> toMap() {
    return {
      'id': '${title.toLowerCase().trim()}|${link.toLowerCase().trim()}',
      'title': title,
      'description': description,
      'source': source,
      'country': country,
      'pubDate': pubDate.toIso8601String(),
      'link': link,
      'apiSource': apiSource,
      'score': score,
      'category': category,
      'color': color,
      'cls': cls,
      'cachedAt': DateTime.now().toIso8601String(),
    };
  }

  factory Article.fromMap(Map<String, dynamic> map) {
    return Article(
      title: map['title']?.toString() ?? '',
      description: map['description']?.toString() ?? '',
      source: map['source']?.toString() ?? '',
      country: map['country']?.toString() ?? 'us',
      pubDate: DateTime.tryParse(map['pubDate']?.toString() ?? '') ?? DateTime.now(),
      link: map['link']?.toString() ?? '#',
      apiSource: map['apiSource']?.toString() ?? '',
      score: (map['score'] is num) ? (map['score'] as num).toDouble() : 5.0,
      category: map['category']?.toString() ?? 'NEUTRAL',
      color: map['color']?.toString() ?? '#888888',
      cls: map['cls']?.toString() ?? 'neutral',
    );
  }
}