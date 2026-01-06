import 'package:flutter/material.dart';

/// View modes for video list display
enum ViewMode {
  card,    // Current: Full card with thumbnail, title, tags, date
  compact, // Compact: Title and tags only (no thumbnail)
  grid,    // Grid: Pure thumbnails (like YouTube grid)
}

extension ViewModeExtension on ViewMode {
  String get displayName {
    switch (this) {
      case ViewMode.card:
        return 'Card';
      case ViewMode.compact:
        return 'Compact';
      case ViewMode.grid:
        return 'Grid';
    }
  }

  IconData get icon {
    switch (this) {
      case ViewMode.card:
        return Icons.view_agenda; // Card view icon
      case ViewMode.compact:
        return Icons.view_list;   // List view icon
      case ViewMode.grid:
        return Icons.grid_view;   // Grid view icon
    }
  }
}
