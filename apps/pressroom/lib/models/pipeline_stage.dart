import 'package:flutter/material.dart';
import '../config.dart';

enum PipelineStage {
  observations(5, 'Observations', '05-operational-observations', StageColors.observations),
  ideas(10, 'Ideas', '10-ideas', StageColors.ideas),
  interpretation(15, 'Interpretation', '15-interpretation', StageColors.interpretation),
  produce(20, 'Produce', '20-produce', StageColors.produce),
  reviewHuman(30, 'Review', '30-review-human', StageColors.reviewHuman),
  assetGeneration(40, 'Asset Generation', '40-asset-generation', StageColors.assetGeneration),
  readyToPublish(50, 'Ready to Publish', '50-ready-to-publish', StageColors.readyToPublish),
  published(60, 'Published', '60-published', StageColors.published),
  canonicalReview(65, 'Canonical Review', '65-canonical-review', StageColors.canonicalReview),
  referenceFrames(70, 'Reference Frames', '70-reference-frames', StageColors.referenceFrames);

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
