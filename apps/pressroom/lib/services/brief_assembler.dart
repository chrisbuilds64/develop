import 'dart:io';

import '../config.dart';
import '../models/article.dart';

class SessionContext {
  final String date;
  final String location;
  final String mood;
  final String? personalNotes;

  SessionContext({
    required this.date,
    required this.location,
    required this.mood,
    this.personalNotes,
  });
}

class BriefAssembler {
  /// Assembles a complete production prompt from all context sources.
  /// Returns a string ready to paste into Claude Chat.
  Future<String> assemble({
    required Article article,
    required SessionContext session,
  }) async {
    final buf = StringBuffer();

    buf.writeln('# PRODUCTION BRIEF');
    buf.writeln();
    buf.writeln('You are producing content for the chrisbuilds64 brand.');
    buf.writeln(
        'Generate ALL 11 deliverables listed below based on the idea, context, rules, and style references provided.');
    buf.writeln(
        'Output each file with a clear `## FILENAME` header so I can split them into separate files.');
    buf.writeln();
    buf.writeln('---');
    buf.writeln();

    // 1. Article Idea
    buf.writeln('## 1. ARTICLE IDEA');
    buf.writeln();
    final notes = await _readArticleNotes(article);
    if (notes != null) {
      buf.writeln(notes);
    } else {
      buf.writeln('Title: ${article.displayTitle}');
      if (article.track != null) buf.writeln('Track: ${article.track}');
    }
    buf.writeln();
    buf.writeln('---');
    buf.writeln();

    // 2. Session Context
    buf.writeln('## 2. SESSION CONTEXT');
    buf.writeln();
    buf.writeln('Date: ${session.date}');
    buf.writeln('Location: ${session.location}');
    buf.writeln('Mood: ${session.mood}');
    if (session.personalNotes != null &&
        session.personalNotes!.trim().isNotEmpty) {
      buf.writeln();
      buf.writeln('Personal Notes:');
      buf.writeln(session.personalNotes);
    }
    buf.writeln();
    buf.writeln('---');
    buf.writeln();

    // 3. Content Rules
    buf.writeln('## 3. CONTENT RULES');
    buf.writeln();
    final rules = await _readAllRules();
    buf.writeln(rules);
    buf.writeln();
    buf.writeln('---');
    buf.writeln();

    // 4. Content Boundaries
    buf.writeln('## 4. CONTENT BOUNDARIES');
    buf.writeln();
    final boundaries = await _readFile(Config.contentBoundariesPath);
    buf.writeln(boundaries);
    buf.writeln();
    buf.writeln('---');
    buf.writeln();

    // 5. Article Template
    buf.writeln('## 5. SUBSTACK TEMPLATE (Logbook Format)');
    buf.writeln();
    final template = await _readFile(
        '${Config.contentTemplatesPath}/ARTICLE-TEMPLATE.md');
    buf.writeln(template);
    buf.writeln();
    buf.writeln('---');
    buf.writeln();

    // 6. Style References
    buf.writeln('## 6. STYLE REFERENCES (Gold Standard)');
    buf.writeln();
    buf.writeln(
        'These are the 3 best published articles. Match this quality, voice, and structure.');
    buf.writeln();
    for (final ref in Config.goldStandardArticles) {
      final refContent = await _readGoldStandard(ref);
      if (refContent != null) {
        buf.writeln('### Reference: $ref');
        buf.writeln();
        buf.writeln(refContent);
        buf.writeln();
      }
    }
    buf.writeln('---');
    buf.writeln();

    // 7. Deliverables
    buf.writeln('## 7. DELIVERABLES TO PRODUCE');
    buf.writeln();
    buf.writeln('Generate each of these files. Use `## FILENAME` as header.');
    buf.writeln();
    buf.writeln('1. **substack.md** -- Full newsletter article in Logbook format (see template + references)');
    buf.writeln('   - Section headers in CAPS');
    buf.writeln('   - Sign-off with --Chris');
    buf.writeln('   - Personal, deep, specific -- not generic advice');
    buf.writeln();
    buf.writeln('2. **substack.html** -- HTML version of the newsletter');
    buf.writeln();
    buf.writeln('3. **linkedin-post.txt** -- Max 3000 chars');
    buf.writeln('   - MUST be a separate narrative, NOT a compressed Substack');
    buf.writeln('   - Mixed rhythm (short lines for hook/punchline, normal paragraphs for substance)');
    buf.writeln('   - NO link in post body (link goes in first comment)');
    buf.writeln('   - End with engaging question');
    buf.writeln('   - NO teaser tone ("want more? check Substack")');
    buf.writeln();
    buf.writeln('4. **first-comment.txt** -- Curiosity/identification hook');
    buf.writeln('   - NEVER "full article here" or promotional');
    buf.writeln('   - Should trigger curiosity or identification');
    buf.writeln('   - Include Substack link naturally');
    buf.writeln();
    buf.writeln('5. **linkedin-article.txt** -- Substack format adapted for LinkedIn');
    buf.writeln('   - Shorter paragraphs, stronger opening');
    buf.writeln('   - Soft Substack reference at end');
    buf.writeln();
    buf.writeln('6. **linkedin-article.html** -- HTML version of LinkedIn article');
    buf.writeln();
    buf.writeln('7. **tiktok-script.txt** -- Include:');
    buf.writeln('   - Script (what to say)');
    buf.writeln('   - Teleprompter version (shorter phrases)');
    buf.writeln('   - Caption (= Instagram caption, one for both)');
    buf.writeln();
    buf.writeln('8. **dalle-prompt.txt** -- 16:9 image');
    buf.writeln('   - Creative visual metaphor (NEVER "man at laptop")');
    buf.writeln('   - Space for title overlay top-left');
    buf.writeln('   - "Header image for LinkedIn post and Substack article"');
    buf.writeln();
    buf.writeln('9. **title-dark.svg** -- Title overlay for dark backgrounds');
    buf.writeln();
    buf.writeln('10. **title-light.svg** -- Title overlay for light backgrounds');
    buf.writeln();
    buf.writeln('11. **meta.json** -- Full metadata:');
    buf.writeln('    ```json');
    buf.writeln('    {');
    buf.writeln('      "day": XXX,');
    buf.writeln('      "title": "...",');
    buf.writeln('      "subtitle": "...",');
    buf.writeln('      "slug": "...",');
    buf.writeln('      "created": "${session.date}",');
    buf.writeln('      "status": "draft",');
    buf.writeln('      "track": "...",');
    buf.writeln('      "mood": "${session.mood}",');
    buf.writeln('      "location": "${session.location}",');
    buf.writeln('      "tags": [...],');
    buf.writeln('      "platforms": { "linkedin": false, "substack": false, "tiktok": false, "instagram": false },');
    buf.writeln('      "core_message": "...",');
    buf.writeln('      "cta_type": "question"');
    buf.writeln('    }');
    buf.writeln('    ```');
    buf.writeln();
    buf.writeln('---');
    buf.writeln();
    buf.writeln('## IMPORTANT RULES');
    buf.writeln();
    buf.writeln('- ALL content in ENGLISH');
    buf.writeln('- Substack = MASTER content (written first, everything derives from it)');
    buf.writeln('- LinkedIn Post = SEPARATE narrative (same core, different form, must stand alone)');
    buf.writeln('- LinkedIn Article = Substack adapted for LinkedIn (shorter paragraphs, stronger opening)');
    buf.writeln('- Check Content Boundaries before every piece');
    buf.writeln('- Voice: Personal, experienced (40 years in tech), honest, no bullshit, specific not generic');

    return buf.toString();
  }

  Future<String?> _readArticleNotes(Article article) async {
    if (article.isStandaloneFile) {
      return _readFile(article.absolutePath);
    }
    final notesFile = File('${article.absolutePath}/notes.md');
    if (await notesFile.exists()) {
      return notesFile.readAsString();
    }
    return null;
  }

  Future<String> _readAllRules() async {
    final dir = Directory(Config.contentRulesPath);
    if (!await dir.exists()) return '[No rules found]';

    final buf = StringBuffer();
    final entities = await dir.list().toList();
    entities.sort(
        (a, b) => a.path.split('/').last.compareTo(b.path.split('/').last));

    for (final entity in entities) {
      if (entity is File && !entity.path.split('/').last.startsWith('.')) {
        final name = entity.path.split('/').last;
        final content = await entity.readAsString();
        buf.writeln('### $name');
        buf.writeln();
        buf.writeln(content);
        buf.writeln();
      }
    }
    return buf.toString();
  }

  Future<String?> _readGoldStandard(String folderName) async {
    final basePath =
        '${Config.contentFlowPath}/60-published/$folderName';
    final dir = Directory(basePath);
    if (!await dir.exists()) return null;

    final buf = StringBuffer();

    // Read substack.md (or source.md)
    for (final name in ['substack.md', 'source.md']) {
      final file = File('$basePath/$name');
      if (await file.exists()) {
        buf.writeln('**Substack ($name):**');
        buf.writeln();
        buf.writeln(await file.readAsString());
        buf.writeln();
        break;
      }
    }

    // Read linkedin-post.txt
    final linkedinFile = File('$basePath/linkedin-post.txt');
    if (await linkedinFile.exists()) {
      buf.writeln('**LinkedIn Post:**');
      buf.writeln();
      buf.writeln(await linkedinFile.readAsString());
      buf.writeln();
    }

    return buf.isEmpty ? null : buf.toString();
  }

  Future<String> _readFile(String path) async {
    final file = File(path);
    if (!await file.exists()) return '[File not found: $path]';
    return file.readAsString();
  }
}
