import 'package:flutter/material.dart';
import '../models/article.dart';
import '../models/pipeline_stage.dart';
import 'article_card.dart';

class StageColumn extends StatelessWidget {
  final PipelineStage stage;
  final List<Article> articles;
  final void Function(Article) onArticleTap;
  final void Function(Article)? onArticleDrop;
  final void Function(Article, ArticleAction)? onArticleAction;

  const StageColumn({
    super.key,
    required this.stage,
    required this.articles,
    required this.onArticleTap,
    this.onArticleDrop,
    this.onArticleAction,
  });

  @override
  Widget build(BuildContext context) {
    return DragTarget<Article>(
      onWillAcceptWithDetails: (details) =>
          details.data.stage != stage,
      onAcceptWithDetails: (details) =>
          onArticleDrop?.call(details.data),
      builder: (context, candidateData, rejectedData) {
        final isHovering = candidateData.isNotEmpty;
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 4),
          decoration: BoxDecoration(
            color: isHovering
                ? stage.color.withValues(alpha: 0.08)
                : const Color(0xFF141414),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isHovering
                  ? stage.color.withValues(alpha: 0.4)
                  : const Color(0xFF1E1E1E),
              width: 1,
            ),
          ),
          child: Column(
            children: [
              // Header
              Padding(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                child: Row(
                  children: [
                    Container(
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: stage.color,
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      stage.label.toUpperCase(),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                        color: stage.color.withValues(alpha: 0.8),
                        letterSpacing: 1.2,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      '${articles.length}',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: stage.color.withValues(alpha: 0.5),
                      ),
                    ),
                  ],
                ),
              ),

              // Thin separator
              Container(
                height: 1,
                color: const Color(0xFF1E1E1E),
              ),

              // Article list
              Expanded(
                child: articles.isEmpty
                    ? Center(
                        child: Text(
                          isHovering ? 'Drop here' : '',
                          style: TextStyle(
                            fontSize: 11,
                            color: isHovering
                                ? stage.color.withValues(alpha: 0.6)
                                : const Color(0xFF404040),
                          ),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(
                            vertical: 6, horizontal: 4),
                        itemCount: articles.length,
                        itemBuilder: (context, index) {
                          final article = articles[index];
                          return Draggable<Article>(
                            data: article,
                            feedback: Material(
                              color: Colors.transparent,
                              child: SizedBox(
                                width: 200,
                                child: Opacity(
                                  opacity: 0.85,
                                  child: ArticleCard(
                                    article: article,
                                    onTap: () {},
                                  ),
                                ),
                              ),
                            ),
                            childWhenDragging: Opacity(
                              opacity: 0.25,
                              child: ArticleCard(
                                article: article,
                                onTap: () {},
                              ),
                            ),
                            child: ArticleCard(
                              article: article,
                              onTap: () => onArticleTap(article),
                              onAction: onArticleAction != null
                                  ? (action) =>
                                      onArticleAction!(article, action)
                                  : null,
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),
        );
      },
    );
  }
}
