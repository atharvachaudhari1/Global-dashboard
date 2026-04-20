import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:provider/provider.dart';
import '../providers/news_provider.dart';

class MapScreen extends StatefulWidget {
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => _MapScreenState();
}

class _MapScreenState extends State<MapScreen> {
  final MapController _mapController = MapController();
  
  static const Map<String, CountryInfo> countryCoords = {
    'us': CountryInfo(coords: LatLng(37.09, -95.71), name: 'United States'),
    'gb': CountryInfo(coords: LatLng(55.37, -3.43), name: 'United Kingdom'),
    'in': CountryInfo(coords: LatLng(20.59, 78.96), name: 'India'),
    'cn': CountryInfo(coords: LatLng(35.86, 104.19), name: 'China'),
    'ru': CountryInfo(coords: LatLng(61.52, 105.31), name: 'Russia'),
    'de': CountryInfo(coords: LatLng(51.16, 10.45), name: 'Germany'),
    'fr': CountryInfo(coords: LatLng(46.22, 2.21), name: 'France'),
    'ua': CountryInfo(coords: LatLng(48.37, 31.16), name: 'Ukraine'),
    'il': CountryInfo(coords: LatLng(31.04, 34.85), name: 'Israel'),
    'iq': CountryInfo(coords: LatLng(33.22, 43.67), name: 'Iraq'),
    'sy': CountryInfo(coords: LatLng(34.8, 38.99), name: 'Syria'),
    'ye': CountryInfo(coords: LatLng(15.55, 48.51), name: 'Yemen'),
    'af': CountryInfo(coords: LatLng(33.93, 67.7), name: 'Afghanistan'),
    'pk': CountryInfo(coords: LatLng(30.37, 69.34), name: 'Pakistan'),
    'ir': CountryInfo(coords: LatLng(32.42, 53.68), name: 'Iran'),
  };

  @override
  Widget build(BuildContext context) {
    return Consumer<NewsProvider>(
      builder: (context, provider, _) {
        final markers = _buildMarkers(provider);
        
        return Stack(
          children: [
            FlutterMap(
              mapController: _mapController,
              options: MapOptions(
                initialCenter: const LatLng(20, 10),
                initialZoom: 2,
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.globalpeace.dashboard',
                ),
                CircleLayer(circles: markers),
              ],
            ),
            Positioned(
              top: 16,
              left: 16,
              right: 16,
              child: _buildLegend(),
            ),
            if (provider.selectedCountry != null)
              Positioned(
                bottom: 16,
                left: 16,
                right: 16,
                child: _buildFilterBar(context, provider),
              ),
          ],
        );
      },
    );
  }

  List<CircleMarker> _buildMarkers(NewsProvider provider) {
    final Map<String, List<double>> countryScores = {};
    
    for (var article in provider.articles) {
      final cc = article.country.toLowerCase();
      if (!countryScores.containsKey(cc)) countryScores[cc] = [];
      countryScores[cc]!.add(article.score);
    }

    final markers = <CircleMarker>[];
    countryScores.forEach((cc, scores) {
      final info = countryCoords[cc];
      if (info == null || scores.isEmpty) return;
      
      final avg = scores.reduce((a, b) => a + b) / scores.length;
      final cls = avg >= 6.5 ? 'peace' : avg >= 4.0 ? 'neutral' : 'conflict';
      final color = cls == 'peace' ? const Color(0xFF1D9E75) : cls == 'neutral' ? const Color(0xFF888888) : const Color(0xFFE24B4A);
      
      markers.add(
        CircleMarker(
          point: info.coords,
          radius: (8 + scores.length * 2).toDouble().clamp(8, 24),
          color: color.withOpacity(0.7),
          borderColor: color,
          borderStrokeWidth: 1.5,
        ),
      );
    });

    return markers;
  }

  Widget _buildLegend() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black.withOpacity(0.7),
        borderRadius: BorderRadius.circular(8),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _LegendItem(color: Color(0xFF1D9E75), label: 'Peaceful (≥6.5)'),
          SizedBox(width: 16),
          _LegendItem(color: Color(0xFFEF9F27), label: 'Tense (4-6.4)'),
          SizedBox(width: 16),
          _LegendItem(color: Color(0xFFE24B4A), label: 'Conflict (<4)'),
        ],
      ),
    );
  }

  Widget _buildFilterBar(BuildContext context, NewsProvider provider) {
    final countryInfo = countryCoords[provider.selectedCountry];
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            'Showing: ${countryInfo?.name ?? provider.selectedCountry}',
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          TextButton(
            onPressed: () => provider.setCountry(null),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
  }
}

class CountryInfo {
  final LatLng coords;
  final String name;
  const CountryInfo({required this.coords, required this.name});
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;
  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 10, color: Colors.white),
        ),
      ],
    );
  }
}