import 'package:flutter/material.dart';

class TagPickerDialog extends StatefulWidget {
  final Set<String> availableTags;
  final List<String> selectedTags;
  final String title;

  const TagPickerDialog({
    super.key,
    required this.availableTags,
    required this.selectedTags,
    this.title = 'Select Tags',
  });

  @override
  State<TagPickerDialog> createState() => _TagPickerDialogState();
}

class _TagPickerDialogState extends State<TagPickerDialog> {
  late List<String> _selected;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _selected = List.from(widget.selectedTags);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<String> get _filteredTags {
    final allTags = widget.availableTags.toList()..sort();
    if (_searchQuery.isEmpty) return allTags;
    return allTags
        .where((tag) => tag.toLowerCase().contains(_searchQuery.toLowerCase()))
        .toList();
  }

  void _toggleTag(String tag) {
    setState(() {
      if (_selected.contains(tag)) {
        _selected.remove(tag);
      } else {
        _selected.add(tag);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: SizedBox(
        width: double.maxFinite,
        height: 400,
        child: Column(
          children: [
            TextField(
              controller: _searchController,
              decoration: InputDecoration(
                hintText: 'Search tags...',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _searchQuery.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _searchQuery = '');
                        },
                      )
                    : null,
                border: const OutlineInputBorder(),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12),
              ),
              onChanged: (value) => setState(() => _searchQuery = value),
            ),
            const SizedBox(height: 12),
            if (_selected.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: _selected.map((tag) {
                    return Chip(
                      label: Text(tag, style: const TextStyle(fontSize: 12)),
                      deleteIcon: const Icon(Icons.close, size: 16),
                      onDeleted: () => _toggleTag(tag),
                      visualDensity: VisualDensity.compact,
                      materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    );
                  }).toList(),
                ),
              ),
            Expanded(
              child: _filteredTags.isEmpty
                  ? Center(
                      child: Text(
                        _searchQuery.isNotEmpty
                            ? 'No tags match "$_searchQuery"'
                            : 'No tags available',
                        style: TextStyle(color: Colors.grey[600]),
                      ),
                    )
                  : ListView.builder(
                      itemCount: _filteredTags.length,
                      itemBuilder: (context, index) {
                        final tag = _filteredTags[index];
                        final isSelected = _selected.contains(tag);
                        return CheckboxListTile(
                          title: Text(tag),
                          value: isSelected,
                          dense: true,
                          onChanged: (_) => _toggleTag(tag),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, null),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, _selected),
          child: const Text('Apply'),
        ),
      ],
    );
  }
}

/// Shows the tag picker dialog and returns selected tags, or null if cancelled
Future<List<String>?> showTagPickerDialog({
  required BuildContext context,
  required Set<String> availableTags,
  required List<String> selectedTags,
  String title = 'Select Tags',
}) {
  return showDialog<List<String>>(
    context: context,
    builder: (ctx) => TagPickerDialog(
      availableTags: availableTags,
      selectedTags: selectedTags,
      title: title,
    ),
  );
}
