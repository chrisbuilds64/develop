class ArticleMeta {
  final int? day;
  final String? title;
  final String? subtitle;
  final String? slug;
  final String? created;
  final String? publishDate;
  final String? status;
  final String? track;
  final String? theme;
  final String? mood;
  final String? location;
  final List<String> tags;
  final Map<String, bool> platforms;
  final bool? boost;
  final String? coreMessage;
  final String? ctaType;

  ArticleMeta({
    this.day,
    this.title,
    this.subtitle,
    this.slug,
    this.created,
    this.publishDate,
    this.status,
    this.track,
    this.theme,
    this.mood,
    this.location,
    this.tags = const [],
    this.platforms = const {},
    this.boost,
    this.coreMessage,
    this.ctaType,
  });

  factory ArticleMeta.fromJson(Map<String, dynamic> json) {
    return ArticleMeta(
      day: json['day'] as int?,
      title: json['title'] as String?,
      subtitle: json['subtitle'] as String?,
      slug: json['slug'] as String?,
      created: (json['created'] ?? json['date']) as String?,
      publishDate: json['publish_date'] as String?,
      status: json['status'] as String?,
      track: json['track'] as String?,
      theme: json['theme'] as String?,
      mood: json['mood'] as String?,
      location: json['location'] as String?,
      tags: _parseTags(json['tags']),
      platforms: _parsePlatforms(json['platforms']),
      boost: (json['boost'] ?? json['boost_recommended']) as bool?,
      coreMessage: json['core_message'] as String?,
      ctaType: json['cta_type'] as String?,
    );
  }

  static List<String> _parseTags(dynamic raw) {
    if (raw is List) return raw.cast<String>();
    return [];
  }

  static Map<String, bool> _parsePlatforms(dynamic raw) {
    if (raw is Map) {
      return raw.map((k, v) => MapEntry(k.toString(), v == true));
    }
    return {};
  }
}
