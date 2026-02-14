import 'package:flutter/foundation.dart';

import '../models/article.dart';
import '../models/pipeline_stage.dart';
import 'filesystem_service.dart';

class PipelineNotifier extends ChangeNotifier {
  final FilesystemService _fs;

  Map<PipelineStage, List<Article>> _pipeline = {};
  bool _loading = false;
  String? _error;

  PipelineNotifier({FilesystemService? filesystemService})
      : _fs = filesystemService ?? FilesystemService();

  Map<PipelineStage, List<Article>> get pipeline => _pipeline;
  bool get loading => _loading;
  String? get error => _error;

  int get totalArticles =>
      _pipeline.values.fold(0, (sum, list) => sum + list.length);

  List<Article> articlesForStage(PipelineStage stage) =>
      _pipeline[stage] ?? [];

  Future<void> refresh() async {
    _loading = true;
    _error = null;
    notifyListeners();

    try {
      _pipeline = await _fs.scanPipeline();
    } catch (e) {
      _error = e.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> moveArticle(Article article, PipelineStage target) async {
    try {
      await _fs.moveArticle(article, target);
      await refresh();
    } catch (e) {
      _error = 'Move failed: $e';
      notifyListeners();
    }
  }

  Future<String> readFile(String path) => _fs.readFile(path);

  Future<void> createIdea(String folderName, String content) async {
    try {
      await _fs.createIdea(folderName, content);
      await refresh();
    } catch (e) {
      _error = 'Create failed: $e';
      notifyListeners();
    }
  }

  Future<List<RuleFile>> listRules() => _fs.listRules();

  Future<void> writeFile(String path, String content) =>
      _fs.writeFile(path, content);
}
