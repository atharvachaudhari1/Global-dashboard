class AppConfig {
  static const String activeSource = 'gdelt';
  static const int refreshInterval = 60000;
  static const bool autoFallback = true;

  static const Map<String, ApiConfig> apis = {
    'gdelt': ApiConfig(
      name: 'GDELT',
      url: 'https://api.gdeltproject.org/api/v2/docact',
      enabled: true,
    ),
    'rss': ApiConfig(
      name: 'RSS Mix',
      url: '',
      enabled: true,
      feeds: [
        {'name': 'Reuters', 'url': 'https://feeds.reuters.com/news/worldnews'},
        {'name': 'BBC', 'url': 'https://feeds.bbci.co.uk/news/world/rss.xml'},
      ],
    ),
    'newsdata': ApiConfig(
      name: 'NewsData.io',
      url: 'https://newsdata.io/api/1/news',
      key: 'YOUR_NEWSdata_API_KEY',
      enabled: false,
    ),
    'gnews': ApiConfig(
      name: 'GNews',
      url: 'https://gnews.io/api/v4/top-headlines',
      key: 'YOUR_GNEWS_API_KEY',
      enabled: false,
    ),
    'newsapi': ApiConfig(
      name: 'NewsAPI',
      url: 'https://newsapi.org/v2/top-headlines',
      key: 'YOUR_NEWSAPI_KEY',
      enabled: false,
    ),
    'guardian': ApiConfig(
      name: 'The Guardian',
      url: 'https://content.guardianapis.com/search',
      key: 'YOUR_GUARDIAN_API_KEY',
      enabled: false,
    ),
    'mediastack': ApiConfig(
      name: 'Mediastack',
      url: 'https://api.mediastack.com/v1/news',
      key: 'YOUR_MEDIASTACK_API_KEY',
      enabled: false,
    ),
    'currents': ApiConfig(
      name: 'Currents',
      url: 'https://api.currentsapi.services/v1/latest',
      key: 'YOUR_CURRENTS_API_KEY',
      enabled: false,
    ),
  };
}

class ApiConfig {
  final String name;
  final String url;
  final String key;
  final bool enabled;
  final List<Map<String, String>>? feeds;

  const ApiConfig({
    required this.name,
    required this.url,
    this.key = '',
    this.enabled = false,
    this.feeds,
  });
}