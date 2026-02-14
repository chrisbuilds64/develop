import 'package:flutter/material.dart';
import '../config.dart';

enum PipelineStage {
  ideas(10, 'Ideas', '10-ideas', StageColors.ideas),
  produce(20, 'Produce', '20-produce', StageColors.produce),
  review(30, 'Review', '30-review', StageColors.review),
  reviewHuman(40, 'Human Review', '40-review-human', StageColors.reviewHuman),
  readyToPublish(
      50, 'Ready to Publish', '50-ready-to-publish', StageColors.readyToPublish),
  published(60, 'Published', '60-published', StageColors.published);

  final int order;
  final String label;
  final String dirName;
  final Color color;

  const PipelineStage(this.order, this.label, this.dirName, this.color);

  PipelineStage? get next {
    final idx = PipelineStage.values.indexOf(this);
    if (idx < PipelineStage.values.length - 1) {
      return PipelineStage.values[idx + 1];
    }
    return null;
  }

  PipelineStage? get previous {
    final idx = PipelineStage.values.indexOf(this);
    if (idx > 0) {
      return PipelineStage.values[idx - 1];
    }
    return null;
  }
}
