// Optional Style Dictionary build for the canonical token source emitted by
// scripts/synthesize_tokens.py. Run this config from the synthesis output root,
// where tokens/json/ and tokens/dist/ live.
//
// `meta` is a top-level provenance block in every source JSON, so we strip it on
// include (it stays in the source files for downstream consumers, just not in the
// generated token tree). Brands get a single 1.0.0-pre config; bumping the API
// target to Style Dictionary v4 later is a drop-in change.
module.exports = {
  source: ["tokens/json/{color,typography,spacing,radius,shadow}.json"],
  include: [],
  excludeParentKeys: ["meta"],
  platforms: {
    css: {
      transformGroup: "css",
      prefix: "",
      buildPath: "tokens/dist/",
      files: [
        {
          destination: "tokens.style-dictionary.css",
          format: "css/variables",
          options: {
            outputReferences: true,
            selector: ":root",
            showFileHeader: true,
          },
        },
      ],
    },
    json: {
      transformGroup: "js",
      buildPath: "tokens/dist/",
      files: [
        {
          destination: "tokens.style-dictionary.json",
          format: "json/nested",
        },
      ],
    },
  },
};
