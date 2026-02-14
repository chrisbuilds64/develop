import 'package:flutter/material.dart';
import '../models/article.dart';
import '../models/pipeline_stage.dart';

class MoveButtons extends StatelessWidget {
  final Article article;
  final void Function(PipelineStage target) onMove;

  const MoveButtons({
    super.key,
    required this.article,
    required this.onMove,
  });

  @override
  Widget build(BuildContext context) {
    final prev = article.stage.previous;
    final next = article.stage.next;

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        if (prev != null)
          OutlinedButton.icon(
            onPressed: () => _confirmMove(context, prev),
            icon: const Icon(Icons.arrow_back, size: 14),
            label: Text(prev.label, style: const TextStyle(fontSize: 11)),
            style: OutlinedButton.styleFrom(
              foregroundColor: prev.color,
              side: BorderSide(color: prev.color.withValues(alpha: 0.5)),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            ),
          ),
        if (next != null)
          FilledButton.icon(
            onPressed: () => _confirmMove(context, next),
            icon: const Icon(Icons.arrow_forward, size: 14),
            label: Text(next.label, style: const TextStyle(fontSize: 11)),
            style: FilledButton.styleFrom(
              backgroundColor: next.color,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            ),
          ),
      ],
    );
  }

  void _confirmMove(BuildContext context, PipelineStage target) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Move Article'),
        content: Text(
            'Move "${article.displayTitle}" to ${target.label}?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              onMove(target);
            },
            style: FilledButton.styleFrom(backgroundColor: target.color),
            child: const Text('Move'),
          ),
        ],
      ),
    );
  }
}
