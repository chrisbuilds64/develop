import 'dart:convert';
import 'dart:io';

import '../config.dart';
import '../models/article.dart';
import '../models/article_meta.dart';
import '../models/pipeline_stage.dart';

class RuleFile {
  final String name;
  final String path;

  RuleFile({required this.name, required this.path});
}

class FilesystemService {
  final String contentFlowPath;
  final String contentRulesPath;

  FilesystemService({
    this.contentFlowPath = Config.contentFlowPath,
    this.contentRulesPath = Config.contentRulesPath,
  });

  Future<Map<PipelineStage, List<Article>>> scanPipeline() async {
    final pipeline = <PipelineStage, List<Article>>{};

    for (final stage in PipelineStage.values) {
      pipeline[stage] = await _scanStage(stage);
    }

    return pipeline;
  }

  Future<List<Article>> _scanStage(PipelineStage stage) async {
    final dir = Directory('$contentFlowPath/${stage.dirName}');
    if (!await dir.exists()) return [];

    final articles = <Article>[];
    final entities = await dir.list().toList();

    for (final entity in entities) {
      final name = entity.uri.pathSegments
          .where((s) => s.isNotEmpty)
          .last;

      // Skip hidden files
      if (name.startsWith('.')) continue;

      if (entity is Directory) {
        final files = await _listFiles(entity);
        final meta = await _readMeta(entity.path);
        articles.add(Article(
          folderName: name,
          absolutePath: entity.path,
          stage: stage,
          meta: meta,
          files: files,
        ));
      } else if (entity is File) {
        // Standalone files (e.g. loose .md in ideas)
        articles.add(Article(
          folderName: name,
          absolutePath: entity.path,
          stage: stage,
          files: [name],
          isStandaloneFile: true,
        ));
      }
    }

    // Sort: by day number (desc), then by name
    articles.sort((a, b) {
      final dayA = a.dayNumber ?? 0;
      final dayB = b.dayNumber ?? 0;
      if (dayA != dayB) return dayB.compareTo(dayA);
      return a.folderName.compareTo(b.folderName);
    });

    return articles;
  }

  Future<List<String>> _listFiles(Directory dir) async {
    final files = <String>[];
    await for (final entity in dir.list()) {
      if (entity is File) {
        final name = entity.uri.pathSegments
            .where((s) => s.isNotEmpty)
            .last;
        if (!name.startsWith('.')) {
          files.add(name);
        }
      }
    }
    files.sort();
    return files;
  }

  Future<ArticleMeta?> _readMeta(String dirPath) async {
    final metaFile = File('$dirPath/meta.json');
    if (!await metaFile.exists()) return null;

    try {
      final content = await metaFile.readAsString();
      final json = jsonDecode(content) as Map<String, dynamic>;
      return ArticleMeta.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  Future<String> readFile(String path) async {
    final file = File(path);
    if (!await file.exists()) return '[File not found]';
    return file.readAsString();
  }

  Future<void> moveArticle(Article article, PipelineStage target) async {
    final targetPath =
        '$contentFlowPath/${target.dirName}/${article.folderName}';

    if (article.isStandaloneFile) {
      await File(article.absolutePath).rename(targetPath);
    } else {
      await Directory(article.absolutePath).rename(targetPath);
    }
  }

  Future<void> createIdea(String folderName, String content) async {
    final dir = Directory(
        '$contentFlowPath/${PipelineStage.ideas.dirName}/$folderName');
    await dir.create(recursive: true);
    final file = File('${dir.path}/notes.md');
    await file.writeAsString(content);
  }

  Future<List<RuleFile>> listRules() async {
    final dir = Directory(contentRulesPath);
    if (!await dir.exists()) return [];

    final rules = <RuleFile>[];
    await for (final entity in dir.list()) {
      if (entity is File) {
        final name =
            entity.uri.pathSegments.where((s) => s.isNotEmpty).last;
        if (!name.startsWith('.')) {
          rules.add(RuleFile(name: name, path: entity.path));
        }
      }
    }
    rules.sort((a, b) => a.name.compareTo(b.name));
    return rules;
  }

  Future<void> writeFile(String path, String content) async {
    await File(path).writeAsString(content);
  }
}
