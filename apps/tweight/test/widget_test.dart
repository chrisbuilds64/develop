import 'package:flutter_test/flutter_test.dart';
import 'package:tweight/main.dart';

void main() {
  testWidgets('App loads login screen', (WidgetTester tester) async {
    await tester.pumpWidget(const TweightApp());
    await tester.pumpAndSettle();

    // Check for login screen elements
    expect(find.text('tweight'), findsOneWidget);
  });
}
