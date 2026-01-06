import 'package:flutter/material.dart';
import '../models/video.dart';
import '../services/video_service.dart';

/// Screen for editing video tags
class EditVideoScreen extends StatefulWidget {
  final Video video;

  const EditVideoScreen({super.key, required this.video});

  @override
  State<EditVideoScreen> createState() => _EditVideoScreenState();
}

class _EditVideoScreenState extends State<EditVideoScreen> {
  final VideoService _videoService = VideoService();
  final TextEditingController _tagsController = TextEditingController();
  bool _saving = false;
  List<String> _availableTags = [];
  bool _loadingTags = true;

  @override
  void initState() {
    super.initState();
    // Initialize with current tags
    _tagsController.text = widget.video.tagsList.join(', ');
    _loadAvailableTags();
  }

  Future<void> _loadAvailableTags() async {
    try {
      final tags = await _videoService.getTags();
      setState(() {
        _availableTags = tags;
        _loadingTags = false;
      });
    } catch (e) {
      setState(() {
        _loadingTags = false;
      });
    }
  }

  Future<void> _saveChanges() async {
    setState(() => _saving = true);

    try {
      // Parse tags from text field
      final tagsText = _tagsController.text.trim();
      final tags = tagsText.isEmpty
          ? <String>[]
          : tagsText.split(',').map((t) => t.trim()).where((t) => t.isNotEmpty).toList();

      // Update video
      await _videoService.updateVideo(widget.video.id, widget.video.url, tags);

      if (mounted) {
        Navigator.pop(context, true); // Return true to indicate success
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Video updated successfully')),
        );
      }
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to update: $e')),
        );
      }
    }
  }

  void _addTag(String tag) {
    final currentTags = _tagsController.text.trim();
    final newTags = currentTags.isEmpty ? tag : '$currentTags, $tag';
    _tagsController.text = newTags;
  }

  @override
  void dispose() {
    _tagsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Edit Video'),
        actions: [
          if (_saving)
            const Padding(
              padding: EdgeInsets.all(16.0),
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            )
          else
            IconButton(
              icon: const Icon(Icons.check),
              onPressed: _saveChanges,
              tooltip: 'Save',
            ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Video info (read-only)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(12.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.video.title ?? 'YouTube Video',
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (widget.video.thumbnailUrl != null)
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: Image.network(
                          widget.video.thumbnailUrl!,
                          height: 120,
                          width: double.infinity,
                          fit: BoxFit.cover,
                        ),
                      ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Tags editor
            Text(
              'Tags (comma-separated)',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _tagsController,
              decoration: InputDecoration(
                hintText: 'workout, triceps, cable',
                border: const OutlineInputBorder(),
                suffixIcon: _tagsController.text.isNotEmpty
                    ? IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () => _tagsController.clear(),
                      )
                    : null,
              ),
              maxLines: 2,
              onChanged: (_) => setState(() {}), // Rebuild for suffix icon
            ),
            const SizedBox(height: 16),

            // Tag suggestions (autocomplete) - with max height to prevent overflow
            if (_loadingTags)
              const Center(child: CircularProgressIndicator())
            else if (_availableTags.isNotEmpty)
              SizedBox(
                height: 120, // Max height to prevent overflow when keyboard is open
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Your tags (tap to add)',
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: _availableTags.map((tag) {
                          final isSelected = widget.video.tagsList.contains(tag);
                          return ActionChip(
                            label: Text(tag),
                            onPressed: () => _addTag(tag),
                            backgroundColor: isSelected
                                ? Theme.of(context).colorScheme.primaryContainer
                                : null,
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                ),
              ),

            const Spacer(),

            // Save button (bottom)
            ElevatedButton.icon(
              onPressed: _saving ? null : _saveChanges,
              icon: _saving
                  ? const SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save),
              label: Text(_saving ? 'Saving...' : 'Save Changes'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
