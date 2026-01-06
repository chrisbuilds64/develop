import 'package:flutter/material.dart';
import '../models/video.dart';

/// Compact video list item - title and tags only (no thumbnail)
/// Fits more videos on screen
class CompactVideoItem extends StatelessWidget {
  final Video video;
  final VoidCallback onTap;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  const CompactVideoItem({
    super.key,
    required this.video,
    required this.onTap,
    this.onEdit,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      onTap: onTap,
      leading: const Icon(Icons.play_circle_outline, size: 32),
      title: Text(
        video.title ?? video.url,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontWeight: FontWeight.w500),
      ),
      subtitle: video.tagsList.isNotEmpty
          ? Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Wrap(
                spacing: 4,
                runSpacing: 2,
                children: video.tagsList
                    .map((tag) => Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Theme.of(context).colorScheme.secondaryContainer,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            tag,
                            style: TextStyle(
                              fontSize: 11,
                              color: Theme.of(context).colorScheme.onSecondaryContainer,
                            ),
                          ),
                        ))
                    .toList(),
              ),
            )
          : null,
      trailing: (onEdit != null || onDelete != null)
          ? Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (onEdit != null)
                  IconButton(
                    icon: const Icon(Icons.edit_outlined),
                    onPressed: onEdit,
                    iconSize: 20,
                    tooltip: 'Edit tags',
                  ),
                if (onDelete != null)
                  IconButton(
                    icon: const Icon(Icons.delete_outline),
                    onPressed: onDelete,
                    color: Colors.red,
                    iconSize: 20,
                    tooltip: 'Delete video',
                  ),
              ],
            )
          : null,
    );
  }
}
