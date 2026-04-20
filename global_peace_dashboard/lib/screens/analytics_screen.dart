import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:provider/provider.dart';
import '../providers/news_provider.dart';

class AnalyticsScreen extends StatelessWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<NewsProvider>(
      builder: (context, provider, _) {
        final articles = provider.articles;
        final total = articles.length > 0 ? articles.length : 1;
        final peace = provider.peaceCount;
        final neutral = provider.neutralCount;
        final conflict = provider.conflictCount;

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Analytics',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 24),
              _buildTrendChart(context, articles),
              const SizedBox(height: 24),
              _buildDoughnutChart(context, peace, neutral, conflict, total),
            ],
          ),
        );
      },
    );
  }

  Widget _buildTrendChart(BuildContext context, List articles) {
    final data = articles.take(20).toList();
    
    return Container(
      height: 200,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Peace Score Trend',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Last 20 articles',
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: data.isEmpty
                ? const Center(child: Text('No data'))
                : BarChart(
                    BarChartData(
                      barGroups: List.generate(data.length, (i) {
                        final score = data[i].score as double;
                        final color = score >= 6.5
                            ? const Color(0xFF1D9E75)
                            : score >= 4.0
                                ? const Color(0xFF888888)
                                : const Color(0xFFE24B4A);
                        return BarChartGroupData(
                          x: i,
                          barRods: [
                            BarChartRodData(
                              toY: score,
                              color: color,
                              width: 12,
                              borderRadius: const BorderRadius.vertical(top: Radius.circular(4)),
                            ),
                          ],
                        );
                      }),
                      borderData: FlBorderData(show: false),
                      gridData: FlGridData(
                        show: true,
                        drawVerticalLine: false,
                        horizontalInterval: 2,
                        getDrawingHorizontalLine: (value) => FlLine(
                          color: Colors.grey.withOpacity(0.2),
                          strokeWidth: 1,
                        ),
                      ),
                      titlesData: FlTitlesData(
                        leftTitles: AxisTitles(
                          sideTitles: SideTitles(
                            showTitles: true,
                            interval: 2,
                            reservedSize: 30,
                            getTitlesWidget: (value, meta) => Text(
                              value.toInt().toString(),
                              style: const TextStyle(fontSize: 10),
                            ),
                          ),
                        ),
                        rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        bottomTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      ),
                      minY: 0,
                      maxY: 10,
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildDoughnutChart(BuildContext context, int peace, int neutral, int conflict, int total) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Classification Split',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            'Article distribution',
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 120,
                  child: total <= 0
                      ? const Center(child: Text('No data'))
                      : PieChart(
                          PieChartData(
                            sectionsSpace: 2,
                            centerSpaceRadius: 30,
                            sections: [
                              PieChartSectionData(
                                value: peace.toDouble(),
                                color: const Color(0xFF1D9E75),
                                title: '${(peace / total * 100).round()}%',
                                titleStyle: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              PieChartSectionData(
                                value: neutral.toDouble(),
                                color: const Color(0xFF888888),
                                title: '${(neutral / total * 100).round()}%',
                                titleStyle: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                              PieChartSectionData(
                                value: conflict.toDouble(),
                                color: const Color(0xFFE24B4A),
                                title: '${(conflict / total * 100).round()}%',
                                titleStyle: const TextStyle(
                                  fontSize: 12,
                                  fontWeight: FontWeight.bold,
                                  color: Colors.white,
                                ),
                              ),
                            ],
                          ),
                        ),
                ),
              ),
              const SizedBox(width: 16),
              Column(
                children: [
                  _buildLegendItem(const Color(0xFF1D9E75), 'Peace', peace, total),
                  const SizedBox(height: 8),
                  _buildLegendItem(const Color(0xFF888888), 'Neutral', neutral, total),
                  const SizedBox(height: 8),
                  _buildLegendItem(const Color(0xFFE24B4A), 'Conflict', conflict, total),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(Color color, String label, int count, int total) {
    return Row(
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '$label: $count',
          style: const TextStyle(fontSize: 13),
        ),
      ],
    );
  }
}