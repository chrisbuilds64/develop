import '../models/item.dart';
import 'api_client.dart';

class ItemService {
  final ApiClient _client;

  ItemService(this._client);

  Future<List<Item>> getItems({String? search, List<String>? tags}) async {
    final queryParams = <String, String>{};
    if (search != null && search.isNotEmpty) {
      queryParams['search'] = search;
    }
    if (tags != null && tags.isNotEmpty) {
      queryParams['tags'] = tags.join(',');
    }

    String path = '/api/v1/items';
    if (queryParams.isNotEmpty) {
      path += '?${queryParams.entries.map((e) => '${e.key}=${Uri.encodeComponent(e.value)}').join('&')}';
    }

    final response = await _client.get(path);
    final items = response['items'] as List;
    return items.map((json) => Item.fromJson(json)).toList();
  }

  Future<Item> getItem(String id) async {
    final response = await _client.get('/api/v1/items/$id');
    return Item.fromJson(response);
  }

  Future<Item> createItem({
    required String label,
    required String contentType,
    Map<String, dynamic>? payload,
    List<String>? tags,
  }) async {
    final response = await _client.post('/api/v1/items', {
      'label': label,
      'content_type': contentType,
      if (payload != null) 'payload': payload,
      'tags': tags ?? [],
    });
    return Item.fromJson(response);
  }

  Future<Item> updateItem(
    String id, {
    String? label,
    String? contentType,
    Map<String, dynamic>? payload,
    List<String>? tags,
  }) async {
    final data = <String, dynamic>{};
    if (label != null) data['label'] = label;
    if (contentType != null) data['content_type'] = contentType;
    if (payload != null) data['payload'] = payload;
    if (tags != null) data['tags'] = tags;

    final response = await _client.put('/api/v1/items/$id', data);
    return Item.fromJson(response);
  }

  Future<void> deleteItem(String id) async {
    await _client.delete('/api/v1/items/$id');
  }
}
