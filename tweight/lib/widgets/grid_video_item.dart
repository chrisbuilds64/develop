import 'package:flutter/material.dart';
import '../models/video.dart';

/// Grid video item - pure thumbnails (like YouTube grid)
/// Maximum density, visual browsing
class GridVideoItem extends StatelessWidget {
  final Video video;
  final VoidCallback onTap;
  final VoidCallback? onEdit;
  final VoidCallback? onDelete;

  const GridVideoItem({
    super.key,
    required this.video,
    required this.onTap,
    this.onEdit,
    this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      onLongPress: () {
        // Show options menu on long press
        showModalBottomSheet(
          context: context,
          builder: (context) => SafeArea(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (onEdit != null)
                  ListTile(
                    leading: const Icon(Icons.edit),
                    title: const Text('Edit tags'),
                    onTap: () {
                      Navigator.pop(context);
                      onEdit!();
                    },
                  ),
                if (onDelete != null)
                  ListTile(
                    leading: const Icon(Icons.delete, color: Colors.red),
                    title: const Text('Delete', style: TextStyle(color: Colors.red)),
                    onTap: () {
                      Navigator.pop(context);
                      onDelete!();
                    },
                  ),
              ],
            ),
          ),
        );
      },
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Thumbnail (16:9 aspect ratio)
            AspectRatio(
              aspectRatio: 16 / 9,
              child: video.thumbnailUrl != null
                  ? Image.network(
                      video.thumbnailUrl!,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error, stackTrace) {
                        return Container(
                          color: Colors.grey[300],
                          child: const Icon(Icons.video_library, size: 48),
                        );
                      },
                    )
                  : Container(
                      color: Colors.grey[300],
                      child: const Icon(Icons.video_library, size: 48),
                    ),
            ),
            // Title overlay
            Padding(
              padding: const EdgeInsets.all(8.0),
              child: Text(
                video.title ?? 'Video',
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
