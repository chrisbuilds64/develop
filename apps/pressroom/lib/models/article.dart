import 'pipeline_stage.dart';
import 'article_meta.dart';

class Article {
  final String folderName;
  final String absolutePath;
  final PipelineStage stage;
  final ArticleMeta? meta;
  final List<String> files;
  final bool isStandaloneFile;

  Article({
    required this.folderName,
    required this.absolutePath,
    required this.stage,
    this.meta,
    this.files = const [],
    this.isStandaloneFile = false,
  });

  String get displayTitle => meta?.title ?? _titleFromFolder();

  int? get dayNumber => meta?.day ?? _dayFromFolder();

  String? get track => meta?.track;

  String? get mood => meta?.mood;

  double get completeness => _calculateCompleteness();

  int get fileCount => files.length;

  String _titleFromFolder() {
    // DAY-032-40-Years-Same-Bugs -> 40 Years Same Bugs
    final parts = folderName.split('-');
    if (parts.length > 2 && parts[0] == 'DAY') {
      return parts.sublist(2).join(' ');
    }
    if (parts.length > 2 && (parts[0] == 'VID' || parts[0] == 'TOP' ||
        parts[0] == 'SPECIAL' || parts[0] == 'FEATURED' || parts[0] == 'WEEK')) {
      return parts.sublist(2).join(' ');
    }
    return folderName.replaceAll('-', ' ');
  }

  int? _dayFromFolder() {
    final match = RegExp(r'^DAY-(\d+)').firstMatch(folderName);
    if (match != null) return int.tryParse(match.group(1)!);
    return null;
  }

  String? get prefix {
    final match = RegExp(r'^([A-Z]+-\d+)').firstMatch(folderName);
    return match?.group(1);
  }

  double _calculateCompleteness() {
    if (isStandaloneFile) return 0.0;

    final expected = expectedDeliverables;
    if (expected.isEmpty) return 0.0;

    int found = 0;
    for (final file in expected) {
      if (files.contains(file)) found++;
    }
    return found / expected.length;
  }

  /// Label-aware canonical deliverable set. POD (podcast) has a different set
  /// than the essay pipeline (FN / WN / default). Kept in sync with the
  /// canonical hierarchy (Tier 5) and the /interpret POD branch.
  List<String> get expectedDeliverables {
    const podcast = [
      'script.md',
      'teleprompter.txt',
      'show-notes.txt',
      'edit-instructions.txt',
      'linkedin-post.txt',
      'first-comment.txt',
      'visual-brief.md',
      'meta.json',
      'validation.md',
    ];
    const essay = [
      'source.md',
      'interpretation.md',
      'substack.md',
      'substack.html',
      'linkedin-post.txt',
      'first-comment.txt',
      'visual-brief.md',
      'meta.json',
      'validation.md',
    ];
    return _labelType() == 'POD' ? podcast : essay;
  }

  /// The alphabetic label prefix (FN, POD, WN, …), or null if none.
  String? _labelType() {
    final match = RegExp(r'^([A-Z]+)-').firstMatch(folderName);
    return match?.group(1);
  }
}
