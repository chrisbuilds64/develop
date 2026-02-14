import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../models/article.dart';
import '../models/pipeline_stage.dart';
import '../services/brief_assembler.dart';
import '../services/filesystem_service.dart';
import '../services/pipeline_notifier.dart';

class ProduceScreen extends StatefulWidget {
  final Article article;
  final PipelineNotifier notifier;

  const ProduceScreen({
    super.key,
    required this.article,
    required this.notifier,
  });

  @override
  State<ProduceScreen> createState() => _ProduceScreenState();
}

class _ProduceScreenState extends State<ProduceScreen> {
  List<RuleFile> _rules = [];
  String? _notesContent;
  String? _selectedRuleContent;
  RuleFile? _selectedRule;
  bool _loading = true;
  bool _assembling = false;

  // Session context fields
  final _dateController = TextEditingController();
  final _locationController = TextEditingController();
  final _moodController = TextEditingController();
  final _personalNotesController = TextEditingController();

  final _assembler = BriefAssembler();

  @override
  void initState() {
    super.initState();
    // Pre-fill date with today
    final now = DateTime.now();
    _dateController.text =
        '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
    _loadData();
  }

  @override
  void dispose() {
    _dateController.dispose();
    _locationController.dispose();
    _moodController.dispose();
    _personalNotesController.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    final rules = await widget.notifier.listRules();

    String? notes;
    if (!widget.article.isStandaloneFile) {
      final notesPath = '${widget.article.absolutePath}/notes.md';
      final content = await widget.notifier.readFile(notesPath);
      if (content != '[File not found]') notes = content;
    } else {
      notes = await widget.notifier.readFile(widget.article.absolutePath);
    }

    if (mounted) {
      setState(() {
        _rules = rules;
        _notesContent = notes;
        _loading = false;
      });
    }
  }

  Future<void> _selectRule(RuleFile rule) async {
    final content = await widget.notifier.readFile(rule.path);
    if (mounted) {
      setState(() {
        _selectedRule = rule;
        _selectedRuleContent = content;
      });
    }
  }

  Future<void> _generateBrief() async {
    if (_locationController.text.trim().isEmpty ||
        _moodController.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Location and Mood are required')),
      );
      return;
    }

    setState(() => _assembling = true);

    try {
      final session = SessionContext(
        date: _dateController.text.trim(),
        location: _locationController.text.trim(),
        mood: _moodController.text.trim(),
        personalNotes: _personalNotesController.text.trim().isEmpty
            ? null
            : _personalNotesController.text.trim(),
      );

      final brief = await _assembler.assemble(
        article: widget.article,
        session: session,
      );

      await Clipboard.setData(ClipboardData(text: brief));

      // Move to produce if still in ideas
      if (widget.article.stage == PipelineStage.ideas) {
        await widget.notifier.moveArticle(
            widget.article, PipelineStage.produce);
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                'Production brief copied to clipboard (${brief.length} chars)'),
            backgroundColor: const Color(0xFF4CAF50),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to generate brief: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _assembling = false);
    }
  }

  Future<void> _moveToProduceOnly() async {
    if (widget.article.stage == PipelineStage.ideas) {
      await widget.notifier.moveArticle(
          widget.article, PipelineStage.produce);
    }
    if (mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final article = widget.article;
    final stageColor = const Color(0xFF448AFF);

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Produce: ${article.displayTitle}',
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        actions: [
          if (article.stage == PipelineStage.ideas)
            OutlinedButton.icon(
              onPressed: _moveToProduceOnly,
              icon: const Icon(Icons.arrow_forward, size: 16),
              label: const Text('Move Only',
                  style: TextStyle(fontSize: 12)),
              style: OutlinedButton.styleFrom(
                foregroundColor: stageColor,
                side: BorderSide(
                    color: stageColor.withValues(alpha: 0.5)),
              ),
            ),
          const SizedBox(width: 8),
          FilledButton.icon(
            onPressed: _assembling ? null : _generateBrief,
            icon: _assembling
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(
                        strokeWidth: 2, color: Colors.white),
                  )
                : const Icon(Icons.content_copy, size: 16),
            label: const Text('Generate Brief',
                style: TextStyle(fontSize: 13)),
            style: FilledButton.styleFrom(backgroundColor: stageColor),
          ),
          const SizedBox(width: 12),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Row(
              children: [
                // Left: Session context + Notes + Deliverables
                SizedBox(
                  width: 380,
                  child: ListView(
                    padding: const EdgeInsets.all(12),
                    children: [
                      // Session Context
                      _sectionHeader('SESSION CONTEXT', stageColor),
                      const SizedBox(height: 8),
                      _contextField('Date', _dateController, 'YYYY-MM-DD'),
                      const SizedBox(height: 8),
                      _contextField(
                          'Location', _locationController, 'e.g. Cologne, Germany'),
                      const SizedBox(height: 8),
                      _contextField(
                          'Mood', _moodController, 'e.g. focused, energetic'),
                      const SizedBox(height: 8),
                      Text('Personal Notes',
                          style: TextStyle(
                              fontSize: 11, color: Colors.grey[500])),
                      const SizedBox(height: 4),
                      TextField(
                        controller: _personalNotesController,
                        maxLines: 4,
                        style: const TextStyle(fontSize: 13, height: 1.4),
                        decoration: _inputDeco(
                            'What happened today? Key experiences, thoughts...'),
                      ),

                      const SizedBox(height: 16),
                      const Divider(),
                      const SizedBox(height: 8),

                      // Article Notes
                      _sectionHeader('ARTICLE NOTES', stageColor),
                      const SizedBox(height: 8),
                      if (_notesContent != null)
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: Colors.grey[900],
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: MarkdownBody(
                            data: _notesContent!,
                            selectable: true,
                            styleSheet: _mdStyle(),
                          ),
                        )
                      else
                        Text('No notes found',
                            style: TextStyle(
                                fontSize: 13, color: Colors.grey[600])),

                      const SizedBox(height: 16),
                      const Divider(),
                      const SizedBox(height: 8),

                      // Deliverables
                      _sectionHeader('DELIVERABLES', stageColor),
                      const SizedBox(height: 4),
                      ..._deliverables.map((d) {
                        final exists = article.files
                            .any((f) => d.any((alt) => f == alt));
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2),
                          child: Row(
                            children: [
                              Icon(
                                exists
                                    ? Icons.check_circle
                                    : Icons.circle_outlined,
                                size: 14,
                                color: exists
                                    ? const Color(0xFF4CAF50)
                                    : Colors.grey[700],
                              ),
                              const SizedBox(width: 8),
                              Text(
                                d.first,
                                style: TextStyle(
                                  fontSize: 12,
                                  fontFamily: 'monospace',
                                  color: exists
                                      ? Colors.grey[400]
                                      : Colors.grey[600],
                                  decoration: exists
                                      ? TextDecoration.lineThrough
                                      : null,
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                    ],
                  ),
                ),

                const VerticalDivider(width: 1),

                // Right: Rules reference
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _sectionHeader('PRODUCTION RULES', stageColor),
                      SizedBox(
                        height: 40,
                        child: ListView(
                          scrollDirection: Axis.horizontal,
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          children: _rules.map((rule) {
                            final selected =
                                rule.name == _selectedRule?.name;
                            return Padding(
                              padding: const EdgeInsets.only(right: 6),
                              child: FilterChip(
                                label: Text(
                                  _shortName(rule.name),
                                  style: TextStyle(
                                    fontSize: 11,
                                    color: selected
                                        ? Colors.white
                                        : Colors.grey[400],
                                  ),
                                ),
                                selected: selected,
                                selectedColor: stageColor,
                                backgroundColor: Colors.grey[850],
                                side: BorderSide(
                                  color: selected
                                      ? stageColor
                                      : Colors.grey[700]!,
                                ),
                                onSelected: (_) => _selectRule(rule),
                              ),
                            );
                          }).toList(),
                        ),
                      ),
                      Expanded(
                        child: _selectedRuleContent != null
                            ? Padding(
                                padding: const EdgeInsets.all(12),
                                child: Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: Colors.grey[900],
                                    borderRadius:
                                        BorderRadius.circular(8),
                                  ),
                                  child: Markdown(
                                    data: _selectedRuleContent!,
                                    selectable: true,
                                    padding: EdgeInsets.zero,
                                    styleSheet: _mdStyle(),
                                  ),
                                ),
                              )
                            : Center(
                                child: Text(
                                  'Select a rule to view',
                                  style:
                                      TextStyle(color: Colors.grey[600]),
                                ),
                              ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }

  Widget _sectionHeader(String text, Color color) {
    return Text(
      text,
      style: TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: color.withValues(alpha: 0.8),
        letterSpacing: 1,
      ),
    );
  }

  Widget _contextField(
      String label, TextEditingController controller, String hint) {
    return Row(
      children: [
        SizedBox(
          width: 70,
          child: Text(label,
              style: TextStyle(fontSize: 11, color: Colors.grey[500])),
        ),
        Expanded(
          child: TextField(
            controller: controller,
            style: const TextStyle(fontSize: 13),
            decoration: _inputDeco(hint),
          ),
        ),
      ],
    );
  }

  InputDecoration _inputDeco(String hint) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(fontSize: 12, color: Colors.grey[700]),
      filled: true,
      fillColor: Colors.grey[900],
      isDense: true,
      contentPadding:
          const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: BorderSide(color: Colors.grey[800]!),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: BorderSide(color: Colors.grey[800]!),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(6),
        borderSide: const BorderSide(color: Color(0xFF448AFF)),
      ),
    );
  }

  String _shortName(String name) {
    return name
        .replaceAll('.md', '')
        .replaceAll('-', ' ')
        .split(' ')
        .map((w) => w.isNotEmpty
            ? '${w[0].toUpperCase()}${w.substring(1).toLowerCase()}'
            : '')
        .join(' ');
  }

  MarkdownStyleSheet _mdStyle() {
    return MarkdownStyleSheet(
      p: TextStyle(fontSize: 13, color: Colors.grey[300], height: 1.5),
      h1: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w700,
          color: Colors.grey[100]),
      h2: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          color: Colors.grey[200]),
      h3: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          color: Colors.grey[200]),
      strong: TextStyle(
          fontWeight: FontWeight.w600, color: Colors.grey[200]),
      code: TextStyle(
        fontSize: 12,
        fontFamily: 'monospace',
        color: Colors.amber[200],
        backgroundColor: Colors.grey[850],
      ),
      codeblockDecoration: BoxDecoration(
        color: Colors.grey[850],
        borderRadius: BorderRadius.circular(6),
      ),
      listBullet: TextStyle(fontSize: 13, color: Colors.grey[400]),
      a: const TextStyle(color: Color(0xFF448AFF)),
    );
  }

  static const _deliverables = [
    ['substack.md', 'source.md'],
    ['substack.html', 'source.html'],
    ['linkedin-post.txt'],
    ['first-comment.txt'],
    ['linkedin-article.txt'],
    ['linkedin-article.html'],
    ['tiktok-script.txt'],
    ['dalle-prompt.txt'],
    ['title-dark.svg'],
    ['title-light.svg'],
    ['meta.json'],
  ];
}
