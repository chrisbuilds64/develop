import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'services/api_client.dart';
import 'screens/login_screen.dart';
import 'screens/items_screen.dart';

void main() {
  runApp(const TweightApp());
}

class TweightApp extends StatelessWidget {
  const TweightApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'tweight',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.blue),
        useMaterial3: true,
      ),
      home: const AuthWrapper(),
    );
  }
}

class AuthWrapper extends StatefulWidget {
  const AuthWrapper({super.key});

  @override
  State<AuthWrapper> createState() => _AuthWrapperState();
}

class _AuthWrapperState extends State<AuthWrapper> {
  final ApiClient _apiClient = ApiClient();
  bool _checking = true;
  bool _hasToken = false;

  @override
  void initState() {
    super.initState();
    _checkAuth();
  }

  Future<void> _checkAuth() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('auth_token');

    if (token != null) {
      _apiClient.setToken(token);
      setState(() {
        _hasToken = true;
        _checking = false;
      });
    } else {
      setState(() => _checking = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_checking) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (_hasToken) {
      return ItemsScreen(apiClient: _apiClient);
    }

    return LoginScreen(apiClient: _apiClient);
  }
}
