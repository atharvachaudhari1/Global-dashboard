import 'package:flutter/material.dart';

class SourceSelector extends StatelessWidget {
  final String activeSource;
  final Function(String) onSourceChanged;

  const SourceSelector({
    super.key,
    required this.activeSource,
    required this.onSourceChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          _buildChip(context, 'gdelt', 'GDELT'),
          _buildChip(context, 'rss', 'RSS Mix'),
          _buildChip(context, 'all', 'All'),
        ],
      ),
    );
  }

  Widget _buildChip(BuildContext context, String source, String label) {
    final isActive = activeSource == source;
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: ChoiceChip(
        label: Text(label),
        selected: isActive,
        onSelected: (_) => onSourceChanged(source),
        selectedColor: Theme.of(context).colorScheme.primaryContainer,
      ),
    );
  }
}