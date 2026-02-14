import 'dart:io';

import 'package:flutter/material.dart';
import '../models/article.dart';
import '../models/pipeline_stage.dart';
import '../services/pipeline_notifier.dart';
import '../widgets/completeness_indicator.dart';
import '../widgets/file_viewer.dart';
import '../widgets/move_buttons.dart';

class ArticleDetailScreen extends StatefulWidget {
  final Article article;
  final PipelineNotifier notifier;

  const ArticleDetailScreen({
    super.key,
    required this.article,
    required this.notifier,
  });

  @override
  State<ArticleDetailScreen> createState() => _ArticleDetailScreenState();
}

class _ArticleDetailScreenState extends State<ArticleDetailScreen> {
  String? _selectedFile;
  String? _fileContent;
  bool _loadingFile = false;

  @override
  void initState() {
    super.initState();
    // Auto-select first readable file
    final readable = widget.article.files
        .where((f) => !f.endsWith('.jpg') && !f.endsWith('.jpeg') &&
            !f.endsWith('.png') && !f.endsWith('.svg'))
        .toList();
    if (readable.isNotEmpty) {
      _loadFile(readable.first);
    }
  }

  bool _isImage(String name) {
    return name.endsWith('.jpg') || name.endsWith('.jpeg') ||
        name.endsWith('.png');
  }

  String get _selectedFilePath {
    final basePath = widget.article.absolutePath;
    return widget.article.isStandaloneFile
        ? basePath
        : '$basePath/$_selectedFile';
  }

  Future<void> _loadFile(String fileName) async {
    if (_isImage(fileName)) {
      setState(() {
        _selectedFile = fileName;
        _fileContent = null;
        _loadingFile = false;
      });
      return;
    }

    setState(() {
      _selectedFile = fileName;
      _loadingFile = true;
    });

    final basePath = widget.article.absolutePath;
    final path = widget.article.isStandaloneFile
        ? basePath
        : '$basePath/$fileName';

    final content = await widget.notifier.readFile(path);
    if (mounted) {
      setState(() {
        _fileContent = content;
        _loadingFile = false;
      });
    }
  }

  void _onMove(PipelineStage target) async {
    await widget.notifier.moveArticle(widget.article, target);
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final article = widget.article;
    final stageColor = article.stage.color;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          article.displayTitle,
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        actions: [
          // Stage badge
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: stageColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              article.stage.label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                color: stageColor,
              ),
            ),
          ),
        ],
      ),
      body: Row(
        children: [
          // Left panel: Info + File list
          SizedBox(
            width: 280,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Article info
                _buildInfoPanel(article, stageColor),

                const Divider(height: 1),

                // Move buttons
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: MoveButtons(
                    article: article,
                    onMove: _onMove,
                  ),
                ),

                const Divider(height: 1),

                // Files header
                Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  child: Text(
                    'FILES',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      color: Colors.grey[500],
                      letterSpacing: 1,
                    ),
                  ),
                ),

                // File list
                Expanded(
                  child: ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    itemCount: article.files.length,
                    itemBuilder: (context, index) {
                      final file = article.files[index];
                      final isSelected = file == _selectedFile;
                      return ListTile(
                        dense: true,
                        selected: isSelected,
                        selectedTileColor: stageColor.withValues(alpha: 0.1),
                        leading: Icon(
                          _fileIcon(file),
                          size: 16,
                          color: isSelected ? stageColor : Colors.grey[600],
                        ),
                        title: Text(
                          file,
                          style: TextStyle(
                            fontSize: 12,
                            fontFamily: 'monospace',
                            color:
                                isSelected ? stageColor : Colors.grey[400],
                          ),
                        ),
                        onTap: () => _loadFile(file),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),

          const VerticalDivider(width: 1),

          // Right panel: File viewer
          Expanded(
            child: _loadingFile
                ? const Center(child: CircularProgressIndicator())
                : _selectedFile != null && _isImage(_selectedFile!)
                    ? _buildImageViewer()
                    : _fileContent != null && _selectedFile != null
                        ? Padding(
                            padding: const EdgeInsets.all(12),
                            child: FileViewer(
                              fileName: _selectedFile!,
                              content: _fileContent!,
                            ),
                          )
                        : Center(
                            child: Text(
                              article.isStandaloneFile
                                  ? 'Standalone file'
                                  : 'Select a file to view',
                              style: TextStyle(color: Colors.grey[600]),
                            ),
                          ),
          ),
        ],
      ),
    );
  }

  Widget _buildInfoPanel(Article article, Color stageColor) {
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Prefix
          if (article.prefix != null)
            Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: stageColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                article.prefix!,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: stageColor,
                ),
              ),
            ),

          // Meta info rows
          if (article.meta?.subtitle != null)
            _infoRow('Subtitle', article.meta!.subtitle!),
          if (article.track != null) _infoRow('Track', article.track!),
          if (article.mood != null) _infoRow('Mood', article.mood!),
          if (article.meta?.location != null)
            _infoRow('Location', article.meta!.location!),
          if (article.meta?.created != null)
            _infoRow('Created', article.meta!.created!),

          const SizedBox(height: 8),

          // Completeness
          if (!article.isStandaloneFile) ...[
            Text(
              'COMPLETENESS',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: Colors.grey[500],
                letterSpacing: 1,
              ),
            ),
            const SizedBox(height: 4),
            CompletenessIndicator(
              completeness: article.completeness,
              color: stageColor,
            ),
          ],

          // Tags
          if (article.meta != null && article.meta!.tags.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: article.meta!.tags.map((tag) {
                return Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.grey[800],
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '#$tag',
                    style: TextStyle(fontSize: 10, color: Colors.grey[400]),
                  ),
                );
              }).toList(),
            ),
          ],

          // Platforms
          if (article.meta?.platforms.isNotEmpty == true) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 4,
              runSpacing: 4,
              children: article.meta!.platforms.entries
                  .where((e) => e.value)
                  .map((e) {
                return Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.green[900],
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    e.key,
                    style:
                        const TextStyle(fontSize: 10, color: Colors.white70),
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 65,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 11,
                color: Colors.grey[600],
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(fontSize: 11),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildImageViewer() {
    final file = File(_selectedFilePath);
    return Padding(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // File name header
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.grey[850],
              borderRadius:
                  const BorderRadius.vertical(top: Radius.circular(8)),
            ),
            child: Text(
              _selectedFile!,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
                fontFamily: 'monospace',
              ),
            ),
          ),
          // Image
          Expanded(
            child: Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.grey[900],
                borderRadius:
                    const BorderRadius.vertical(bottom: Radius.circular(8)),
              ),
              child: InteractiveViewer(
                maxScale: 5.0,
                child: Image.file(
                  file,
                  fit: BoxFit.contain,
                  errorBuilder: (_, error, _) => Center(
                    child: Text(
                      'Could not load image\n$error',
                      style: TextStyle(color: Colors.grey[500], fontSize: 12),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  IconData _fileIcon(String name) {
    if (name.endsWith('.md')) return Icons.description;
    if (name.endsWith('.html')) return Icons.code;
    if (name.endsWith('.txt')) return Icons.text_snippet;
    if (name.endsWith('.json')) return Icons.data_object;
    if (name.endsWith('.svg')) return Icons.image;
    if (name.endsWith('.jpg') || name.endsWith('.jpeg') || name.endsWith('.png')) {
      return Icons.photo;
    }
    return Icons.insert_drive_file;
  }
}
