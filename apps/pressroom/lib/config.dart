import 'package:flutter/material.dart';

class Config {
  static const String projectRoot =
      '/Users/christianmoser/ChrisBuilds64';
  static const String contentRoot = '$projectRoot/content';
  static const String contentFlowPath = '$contentRoot/flow';
  static const String contentRulesPath = '$contentRoot/rules';
  static const String contentTemplatesPath = '$contentRoot/templates';
  static const String contentBoundariesPath =
      '$projectRoot/control/principles/CONTENT-BOUNDARIES.md';

  /// Gold standard articles for style reference (folder names in 60-published/)
  static const List<String> goldStandardArticles = [
    'DAY-032-40-Years-Same-Bugs',
    'DAY-030-Almost-Quit',
    'DAY-026-AI-Amplifies-Thinking',
  ];
}

class StageColors {
  static const ideas = Color(0xFF7C4DFF);
  static const produce = Color(0xFF448AFF);
  static const review = Color(0xFFFF9800);
  static const reviewHuman = Color(0xFFFF5722);
  static const readyToPublish = Color(0xFF4CAF50);
  static const published = Color(0xFF78909C);
}
