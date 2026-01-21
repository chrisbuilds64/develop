import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/item.dart';
import '../services/api_client.dart';
import '../services/item_service.dart';
import '../widgets/tag_picker_dialog.dart';
import 'login_screen.dart';
import 'item_form_screen.dart';

class ItemsScreen extends StatefulWidget {
  final ApiClient apiClient;

  const ItemsScreen({super.key, required this.apiClient});

  @override
  State<ItemsScreen> createState() => _ItemsScreenState();
}

class _ItemsScreenState extends State<ItemsScreen> {
  late final ItemService _itemService;
  List<Item> _items = [];
  bool _loading = true;
  String? _error;

  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  List<String> _selectedTags = [];
  Set<String> _availableTags = {};
  bool _textViewMode = false; // false = card view, true = text view

  @override
  void initState() {
    super.initState();
    _itemService = ItemService(widget.apiClient);
    _loadItems();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadItems({bool updateAvailableTags = true}) async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final items = await _itemService.getItems(
        search: _searchQuery.isNotEmpty ? _searchQuery : null,
        tags: _selectedTags.isNotEmpty ? _selectedTags : null,
      );
      setState(() {
        _items = items;
        if (updateAvailableTags) {
          _availableTags = items.expand((item) => item.tags).toSet();
        }
      });
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Error: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  void _onSearchChanged(String value) {
    setState(() => _searchQuery = value);
    Future.delayed(const Duration(milliseconds: 300), () {
      if (_searchQuery == value) {
        _loadItems(updateAvailableTags: false);
      }
    });
  }

  void _toggleTag(String tag) {
    setState(() {
      if (_selectedTags.contains(tag)) {
        _selectedTags.remove(tag);
      } else {
        _selectedTags.add(tag);
      }
    });
    _loadItems(updateAvailableTags: false);
  }

  void _clearFilters() {
    setState(() {
      _searchController.clear();
      _searchQuery = '';
      _selectedTags.clear();
    });
    _loadItems();
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    widget.apiClient.clearToken();

    if (mounted) {
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => LoginScreen(apiClient: widget.apiClient),
        ),
      );
    }
  }

  Future<void> _deleteItem(Item item) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete Item'),
        content: Text('Delete "${item.label}"?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    try {
      await _itemService.deleteItem(item.id);
      await _loadItems();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${e.message}')),
        );
      }
    }
  }

  void _navigateToForm({Item? item}) async {
    final result = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => ItemFormScreen(
          apiClient: widget.apiClient,
          item: item,
        ),
      ),
    );

    if (result == true) {
      _loadItems();
    }
  }

  Future<void> _showQuickCapture() async {
    final controller = TextEditingController();
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Quick Capture'),
        content: TextField(
          controller: controller,
          maxLines: 8,
          autofocus: true,
          decoration: const InputDecoration(
            hintText: 'One item per line...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result != true || controller.text.trim().isEmpty) return;

    final lines = controller.text
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();

    if (lines.isEmpty) return;

    int saved = 0;
    for (final line in lines) {
      try {
        await _itemService.createItem(
          label: line,
          contentType: 'note',
          tags: ['inbox'],
        );
        saved++;
      } catch (e) {
        // Continue with next item
      }
    }

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$saved items added to inbox')),
      );
      _loadItems();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Items'),
        actions: [
          IconButton(
            icon: const Icon(Icons.inbox),
            tooltip: 'Quick Capture',
            onPressed: _showQuickCapture,
          ),
          IconButton(
            icon: Icon(_textViewMode ? Icons.view_list : Icons.article),
            tooltip: _textViewMode ? 'Card View' : 'Text View',
            onPressed: () => setState(() => _textViewMode = !_textViewMode),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
      ),
      body: Column(
        children: [
          _buildSearchBar(),
          if (_availableTags.isNotEmpty) _buildTagChips(),
          Expanded(child: _buildBody()),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _navigateToForm(),
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.all(8.0),
      child: TextField(
        controller: _searchController,
        decoration: InputDecoration(
          hintText: 'Search items...',
          prefixIcon: const Icon(Icons.search),
          suffixIcon: (_searchQuery.isNotEmpty || _selectedTags.isNotEmpty)
              ? IconButton(
                  icon: const Icon(Icons.clear),
                  onPressed: _clearFilters,
                )
              : null,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(8),
          ),
          contentPadding: const EdgeInsets.symmetric(horizontal: 16),
        ),
        onChanged: _onSearchChanged,
      ),
    );
  }

  Future<void> _showTagPicker() async {
    final result = await showTagPickerDialog(
      context: context,
      availableTags: _availableTags,
      selectedTags: _selectedTags,
      title: 'Filter by Tags',
    );

    if (result != null) {
      setState(() => _selectedTags = result);
      _loadItems(updateAvailableTags: false);
    }
  }

  Widget _buildTagChips() {
    return GestureDetector(
      onLongPress: _showTagPicker,
      child: Container(
        height: 40,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: [
            // Tag picker button
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: ActionChip(
                avatar: const Icon(Icons.filter_list, size: 18),
                label: Text(_selectedTags.isEmpty
                    ? 'Tags'
                    : '${_selectedTags.length} selected'),
                onPressed: _showTagPicker,
              ),
            ),
            // Quick filter chips for available tags
            ..._availableTags.map((tag) {
              final isSelected = _selectedTags.contains(tag);
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(tag),
                  selected: isSelected,
                  onSelected: (_) => _toggleTag(tag),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadItems,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_items.isEmpty) {
      return Center(
        child: Text(
          (_searchQuery.isNotEmpty || _selectedTags.isNotEmpty)
              ? 'No items match your search.'
              : 'No items yet. Tap + to create one.',
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadItems,
      child: _textViewMode ? _buildTextView() : _buildCardView(),
    );
  }

  Widget _buildCardView() {
    return ListView.builder(
      itemCount: _items.length,
      itemBuilder: (context, index) {
        final item = _items[index];
        return ListTile(
          title: Text(item.label),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(item.contentType),
              if (item.tags.isNotEmpty)
                Wrap(
                  spacing: 4,
                  children: item.tags
                      .map((tag) => Chip(
                            label: Text(tag, style: const TextStyle(fontSize: 10)),
                            padding: EdgeInsets.zero,
                            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                            visualDensity: VisualDensity.compact,
                          ))
                      .toList(),
                ),
            ],
          ),
          isThreeLine: item.tags.isNotEmpty,
          trailing: IconButton(
            icon: const Icon(Icons.delete, color: Colors.red),
            onPressed: () => _deleteItem(item),
          ),
          onTap: () => _navigateToForm(item: item),
        );
      },
    );
  }

  Widget _buildTextView() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _items.length,
      itemBuilder: (context, index) {
        final item = _items[index];
        return InkWell(
          onTap: () => _navigateToForm(item: item),
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Text(
              item.label,
              style: const TextStyle(fontSize: 16, height: 1.5),
            ),
          ),
        );
      },
    );
  }
}
