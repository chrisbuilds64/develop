# FLUX MCP Server

An MCP (Model Context Protocol) server for generating images via the [Black Forest Labs](https://blackforestlabs.ai) FLUX API.

Built for [PressRoom](https://github.com/chrisbuilds64/develop), an open-source editorial dashboard.

## Tools

### `generate_image`
Generate a single image with custom prompt, aspect ratio, and optional file save.

### `generate_article_images`
Generate both Substack (16:9) and LinkedIn (4:5) header images for a content article. Reads prompt files (`dalle-prompt.txt`, `dalle-linkedin-prompt.txt`) from the article folder.

## Setup

```bash
# 1. Get your API key from https://dashboard.bfl.ai

# 2. Store the key securely
echo "YOUR_KEY" > ~/.secrets/chrisbuilds64/bfl-api-key
chmod 400 ~/.secrets/chrisbuilds64/bfl-api-key

# 3. Add to Claude Code
claude mcp add --transport stdio \
  --env BFL_API_KEY="$(cat ~/.secrets/chrisbuilds64/bfl-api-key)" \
  flux-images -- node /path/to/flux-mcp-server/index.js
```

## Usage in Claude Code

Once connected, Claude can:

```
Generate the article images for DAY-042
→ Claude calls generate_article_images with the article path
→ FLUX generates 16:9 + 4:5 images
→ Images saved to article folder
```

## Models

| Model | Quality | Price |
|-------|---------|-------|
| flux-2-pro-preview | Best | ~$0.03/MP |
| flux-1.1-pro | Great | $0.04/image |
| flux-1.1-pro-ultra | Great + native aspect ratios | $0.06/image |

## License

MIT
