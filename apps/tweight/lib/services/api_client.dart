import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException: $statusCode - $message';
}

class ApiClient {
  final String baseUrl;
  String? _token;

  ApiClient({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  void setToken(String token) {
    _token = token;
  }

  void clearToken() {
    _token = null;
  }

  bool get hasToken => _token != null;

  Map<String, String> get _headers {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }
    return headers;
  }

  Future<Map<String, dynamic>> get(String path) async {
    final response = await http.get(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
    );
    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> data) async {
    final response = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
      body: jsonEncode(data),
    );
    return _handleResponse(response);
  }

  Future<Map<String, dynamic>> put(String path, Map<String, dynamic> data) async {
    final response = await http.put(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
      body: jsonEncode(data),
    );
    return _handleResponse(response);
  }

  Future<void> delete(String path) async {
    final response = await http.delete(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
    );
    if (response.statusCode != 204) {
      _handleResponse(response);
    }
  }

  Map<String, dynamic> _handleResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (response.body.isEmpty) {
        return {};
      }
      return jsonDecode(response.body);
    }

    String message;
    try {
      final body = jsonDecode(response.body);
      message = body['detail'] ?? body['message'] ?? 'Unknown error';
    } catch (_) {
      message = response.body.isNotEmpty ? response.body : 'Request failed';
    }

    throw ApiException(response.statusCode, message);
  }
}
