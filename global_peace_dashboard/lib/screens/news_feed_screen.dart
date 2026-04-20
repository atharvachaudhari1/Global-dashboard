import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/news_provider.dart';
import '../widgets/article_card.dart';

class NewsFeedScreen extends StatefulWidget {
  const NewsFeedScreen({super.key});

  @override
  State<NewsFeedScreen> createState() => _NewsFeedScreenState();
}

class _NewsFeedScreenState extends State<NewsFeedScreen> {
  final TextEditingController _searchController = TextEditingController();

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Consumer<NewsProvider>(
      builder: (context, provider, _) {
        return Column(
          children: [
            Padding(
              padding: const EdgeInsets.all(12),
              child: TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  hintText: 'Search articles...',
                  prefixIcon: const Icon(Icons.search),
                  suffixIcon: _searchController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear),
                          onPressed: () {
                            _searchController.clear();
                            provider.setSearch('');
                          },
                        )
                      : null,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                  filled: true,
                ),
                onChanged: (value) => provider.setSearch(value),
              ),
            ),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Row(
                children: [
                  _buildFilterChip(context, 'all', 'All', provider),
                  _buildFilterChip(context, 'peace', 'Peace', provider),
                  _buildFilterChip(context, 'neutral', 'Neutral', provider),
                  _buildFilterChip(context, 'conflict', 'Conflict', provider),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: provider.isLoading
                  ? const Center(child: CircularProgressIndicator())
                  : provider.articles.isEmpty
                      ? _buildEmptyState()
                      : RefreshIndicator(
                          onRefresh: () => provider.fetchNews(),
                          child: ListView.builder(
                            itemCount: provider.articles.length,
                            itemBuilder: (context, index) {
                              final article = provider.articles[index];
                              return ArticleCard(
                                article: article,
                                onTap: () => _openArticle(context, article.link),
                              );
                            },
                          ),
                        ),
            ),
          ],
        );
      },
    );
  }

  Widget _buildFilterChip(BuildContext context, String filter, String label, NewsProvider provider) {
    final isActive = provider.filter == filter;
    final color = filter == 'peace'
        ? const Color(0xFF1D9E75)
        : filter == 'conflict'
            ? const Color(0xFFE24B4A)
            : Colors.grey;
    
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: FilterChip(
        label: Text(label),
        selected: isActive,
        onSelected: (_) => provider.setFilter(filter),
        selectedColor: color.withOpacity(0.2),
        checkmarkColor: color,
        labelStyle: TextStyle(
          color: isActive ? color : null,
          fontWeight: isActive ? FontWeight.bold : null,
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.article_outlined, size: 48, color: Colors.grey),
          SizedBox(height: 16),
          Text('No articles match your filter'),
          SizedBox(height: 8),
          Text(
            'Try changing the source or filter',
            style: TextStyle(color: Colors.grey),
          ),
        ],
      ),
    );
  }

  void _openArticle(BuildContext context, String url) {
    if (url == '#') {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No link available')),
      );
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Opening: $url')),
    );
  }
}