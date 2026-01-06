import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/video.dart';
import '../models/view_mode.dart';
import '../services/video_service.dart';
import '../widgets/video_card.dart';
import '../widgets/compact_video_item.dart';
import '../widgets/grid_video_item.dart';
import 'edit_video_screen.dart';

class VideoListScreen extends StatefulWidget {
  const VideoListScreen({super.key});

  @override
  State<VideoListScreen> createState() => _VideoListScreenState();
}

class _VideoListScreenState extends State<VideoListScreen> {
  final VideoService _videoService = VideoService();
  List<Video> _videos = [];
  bool _loading = true;
  String? _error;
  String? _filterTag;
  ViewMode _viewMode = ViewMode.card; // Default view mode

  @override
  void initState() {
    super.initState();
    _loadViewMode();
    _loadVideos();
  }

  Future<void> _loadViewMode() async {
    final prefs = await SharedPreferences.getInstance();
    final viewModeIndex = prefs.getInt('view_mode') ?? 0;
    setState(() {
      _viewMode = ViewMode.values[viewModeIndex];
    });
  }

  Future<void> _saveViewMode(ViewMode mode) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt('view_mode', mode.index);
    setState(() {
      _viewMode = mode;
    });
  }

  void _cycleViewMode() {
    // Cycle through view modes: Card → Compact → Grid → Card
    final currentIndex = _viewMode.index;
    final nextIndex = (currentIndex + 1) % ViewMode.values.length;
    _saveViewMode(ViewMode.values[nextIndex]);
  }

  Future<void> _loadVideos() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final videos = _filterTag == null
          ? await _videoService.getVideos()
          : await _videoService.getVideosByTags([_filterTag!]);

      setState(() {
        _videos = videos;
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _openVideo(Video video) async {
    final uri = Uri.parse(video.url);
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    } else {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Could not open video: ${video.url}')),
        );
      }
    }
  }

  Future<void> _editVideo(Video video) async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => EditVideoScreen(video: video),
      ),
    );

    // Reload videos if edit was successful
    if (result == true) {
      _loadVideos();
    }
  }

  Future<void> _deleteVideo(Video video) async {
    // Show confirmation dialog
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Video'),
        content: const Text('Are you sure you want to delete this video?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        await _videoService.deleteVideo(video.id);
        _loadVideos(); // Refresh list
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Video deleted')),
          );
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to delete: $e')),
          );
        }
      }
    }
  }

  void _showFilterDialog() {
    // Get all unique tags from videos
    final allTags = <String>{};
    for (final video in _videos) {
      allTags.addAll(video.tagsList);
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter by Tag'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('All Videos'),
              onTap: () {
                setState(() => _filterTag = null);
                Navigator.pop(context);
                _loadVideos();
              },
            ),
            const Divider(),
            ...allTags.map((tag) => ListTile(
                  title: Text(tag),
                  onTap: () {
                    setState(() => _filterTag = tag);
                    Navigator.pop(context);
                    _loadVideos();
                  },
                )),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(_filterTag == null ? 'Tweight Videos' : 'Tag: $_filterTag'),
        actions: [
          // View mode toggle
          IconButton(
            icon: Icon(_viewMode.icon),
            onPressed: _cycleViewMode,
            tooltip: 'View: ${_viewMode.displayName}',
          ),
          // Filter button
          IconButton(
            icon: const Icon(Icons.filter_list),
            onPressed: _showFilterDialog,
            tooltip: 'Filter by tag',
          ),
          // Clear filter button
          if (_filterTag != null)
            IconButton(
              icon: const Icon(Icons.clear),
              onPressed: () {
                setState(() => _filterTag = null);
                _loadVideos();
              },
              tooltip: 'Clear filter',
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 16),
            Text('Error: $_error'),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadVideos,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    if (_videos.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.video_library_outlined, size: 64, color: Colors.grey),
            const SizedBox(height: 16),
            Text(
              _filterTag == null
                  ? 'No videos yet'
                  : 'No videos with tag "$_filterTag"',
              style: const TextStyle(fontSize: 18, color: Colors.grey),
            ),
            const SizedBox(height: 8),
            const Text(
              'Share a YouTube link to Tweight to get started',
              style: TextStyle(color: Colors.grey),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadVideos,
      child: _buildVideoList(),
    );
  }

  Widget _buildVideoList() {
    switch (_viewMode) {
      case ViewMode.card:
        return _buildCardView();
      case ViewMode.compact:
        return _buildCompactView();
      case ViewMode.grid:
        return _buildGridView();
    }
  }

  Widget _buildCardView() {
    return ListView.builder(
      itemCount: _videos.length,
      itemBuilder: (context, index) {
        final video = _videos[index];
        return VideoCard(
          video: video,
          onTap: () => _openVideo(video),
          onEdit: () => _editVideo(video),
          onDelete: () => _deleteVideo(video),
        );
      },
    );
  }

  Widget _buildCompactView() {
    return ListView.builder(
      itemCount: _videos.length,
      itemBuilder: (context, index) {
        final video = _videos[index];
        return CompactVideoItem(
          video: video,
          onTap: () => _openVideo(video),
          onEdit: () => _editVideo(video),
          onDelete: () => _deleteVideo(video),
        );
      },
    );
  }

  Widget _buildGridView() {
    return GridView.builder(
      padding: const EdgeInsets.all(8),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        childAspectRatio: 16 / 12, // Slightly taller than 16:9 to fit title
        crossAxisSpacing: 8,
        mainAxisSpacing: 8,
      ),
      itemCount: _videos.length,
      itemBuilder: (context, index) {
        final video = _videos[index];
        return GridVideoItem(
          video: video,
          onTap: () => _openVideo(video),
          onEdit: () => _editVideo(video),
          onDelete: () => _deleteVideo(video),
        );
      },
    );
  }
}
