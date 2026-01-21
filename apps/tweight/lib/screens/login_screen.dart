import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../services/api_client.dart';
import 'items_screen.dart';

class LoginScreen extends StatefulWidget {
  final ApiClient apiClient;

  const LoginScreen({super.key, required this.apiClient});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _tokenController = TextEditingController();
  String? _error;
  bool _loading = false;

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _login(String token) async {
    if (token.isEmpty) {
      setState(() => _error = 'Please enter a token');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      widget.apiClient.setToken(token);

      // Test the token by fetching items
      await widget.apiClient.get('/api/v1/items');

      // Save token
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', token);

      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => ItemsScreen(apiClient: widget.apiClient),
          ),
        );
      }
    } on ApiException catch (e) {
      widget.apiClient.clearToken();
      setState(() {
        _error = e.statusCode == 401
            ? 'Invalid token'
            : 'Error: ${e.message}';
      });
    } catch (e) {
      widget.apiClient.clearToken();
      setState(() => _error = 'Connection error: $e');
    } finally {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('tweight'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextField(
              controller: _tokenController,
              decoration: const InputDecoration(
                labelText: 'Token',
                hintText: 'Enter your auth token',
                border: OutlineInputBorder(),
              ),
              enabled: !_loading,
            ),
            const SizedBox(height: 16),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(
                  _error!,
                  style: const TextStyle(color: Colors.red),
                ),
              ),
            ElevatedButton(
              onPressed: _loading ? null : () => _login(_tokenController.text),
              child: _loading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Login'),
            ),
            const SizedBox(height: 24),
            const Divider(),
            const SizedBox(height: 8),
            const Text(
              'Quick Login (Dev)',
              style: TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                TextButton(
                  onPressed: _loading ? null : () => _login('test-chris'),
                  child: const Text('Chris'),
                ),
                TextButton(
                  onPressed: _loading ? null : () => _login('test-lars'),
                  child: const Text('Lars'),
                ),
                TextButton(
                  onPressed: _loading ? null : () => _login('test-lily'),
                  child: const Text('Lily'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
