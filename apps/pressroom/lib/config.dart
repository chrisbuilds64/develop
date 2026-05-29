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
    'FN-055-blind-spot-amplifier',
    'FN-056-before-the-first-prompt',
  ];
}

class StageColors {
  static const observations = Color(0xFF00ACC1);
  static const ideas = Color(0xFF7C4DFF);
  static const interpretation = Color(0xFF3949AB);
  static const produce = Color(0xFF448AFF);
  static const reviewHuman = Color(0xFFFF9800);
  static const assetGeneration = Color(0xFFFF5722);
  static const readyToPublish = Color(0xFF4CAF50);
  static const published = Color(0xFF78909C);
  static const canonicalReview = Color(0xFFFFB300);
  static const referenceFrames = Color(0xFFFF8F00);
}
