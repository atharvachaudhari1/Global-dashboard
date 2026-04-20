import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/article.dart';
import '../services/api_service.dart';
import '../config/config.dart';

class NewsProvider extends ChangeNotifier {
  List<Article> _articles = [];
  String _activeSource = 'gdelt';
  String _filter = 'all';
  String _searchQuery = '';
  String? _selectedCountry;
  bool _isLoading = false;
  DateTime? _lastUpdated;
  Timer? _refreshTimer;
  int _countdown = 60;

  List<Article> get articles => _filteredArticles;
  bool get isLoading => _isLoading;
  DateTime? get lastUpdated => _lastUpdated;
  int get countdown => _countdown;
  String get activeSource => _activeSource;
  String get filter => _filter;
  String? get selectedCountry => _selectedCountry;

  double get globalPeaceIndex {
    if (_articles.isEmpty) return 0;
    return double.parse((_articles.map((a) => a.score).reduce((a, b) => a + b) / _articles.length).toStringAsFixed(1));
  }

  int get totalArticles => _articles.length;

  int get conflictCount => _articles.where((a) => a.cls == 'conflict').length;

  int get peaceCount => _articles.where((a) => a.cls == 'peace').length;

  int get neutralCount => _articles.where((a) => a.cls == 'neutral').length;

  List<Article> get _filteredArticles {
    var result = List<Article>.from(_articles);
    if (_selectedCountry != null) {
      result = result.where((a) => a.country == _selectedCountry).toList();
    }
    if (_filter != 'all') {
      result = result.where((a) => a.cls == _filter).toList();
    }
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      result = result.where((a) =>
        a.title.toLowerCase().contains(q) ||
        a.source.toLowerCase().contains(q)
      ).toList();
    }
    return result;
  }

  Future<void> fetchNews() async {
    _isLoading = true;
    notifyListeners();

    try {
      if (_activeSource == 'all') {
        _articles = await ApiService.fetchFromAll();
      } else if (_activeSource == 'gdelt') {
        _articles = await ApiService.fetchFromGdelt();
      } else {
        _articles = await ApiService.fetchFromRss();
      }
      _lastUpdated = DateTime.now();
    } catch (e) {
      _articles = [];
    }

    _isLoading = false;
    notifyListeners();
  }

  void setSource(String source) {
    _activeSource = source;
    fetchNews();
  }

  void setFilter(String filter) {
    _filter = filter;
    notifyListeners();
  }

  void setSearch(String query) {
    _searchQuery = query;
    notifyListeners();
  }

  void setCountry(String? country) {
    _selectedCountry = country;
    notifyListeners();
  }

  void startAutoRefresh() {
    _refreshTimer?.cancel();
    _refreshTimer = Timer.periodic(
      Duration(milliseconds: AppConfig.refreshInterval),
      (_) => fetchNews(),
    );
  }

  void startCountdown() {
    _countdown = AppConfig.refreshInterval ~/ 1000;
    Timer.periodic(const Duration(seconds: 1), (timer) {
      _countdown--;
      notifyListeners();
      if (_countdown <= 0) {
        timer.cancel();
        fetchNews();
        startCountdown();
      }
    });
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}