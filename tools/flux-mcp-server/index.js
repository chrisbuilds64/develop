#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "@modelcontextprotocol/sdk/zod.js";
import { writeFile, mkdir, readFile } from "fs/promises";
import { join, dirname } from "path";
import { homedir } from "os";

const BFL_API_URL = process.env.BFL_API_URL || "https://api.bfl.ai";
const POLL_INTERVAL_MS = 1000;
const MAX_POLL_ATTEMPTS = 120; // 2 minutes max

// Load API key from secrets file (preferred) or env var (fallback)
const SECRETS_PATH = join(homedir(), ".secrets", "chrisbuilds64", "bfl.api");
let BFL_API_KEY;
try {
  BFL_API_KEY = (await readFile(SECRETS_PATH, "utf-8")).trim();
} catch {
  BFL_API_KEY = process.env.BFL_API_KEY;
}

if (!BFL_API_KEY) {
  console.error(`Error: BFL API key not found at ${SECRETS_PATH} and BFL_API_KEY env var not set`);
  console.error("Get your key at https://dashboard.bfl.ai");
  process.exit(1);
}

// --- API helpers ---

async function submitGeneration(endpoint, params) {
  const res = await fetch(`${BFL_API_URL}${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      accept: "application/json",
      "x-key": BFL_API_KEY,
    },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    const body = await res.text();
    throw new Error(`FLUX API error (${res.status}): ${body}`);
  }

  return res.json();
}

async function pollResult(pollingUrl) {
  for (let i = 0; i < MAX_POLL_ATTEMPTS; i++) {
    const res = await fetch(pollingUrl, {
      headers: {
        accept: "application/json",
        "x-key": BFL_API_KEY,
      },
    });

    if (!res.ok) {
      throw new Error(`Polling error (${res.status}): ${await res.text()}`);
    }

    const data = await res.json();

    if (data.status === "Ready") {
      return data.result;
    }

    if (data.status === "Error") {
      throw new Error(`FLUX generation failed: ${data.error || "Unknown error"}`);
    }

    // Still pending, wait and retry
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
  }

  throw new Error("FLUX generation timed out after 2 minutes");
}

async function downloadImage(url, outputPath) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Download failed (${res.status})`);
  }
  const buffer = Buffer.from(await res.arrayBuffer());
  await mkdir(dirname(outputPath), { recursive: true });
  await writeFile(outputPath, buffer);
  return buffer.length;
}

// Round to nearest multiple of 16
function roundTo16(n) {
  return Math.round(n / 16) * 16;
}

// Resolve dimensions from aspect ratio string
function aspectToDimensions(aspect, maxMp = 2) {
  const [w, h] = aspect.split(":").map(Number);
  const ratio = w / h;
  const maxPixels = maxMp * 1_000_000;
  const height = roundTo16(Math.sqrt(maxPixels / ratio));
  const width = roundTo16(height * ratio);
  return { width, height };
}

// --- MCP Server ---

const server = new McpServer({
  name: "flux-image-generator",
  version: "1.0.0",
});

server.tool(
  "generate_image",
  "Generate an image using Black Forest Labs FLUX API. Returns the image URL and optionally saves to disk.",
  {
    prompt: z.string().describe("Text description of the image to generate"),
    aspect_ratio: z
      .string()
      .default("16:9")
      .describe("Aspect ratio (e.g. '16:9', '4:5', '1:1', '9:16')"),
    output_path: z
      .string()
      .optional()
      .describe("Absolute file path to save the image (e.g. /path/to/image.jpg). If omitted, returns URL only."),
    model: z
      .enum(["flux-2-pro-preview", "flux-1.1-pro", "flux-1.1-pro-ultra"])
      .default("flux-2-pro-preview")
      .describe("FLUX model to use"),
    output_format: z
      .enum(["jpeg", "png"])
      .default("jpeg")
      .describe("Output image format"),
  },
  async ({ prompt, aspect_ratio, output_path, model, output_format }) => {
    try {
      let endpoint;
      let params;

      if (model === "flux-1.1-pro-ultra") {
        // Ultra uses aspect_ratio string directly
        endpoint = "/v1/flux-pro-1.1-ultra";
        params = {
          prompt,
          aspect_ratio,
          output_format,
          safety_tolerance: 2,
        };
      } else if (model === "flux-1.1-pro") {
        endpoint = "/v1/flux-pro-1.1";
        const dims = aspectToDimensions(aspect_ratio);
        params = {
          prompt,
          width: dims.width,
          height: dims.height,
          output_format,
          safety_tolerance: 2,
        };
      } else {
        // flux-2-pro-preview (default)
        endpoint = "/v1/flux-2-pro-preview";
        const dims = aspectToDimensions(aspect_ratio);
        params = {
          prompt,
          width: dims.width,
          height: dims.height,
          output_format,
          safety_tolerance: 2,
        };
      }

      // Step 1: Submit
      const submission = await submitGeneration(endpoint, params);
      const pollingUrl = submission.polling_url;

      if (!pollingUrl) {
        throw new Error("No polling URL returned from FLUX API");
      }

      // Step 2: Poll
      const result = await pollResult(pollingUrl);
      const imageUrl = result.sample;

      if (!imageUrl) {
        throw new Error("No image URL in FLUX result");
      }

      // Step 3: Optionally save
      let savedInfo = "";
      if (output_path) {
        const bytes = await downloadImage(imageUrl, output_path);
        savedInfo = `\nSaved to: ${output_path} (${(bytes / 1024).toFixed(0)} KB)`;
      }

      const dimsInfo =
        model === "flux-1.1-pro-ultra"
          ? `Aspect: ${aspect_ratio}`
          : `Dimensions: ${params.width}x${params.height}`;

      return {
        content: [
          {
            type: "text",
            text: `Image generated successfully.\nModel: ${model}\n${dimsInfo}\nFormat: ${output_format}\nURL: ${imageUrl}${savedInfo}\n\nNote: URL expires in 10 minutes. ${output_path ? "Image has been saved to disk." : "Use output_path to save to disk."}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error generating image: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

server.tool(
  "generate_article_images",
  "Generate both Substack (16:9) and LinkedIn (4:5) images for a content article. Reads the DALL-E prompt files from the article folder and generates images via FLUX.",
  {
    article_path: z
      .string()
      .describe("Absolute path to the article folder (e.g. /path/to/DAY-042-The-Skill-Layer)"),
    model: z
      .enum(["flux-2-pro-preview", "flux-1.1-pro", "flux-1.1-pro-ultra"])
      .default("flux-2-pro-preview")
      .describe("FLUX model to use"),
  },
  async ({ article_path, model }) => {
    try {
      const results = [];

      // Read prompt files
      const substackPromptPath = join(article_path, "dalle-prompt.txt");
      const linkedinPromptPath = join(article_path, "dalle-linkedin-prompt.txt");

      let substackPrompt, linkedinPrompt;

      try {
        const { readFile } = await import("fs/promises");
        substackPrompt = await readFile(substackPromptPath, "utf-8");
      } catch {
        results.push("Warning: dalle-prompt.txt not found, skipping Substack image");
      }

      try {
        const { readFile } = await import("fs/promises");
        linkedinPrompt = await readFile(linkedinPromptPath, "utf-8");
      } catch {
        results.push("Warning: dalle-linkedin-prompt.txt not found, skipping LinkedIn image");
      }

      // Generate Substack image (16:9)
      if (substackPrompt) {
        const dims = aspectToDimensions("16:9");
        const endpoint =
          model === "flux-1.1-pro-ultra"
            ? "/v1/flux-pro-1.1-ultra"
            : model === "flux-1.1-pro"
              ? "/v1/flux-pro-1.1"
              : "/v1/flux-2-pro-preview";

        const params =
          model === "flux-1.1-pro-ultra"
            ? { prompt: substackPrompt, aspect_ratio: "16:9", output_format: "jpeg", safety_tolerance: 2 }
            : { prompt: substackPrompt, width: dims.width, height: dims.height, output_format: "jpeg", safety_tolerance: 2 };

        const submission = await submitGeneration(endpoint, params);
        const result = await pollResult(submission.polling_url);
        const outputPath = join(article_path, "header-substack.jpg");
        const bytes = await downloadImage(result.sample, outputPath);
        results.push(`Substack (16:9): ${outputPath} (${(bytes / 1024).toFixed(0)} KB)`);
      }

      // Generate LinkedIn image (4:5)
      if (linkedinPrompt) {
        const dims = aspectToDimensions("4:5");
        const endpoint =
          model === "flux-1.1-pro-ultra"
            ? "/v1/flux-pro-1.1-ultra"
            : model === "flux-1.1-pro"
              ? "/v1/flux-pro-1.1"
              : "/v1/flux-2-pro-preview";

        const params =
          model === "flux-1.1-pro-ultra"
            ? { prompt: linkedinPrompt, aspect_ratio: "4:5", output_format: "jpeg", safety_tolerance: 2 }
            : { prompt: linkedinPrompt, width: dims.width, height: dims.height, output_format: "jpeg", safety_tolerance: 2 };

        const submission = await submitGeneration(endpoint, params);
        const result = await pollResult(submission.polling_url);
        const outputPath = join(article_path, "header-linkedin.jpg");
        const bytes = await downloadImage(result.sample, outputPath);
        results.push(`LinkedIn (4:5): ${outputPath} (${(bytes / 1024).toFixed(0)} KB)`);
      }

      return {
        content: [
          {
            type: "text",
            text: `Article images generated:\n${results.join("\n")}\n\nModel: ${model}`,
          },
        ],
      };
    } catch (error) {
      return {
        content: [
          {
            type: "text",
            text: `Error generating article images: ${error.message}`,
          },
        ],
        isError: true,
      };
    }
  }
);

// Start server
const transport = new StdioServerTransport();
await server.connect(transport);
