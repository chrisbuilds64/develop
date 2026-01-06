import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/video.dart';
import '../config/environment.dart';
import 'auth_service.dart';

/// Service for managing videos via backend API
class VideoService {
  // Backend URL from environment configuration
  static String get baseUrl => Environment.baseUrl;

  // Auth service for getting tokens
  final _authService = AuthService();

  /// Save a new video with tags
  Future<Video> saveVideo(String url, List<String> tags) async {
    final authHeaders = await _authService.getAuthHeaders();

    final response = await http.post(
      Uri.parse('$baseUrl/videos'),
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders, // Include auth token
      },
      body: jsonEncode({
        'url': url,
        'tags': tags,
      }),
    );

    if (response.statusCode == 201) {
      return Video.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to save video: ${response.body}');
    }
  }

  /// Get all videos
  Future<List<Video>> getVideos() async {
    final authHeaders = await _authService.getAuthHeaders();

    final response = await http.get(
      Uri.parse('$baseUrl/videos'),
      headers: authHeaders,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final List<dynamic> videosJson = data['videos'];
      return videosJson.map((json) => Video.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load videos');
    }
  }

  /// Get videos filtered by tags
  Future<List<Video>> getVideosByTags(List<String> tags) async {
    final authHeaders = await _authService.getAuthHeaders();
    final tagsParam = tags.join(',');

    final response = await http.get(
      Uri.parse('$baseUrl/videos?tags=$tagsParam'),
      headers: authHeaders,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final List<dynamic> videosJson = data['videos'];
      return videosJson.map((json) => Video.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load videos');
    }
  }

  /// Get all unique tags (for autocomplete)
  Future<List<String>> getTags() async {
    final authHeaders = await _authService.getAuthHeaders();

    final response = await http.get(
      Uri.parse('$baseUrl/tags'),
      headers: authHeaders,
    );

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      final List<dynamic> tagsJson = data['tags'];
      return tagsJson.map((tag) => tag.toString()).toList();
    } else {
      throw Exception('Failed to load tags');
    }
  }

  /// Update a video's tags
  Future<Video> updateVideo(int id, String url, List<String> tags) async {
    final authHeaders = await _authService.getAuthHeaders();

    final response = await http.put(
      Uri.parse('$baseUrl/videos/$id'),
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
      },
      body: jsonEncode({
        'url': url,
        'tags': tags,
      }),
    );

    if (response.statusCode == 200) {
      return Video.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to update video: ${response.body}');
    }
  }

  /// Delete a video
  Future<void> deleteVideo(int id) async {
    final authHeaders = await _authService.getAuthHeaders();

    final response = await http.delete(
      Uri.parse('$baseUrl/videos/$id'),
      headers: authHeaders,
    );

    if (response.statusCode != 204) {
      throw Exception('Failed to delete video');
    }
  }
}
