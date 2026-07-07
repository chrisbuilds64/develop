import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../services/filesystem_service.dart';
import '../services/pipeline_notifier.dart';

/// Canon Reference — read-only view of the editorial governing documents.
/// View-only by design: several referenced docs are immutable per the
/// canonical hierarchy, so PressRoom never edits them.
class RulesScreen extends StatefulWidget {
  final PipelineNotifier notifier;

  const RulesScreen({super.key, required this.notifier});

  @override
  State<RulesScreen> createState() => _RulesScreenState();
}

class _RulesScreenState extends State<RulesScreen> {
  List<RuleFile> _rules = [];
  RuleFile? _selectedRule;
  String? _content;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadRules();
  }

  Future<void> _loadRules() async {
    setState(() => _loading = true);
    final rules = await widget.notifier.listRules();
    if (mounted) {
      setState(() {
        _rules = rules;
        _loading = false;
      });
      if (rules.isNotEmpty) _selectRule(rules.first);
    }
  }

  Future<void> _selectRule(RuleFile rule) async {
    setState(() => _selectedRule = rule);
    final content = await widget.notifier.readFile(rule.path);
    if (mounted) setState(() => _content = content);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Canon Reference',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
        ),
        actions: const [
          Padding(
            padding: EdgeInsets.only(right: 16),
            child: Center(
              child: Text(
                'read-only',
                style: TextStyle(fontSize: 11, color: Color(0xFF606060)),
              ),
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _rules.isEmpty
              ? Center(
                  child: Text(
                    'No canon reference documents found',
                    style: TextStyle(color: Colors.grey[600]),
                  ),
                )
              : Row(
                  children: [
                    // Document list
                    SizedBox(
                      width: 260,
                      child: ListView.builder(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        itemCount: _rules.length,
                        itemBuilder: (context, index) {
                          final rule = _rules[index];
                          final selected = rule.name == _selectedRule?.name;
                          return ListTile(
                            dense: true,
                            selected: selected,
                            selectedTileColor:
                                Colors.indigo.withValues(alpha: 0.1),
                            leading: Icon(
                              Icons.description,
                              size: 16,
                              color: selected
                                  ? Colors.indigo[300]
                                  : Colors.grey[600],
                            ),
                            title: Text(
                              rule.name,
                              style: TextStyle(
                                fontSize: 13,
                                color: selected
                                    ? Colors.indigo[300]
                                    : Colors.grey[400],
                              ),
                            ),
                            onTap: () => _selectRule(rule),
                          );
                        },
                      ),
                    ),

                    const VerticalDivider(width: 1),

                    // Content viewer
                    Expanded(
                      child: _content == null
                          ? Center(
                              child: Text(
                                'Select a document',
                                style: TextStyle(color: Colors.grey[600]),
                              ),
                            )
                          : Padding(
                              padding: const EdgeInsets.all(16),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  // Header
                                  Container(
                                    width: double.infinity,
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 8),
                                    decoration: BoxDecoration(
                                      color: Colors.grey[850],
                                      borderRadius: const BorderRadius.vertical(
                                          top: Radius.circular(8)),
                                    ),
                                    child: Text(
                                      _selectedRule!.name,
                                      style: const TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ),
                                  // Content
                                  Expanded(
                                    child: Container(
                                      width: double.infinity,
                                      padding: const EdgeInsets.all(12),
                                      decoration: BoxDecoration(
                                        color: Colors.grey[900],
                                        borderRadius:
                                            const BorderRadius.vertical(
                                                bottom: Radius.circular(8)),
                                      ),
                                      child: Markdown(
                                        data: _content!,
                                        selectable: true,
                                        padding: EdgeInsets.zero,
                                        styleSheet: _markdownStyle(context),
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                    ),
                  ],
                ),
    );
  }

  MarkdownStyleSheet _markdownStyle(BuildContext context) {
    return MarkdownStyleSheet(
      p: TextStyle(fontSize: 14, color: Colors.grey[300], height: 1.6),
      h1: TextStyle(
          fontSize: 22,
          fontWeight: FontWeight.w700,
          color: Colors.grey[100]),
      h2: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w600,
          color: Colors.grey[200]),
      h3: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.w600,
          color: Colors.grey[200]),
      strong: TextStyle(
          fontWeight: FontWeight.w600, color: Colors.grey[200]),
      em: TextStyle(
          fontStyle: FontStyle.italic, color: Colors.grey[300]),
      code: TextStyle(
        fontSize: 13,
        fontFamily: 'monospace',
        color: Colors.amber[200],
        backgroundColor: Colors.grey[850],
      ),
      codeblockDecoration: BoxDecoration(
        color: Colors.grey[850],
        borderRadius: BorderRadius.circular(6),
      ),
      listBullet: TextStyle(fontSize: 14, color: Colors.grey[400]),
      a: const TextStyle(color: Color(0xFF448AFF)),
    );
  }
}
