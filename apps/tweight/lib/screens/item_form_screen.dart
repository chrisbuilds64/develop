import 'package:flutter/material.dart';
import '../models/item.dart';
import '../services/api_client.dart';
import '../services/item_service.dart';
import '../widgets/tag_picker_dialog.dart';

class ItemFormScreen extends StatefulWidget {
  final ApiClient apiClient;
  final Item? item;

  const ItemFormScreen({
    super.key,
    required this.apiClient,
    this.item,
  });

  bool get isEditing => item != null;

  @override
  State<ItemFormScreen> createState() => _ItemFormScreenState();
}

class _ItemFormScreenState extends State<ItemFormScreen> {
  late final ItemService _itemService;
  late final TextEditingController _labelController;
  late final TextEditingController _tagController;
  String _contentType = 'note';
  List<String> _tags = [];
  Set<String> _availableTags = {};
  bool _saving = false;
  String? _error;

  static const _contentTypes = ['note', 'task', 'link', 'other'];

  @override
  void initState() {
    super.initState();
    _itemService = ItemService(widget.apiClient);
    _labelController = TextEditingController(text: widget.item?.label ?? '');
    _tagController = TextEditingController();
    if (widget.item != null) {
      _contentType = widget.item!.contentType;
      _tags = List.from(widget.item!.tags);
    }
    _loadAvailableTags();
  }

  Future<void> _loadAvailableTags() async {
    try {
      final items = await _itemService.getItems();
      setState(() {
        _availableTags = items.expand((item) => item.tags).toSet();
      });
    } catch (e) {
      // Ignore errors, tags will just be empty
    }
  }

  @override
  void dispose() {
    _labelController.dispose();
    _tagController.dispose();
    super.dispose();
  }

  void _addTag() {
    final tag = _tagController.text.trim().toLowerCase();
    if (tag.isNotEmpty && !_tags.contains(tag)) {
      setState(() {
        _tags.add(tag);
        _tagController.clear();
      });
    }
  }

  void _removeTag(String tag) {
    setState(() => _tags.remove(tag));
  }

  Future<void> _showTagPicker() async {
    final result = await showTagPickerDialog(
      context: context,
      availableTags: _availableTags,
      selectedTags: _tags,
      title: 'Select Tags',
    );

    if (result != null) {
      setState(() => _tags = result);
    }
  }

  Future<void> _save() async {
    final label = _labelController.text.trim();
    if (label.isEmpty) {
      setState(() => _error = 'Label is required');
      return;
    }

    setState(() {
      _saving = true;
      _error = null;
    });

    try {
      if (widget.isEditing) {
        await _itemService.updateItem(
          widget.item!.id,
          label: label,
          contentType: _contentType,
          tags: _tags,
        );
      } else {
        await _itemService.createItem(
          label: label,
          contentType: _contentType,
          tags: _tags,
        );
      }

      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } catch (e) {
      setState(() => _error = 'Error: $e');
    } finally {
      if (mounted) {
        setState(() => _saving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isEditing ? 'Edit Item' : 'New Item'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _labelController,
              decoration: const InputDecoration(
                labelText: 'Label',
                border: OutlineInputBorder(),
              ),
              enabled: !_saving,
              autofocus: true,
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              value: _contentType,
              decoration: const InputDecoration(
                labelText: 'Content Type',
                border: OutlineInputBorder(),
              ),
              items: _contentTypes.map((type) {
                return DropdownMenuItem(
                  value: type,
                  child: Text(type),
                );
              }).toList(),
              onChanged: _saving
                  ? null
                  : (value) {
                      if (value != null) {
                        setState(() => _contentType = value);
                      }
                    },
            ),
            const SizedBox(height: 16),
            // Tags section
            InkWell(
              onTap: _saving ? null : _showTagPicker,
              child: InputDecorator(
                decoration: InputDecoration(
                  labelText: 'Tags',
                  border: const OutlineInputBorder(),
                  suffixIcon: IconButton(
                    icon: const Icon(Icons.sell),
                    onPressed: _saving ? null : _showTagPicker,
                  ),
                ),
                child: _tags.isEmpty
                    ? Text(
                        'Tap to select tags...',
                        style: TextStyle(color: Colors.grey[600]),
                      )
                    : Wrap(
                        spacing: 8,
                        runSpacing: 4,
                        children: _tags.map((tag) {
                          return Chip(
                            label: Text(tag),
                            deleteIcon: const Icon(Icons.close, size: 18),
                            onDeleted: _saving ? null : () => _removeTag(tag),
                            visualDensity: VisualDensity.compact,
                          );
                        }).toList(),
                      ),
              ),
            ),
            const SizedBox(height: 8),
            // Manual tag input
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _tagController,
                    decoration: const InputDecoration(
                      labelText: 'New tag',
                      border: OutlineInputBorder(),
                      hintText: 'Or type new tag...',
                    ),
                    enabled: !_saving,
                    onSubmitted: (_) => _addTag(),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: _saving ? null : _addTag,
                  icon: const Icon(Icons.add),
                ),
              ],
            ),
            const SizedBox(height: 24),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(
                  _error!,
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            ElevatedButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(widget.isEditing ? 'Save' : 'Create'),
            ),
          ],
        ),
      ),
    );
  }
}
