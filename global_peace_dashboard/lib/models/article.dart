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
}