class Item {
  final String id;
  final String ownerId;
  final String label;
  final String contentType;
  final Map<String, dynamic>? payload;
  final List<String> tags;
  final DateTime createdAt;
  final DateTime? updatedAt;

  Item({
    required this.id,
    required this.ownerId,
    required this.label,
    required this.contentType,
    this.payload,
    required this.tags,
    required this.createdAt,
    this.updatedAt,
  });

  factory Item.fromJson(Map<String, dynamic> json) {
    return Item(
      id: json['id'],
      ownerId: json['owner_id'],
      label: json['label'],
      contentType: json['content_type'],
      payload: json['payload'],
      tags: List<String>.from(json['tags'] ?? []),
      createdAt: DateTime.parse(json['created_at']),
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'])
          : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'label': label,
      'content_type': contentType,
      if (payload != null) 'payload': payload,
      'tags': tags,
    };
  }
}
