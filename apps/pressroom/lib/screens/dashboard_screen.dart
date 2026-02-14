import 'package:flutter/material.dart';
import '../models/article.dart';
import '../models/pipeline_stage.dart';
import '../services/pipeline_notifier.dart';
import '../widgets/article_card.dart';
import '../widgets/stage_column.dart';
import 'article_detail_screen.dart';
import 'idea_editor_screen.dart';
import 'produce_screen.dart';
import 'rules_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final PipelineNotifier _notifier = PipelineNotifier();

  @override
  void initState() {
    super.initState();
    _notifier.addListener(_onNotifierChange);
    _notifier.refresh();
  }

  @override
  void dispose() {
    _notifier.removeListener(_onNotifierChange);
    _notifier.dispose();
    super.dispose();
  }

  void _onNotifierChange() {
    if (mounted) setState(() {});
  }

  void _openArticle(Article article) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ArticleDetailScreen(
          article: article,
          notifier: _notifier,
        ),
      ),
    ).then((_) => _notifier.refresh());
  }

  void _openIdeaEditor() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => IdeaEditorScreen(notifier: _notifier),
      ),
    ).then((created) {
      if (created == true) _notifier.refresh();
    });
  }

  void _openRules() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => RulesScreen(notifier: _notifier),
      ),
    );
  }

  void _openProduce(Article article) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ProduceScreen(
          article: article,
          notifier: _notifier,
        ),
      ),
    ).then((_) => _notifier.refresh());
  }

  void _handleArticleAction(Article article, ArticleAction action) {
    switch (action) {
      case ArticleAction.produce:
        _openProduce(article);
      case ArticleAction.moveNext:
        if (article.stage.next != null) {
          _notifier.moveArticle(article, article.stage.next!);
        }
      case ArticleAction.movePrev:
        if (article.stage.previous != null) {
          _notifier.moveArticle(article, article.stage.previous!);
        }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Column(
        children: [
          // Header
          Container(
            padding: const EdgeInsets.fromLTRB(24, 18, 24, 14),
            decoration: const BoxDecoration(
              color: Color(0xFF111111),
              border: Border(
                bottom: BorderSide(color: Color(0xFF1E1E1E), width: 1),
              ),
            ),
            child: Row(
              children: [
                // Logo + Title
                ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: Image.asset('assets/logo.png', width: 40, height: 40),
                ),
                const SizedBox(width: 14),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'PressRoom',
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 22,
                        letterSpacing: -0.5,
                        color: Color(0xFFF5F5F5),
                      ),
                    ),
                    if (!_notifier.loading)
                      Text(
                        '${_notifier.totalArticles} articles in pipeline',
                        style: const TextStyle(
                          fontSize: 11,
                          color: Color(0xFF606060),
                          fontWeight: FontWeight.w400,
                        ),
                      ),
                  ],
                ),
                const Spacer(),
                // Actions
                if (_notifier.loading)
                  const Padding(
                    padding: EdgeInsets.only(right: 12),
                    child: SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Color(0xFF525252),
                      ),
                    ),
                  ),
                _ActionButton(
                  icon: Icons.add_rounded,
                  label: 'New Idea',
                  color: const Color(0xFF7C4DFF),
                  onPressed: _openIdeaEditor,
                ),
                const SizedBox(width: 8),
                _IconAction(
                  icon: Icons.menu_book_rounded,
                  tooltip: 'Rules',
                  onPressed: _openRules,
                ),
                const SizedBox(width: 4),
                _IconAction(
                  icon: Icons.refresh_rounded,
                  tooltip: 'Refresh',
                  onPressed: _notifier.refresh,
                ),
              ],
            ),
          ),

          // Error bar
          if (_notifier.error != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: const Color(0xFF7F1D1D),
              child: Row(
                children: [
                  const Icon(Icons.error_outline,
                      size: 14, color: Color(0xFFFCA5A5)),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _notifier.error!,
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFFFCA5A5)),
                    ),
                  ),
                ],
              ),
            ),

          // Kanban board
          Expanded(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(8, 8, 8, 8),
              child: Row(
                children: PipelineStage.values.map((stage) {
                  return Expanded(
                    child: StageColumn(
                      stage: stage,
                      articles: _notifier.articlesForStage(stage),
                      onArticleTap: _openArticle,
                      onArticleDrop: (article) =>
                          _notifier.moveArticle(article, stage),
                      onArticleAction: _handleArticleAction,
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onPressed;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return TextButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, size: 16, color: color),
      label: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
      style: TextButton.styleFrom(
        backgroundColor: color.withValues(alpha: 0.1),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    );
  }
}

class _IconAction extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onPressed;

  const _IconAction({
    required this.icon,
    required this.tooltip,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return IconButton(
      icon: Icon(icon, size: 18, color: const Color(0xFF737373)),
      tooltip: tooltip,
      onPressed: onPressed,
      style: IconButton.styleFrom(
        padding: const EdgeInsets.all(8),
      ),
    );
  }
}
