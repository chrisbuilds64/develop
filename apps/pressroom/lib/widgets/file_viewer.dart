import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_widget_from_html_core/flutter_widget_from_html_core.dart';

class FileViewer extends StatelessWidget {
  final String fileName;
  final String content;

  const FileViewer({
    super.key,
    required this.fileName,
    required this.content,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // File name header
        Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.grey[850],
            borderRadius:
                const BorderRadius.vertical(top: Radius.circular(8)),
          ),
          child: Text(
            fileName,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              fontFamily: 'monospace',
            ),
          ),
        ),

        // Content
        Expanded(
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey[900],
              borderRadius:
                  const BorderRadius.vertical(bottom: Radius.circular(8)),
            ),
            child: _isMarkdown(fileName)
                ? Markdown(
                    data: content,
                    selectable: true,
                    padding: EdgeInsets.zero,
                    styleSheet: _markdownStyle(context),
                  )
                : _isHtml(fileName)
                    ? SingleChildScrollView(
                        child: HtmlWidget(
                          content,
                          textStyle: TextStyle(
                            fontSize: 14,
                            color: Colors.grey[300],
                            height: 1.6,
                          ),
                        ),
                      )
                    : SelectableText(
                        content,
                        style: TextStyle(
                          fontSize: 13,
                          fontFamily: _isCode(fileName) ? 'monospace' : null,
                          color: Colors.grey[300],
                          height: 1.5,
                        ),
                      ),
          ),
        ),
      ],
    );
  }

  bool _isMarkdown(String name) => name.endsWith('.md');

  bool _isHtml(String name) => name.endsWith('.html');

  bool _isCode(String name) {
    return name.endsWith('.json') ||
        name.endsWith('.svg') ||
        name.endsWith('.sh');
  }

  MarkdownStyleSheet _markdownStyle(BuildContext context) {
    return MarkdownStyleSheet(
      p: TextStyle(fontSize: 14, color: Colors.grey[300], height: 1.6),
      h1: TextStyle(
          fontSize: 24,
          fontWeight: FontWeight.w700,
          color: Colors.grey[100]),
      h2: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: Colors.grey[200]),
      h3: TextStyle(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          color: Colors.grey[200]),
      h4: TextStyle(
          fontSize: 15,
          fontWeight: FontWeight.w600,
          color: Colors.grey[300]),
      blockquoteDecoration: BoxDecoration(
        border: Border(
          left: BorderSide(color: Colors.grey[600]!, width: 3),
        ),
      ),
      blockquotePadding: const EdgeInsets.only(left: 12),
      code: TextStyle(
        fontSize: 13,
        fontFamily: 'monospace',
        color: Colors.amber[200],
        backgroundColor: Colors.grey[850],
      ),
      codeblockDecoration: BoxDecoration(
        color: Colors.grey[850],
        borderRadius: BorderRadius.circular(6),
      ),
      codeblockPadding: const EdgeInsets.all(12),
      listBullet:
          TextStyle(fontSize: 14, color: Colors.grey[400]),
      horizontalRuleDecoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: Colors.grey[700]!, width: 1),
        ),
      ),
      strong: TextStyle(
          fontWeight: FontWeight.w600, color: Colors.grey[200]),
      em: TextStyle(
          fontStyle: FontStyle.italic, color: Colors.grey[300]),
      a: const TextStyle(color: Color(0xFF448AFF)),
    );
  }
}
