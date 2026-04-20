import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/news_provider.dart';
import '../widgets/metric_card.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<NewsProvider>(
      builder: (context, provider, _) {
        final gpi = provider.globalPeaceIndex;
        final gpiColor = gpi >= 6.0 ? const Color(0xFF1D9E75) : gpi >= 4.0 ? const Color(0xFFEF9F27) : const Color(0xFFE24B4A);
        
        return RefreshIndicator(
          onRefresh: () => provider.fetchNews(),
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(context, provider),
                const SizedBox(height: 16),
                GridView.count(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  crossAxisCount: 2,
                  crossAxisSpacing: 12,
                  mainAxisSpacing: 12,
                  childAspectRatio: 1.3,
                  children: [
                    MetricCard(
                      label: 'Global Peace Index',
                      value: provider.isLoading ? '--' : gpi.toString(),
                      sub: 'Average score',
                      valueColor: provider.isLoading ? null : gpiColor,
                    ),
                    MetricCard(
                      label: 'Articles Analyzed',
                      value: provider.isLoading ? '0' : provider.totalArticles.toString(),
                      sub: 'This session',
                    ),
                    MetricCard(
                      label: 'Conflict Alerts',
                      value: provider.isLoading ? '0' : provider.conflictCount.toString(),
                      sub: 'Score below 4.0',
                      valueColor: const Color(0xFFE24B4A),
                    ),
                    MetricCard(
                      label: 'Peace Events',
                      value: provider.isLoading ? '0' : provider.peaceCount.toString(),
                      sub: 'Score above 6.5',
                      valueColor: const Color(0xFF1D9E75),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildHeader(BuildContext context, NewsProvider provider) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Global Peace Dashboard',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            if (provider.lastUpdated != null)
              Text(
                'Updated: ${_formatTime(provider.lastUpdated!)}',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.grey[600],
                ),
              ),
          ],
        ),
        Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.red[400],
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: const BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 4),
                  const Text(
                    'LIVE',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  String _formatTime(DateTime dt) {
    return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
  }
}