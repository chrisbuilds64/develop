import 'package:flutter/material.dart';
import '../models/article.dart';
import '../models/pipeline_stage.dart';
import 'completeness_indicator.dart';

enum ArticleAction { produce, moveNext, movePrev }

class ArticleCard extends StatelessWidget {
  final Article article;
  final VoidCallback onTap;
  final void Function(ArticleAction)? onAction;

  const ArticleCard({
    super.key,
    required this.article,
    required this.onTap,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    final stageColor = article.stage.color;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
      child: Material(
        color: const Color(0xFF1A1A1A),
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          borderRadius: BorderRadius.circular(8),
          onTap: onTap,
          hoverColor: const Color(0xFF222222),
          child: Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: const Color(0xFF262626),
                width: 1,
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Top row: prefix + menu
                Row(
                  children: [
                    if (article.prefix != null)
                      Text(
                        article.prefix!,
                        style: TextStyle(
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                          color: stageColor.withValues(alpha: 0.6),
                          letterSpacing: 0.5,
                        ),
                      ),
                    const Spacer(),
                    if (onAction != null)
                      SizedBox(
                        width: 22,
                        height: 22,
                        child: PopupMenuButton<ArticleAction>(
                          padding: EdgeInsets.zero,
                          iconSize: 14,
                          icon: Icon(Icons.more_horiz,
                              size: 14, color: Colors.grey[700]),
                          onSelected: onAction,
                          itemBuilder: (_) => _menuItems(),
                        ),
                      )
                    else if (article.fileCount > 0)
                      Text(
                        '${article.fileCount}',
                        style: TextStyle(
                            fontSize: 10, color: Colors.grey[700]),
                      ),
                  ],
                ),
                const SizedBox(height: 4),

                // Title
                Text(
                  article.displayTitle,
                  style: const TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    color: Color(0xFFD4D4D4),
                    height: 1.3,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 6),

                // Track badge
                if (article.track != null) ...[
                  _TrackBadge(track: article.track!),
                  const SizedBox(height: 6),
                ],

                // Completeness
                if (!article.isStandaloneFile)
                  CompletenessIndicator(
                    completeness: article.completeness,
                    color: stageColor,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<PopupMenuEntry<ArticleAction>> _menuItems() {
    final items = <PopupMenuEntry<ArticleAction>>[];
    final stage = article.stage;

    if (stage == PipelineStage.ideas || stage == PipelineStage.produce) {
      items.add(const PopupMenuItem(
        value: ArticleAction.produce,
        child: Row(
          children: [
            Icon(Icons.rocket_launch, size: 14),
            SizedBox(width: 8),
            Text('Produce', style: TextStyle(fontSize: 12)),
          ],
        ),
      ));
    }

    if (stage.next != null) {
      items.add(PopupMenuItem(
        value: ArticleAction.moveNext,
        child: Row(
          children: [
            const Icon(Icons.arrow_forward, size: 14),
            const SizedBox(width: 8),
            Text('Move to ${stage.next!.label}',
                style: const TextStyle(fontSize: 12)),
          ],
        ),
      ));
    }

    if (stage.previous != null) {
      items.add(PopupMenuItem(
        value: ArticleAction.movePrev,
        child: Row(
          children: [
            const Icon(Icons.arrow_back, size: 14),
            const SizedBox(width: 8),
            Text('Move to ${stage.previous!.label}',
                style: const TextStyle(fontSize: 12)),
          ],
        ),
      ));
    }

    return items;
  }
}

class _TrackBadge extends StatelessWidget {
  final String track;

  const _TrackBadge({required this.track});

  Color get _color {
    switch (track) {
      case 'deep-tech':
        return const Color(0xFF3B82F6);
      case 'clarity':
        return const Color(0xFFF59E0B);
      case 'security':
        return const Color(0xFFEF4444);
      case 'tech':
        return const Color(0xFF06B6D4);
      default:
        return const Color(0xFF737373);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Text(
      track.toUpperCase(),
      style: TextStyle(
        fontSize: 9,
        fontWeight: FontWeight.w700,
        color: _color.withValues(alpha: 0.7),
        letterSpacing: 0.8,
      ),
    );
  }
}
