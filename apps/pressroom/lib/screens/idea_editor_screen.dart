import 'package:flutter/material.dart';
import '../services/pipeline_notifier.dart';

class IdeaEditorScreen extends StatefulWidget {
  final PipelineNotifier notifier;

  const IdeaEditorScreen({super.key, required this.notifier});

  @override
  State<IdeaEditorScreen> createState() => _IdeaEditorScreenState();
}

class _IdeaEditorScreenState extends State<IdeaEditorScreen> {
  final _titleController = TextEditingController();
  final _trackController = TextEditingController();
  final _notesController = TextEditingController();
  String _selectedTrack = 'deep-tech';
  bool _saving = false;

  static const _tracks = ['deep-tech', 'clarity', 'security', 'tech'];

  @override
  void dispose() {
    _titleController.dispose();
    _trackController.dispose();
    _notesController.dispose();
    super.dispose();
  }

  String _buildFolderName() {
    final title = _titleController.text.trim();
    final slug = title
        .replaceAll(RegExp(r'[^a-zA-Z0-9\s]'), '')
        .trim()
        .replaceAll(RegExp(r'\s+'), '-');
    return slug;
  }

  String _buildNotesContent() {
    final buf = StringBuffer();
    buf.writeln('# ${_titleController.text.trim()}');
    buf.writeln();
    buf.writeln('**Track:** $_selectedTrack');
    buf.writeln();
    final notes = _notesController.text.trim();
    if (notes.isNotEmpty) {
      buf.writeln('## Notes');
      buf.writeln();
      buf.writeln(notes);
    }
    return buf.toString();
  }

  Future<void> _save() async {
    final title = _titleController.text.trim();
    if (title.isEmpty) return;

    setState(() => _saving = true);

    try {
      final folderName = _buildFolderName();
      final content = _buildNotesContent();
      await widget.notifier.createIdea(folderName, content);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to create idea: $e')),
        );
        setState(() => _saving = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'New Idea',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: FilledButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.save, size: 16),
              label: const Text('Save', style: TextStyle(fontSize: 13)),
              style: FilledButton.styleFrom(
                backgroundColor: const Color(0xFF7C4DFF),
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: SizedBox(
          width: 600,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Title
              _label('TITLE'),
              const SizedBox(height: 6),
              TextField(
                controller: _titleController,
                autofocus: true,
                style: const TextStyle(fontSize: 14),
                decoration: _inputDecoration('Working title for the idea'),
              ),
              const SizedBox(height: 20),

              // Track
              _label('TRACK'),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                children: _tracks.map((track) {
                  final selected = track == _selectedTrack;
                  return ChoiceChip(
                    label: Text(
                      track.toUpperCase(),
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: selected ? Colors.white : Colors.grey[400],
                      ),
                    ),
                    selected: selected,
                    selectedColor: _trackColor(track),
                    backgroundColor: Colors.grey[850],
                    side: BorderSide(
                      color: selected
                          ? _trackColor(track)
                          : Colors.grey[700]!,
                    ),
                    onSelected: (_) =>
                        setState(() => _selectedTrack = track),
                  );
                }).toList(),
              ),
              const SizedBox(height: 20),

              // Notes
              _label('NOTES'),
              const SizedBox(height: 6),
              TextField(
                controller: _notesController,
                maxLines: 12,
                style: const TextStyle(fontSize: 14, height: 1.5),
                decoration: _inputDecoration(
                    'What is this about? Key points, angles, rough structure...'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _label(String text) {
    return Text(
      text,
      style: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: Colors.grey[500],
        letterSpacing: 1,
      ),
    );
  }

  InputDecoration _inputDecoration(String hint) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(fontSize: 13, color: Colors.grey[700]),
      filled: true,
      fillColor: Colors.grey[900],
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: Colors.grey[800]!),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: BorderSide(color: Colors.grey[800]!),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFF7C4DFF)),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    );
  }

  Color _trackColor(String track) {
    switch (track) {
      case 'deep-tech':
        return const Color(0xFF2196F3);
      case 'clarity':
        return const Color(0xFFFFC107);
      case 'security':
        return const Color(0xFFF44336);
      case 'tech':
        return const Color(0xFF00BCD4);
      default:
        return Colors.grey;
    }
  }
}
