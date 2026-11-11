console.error(
  "Refusing a static-only deployment: this checkout has no packaged Python API or index. " +
  "Deploy the full application from clean committed source with " +
  "python -m arxiv_search.serving.export --spec serving/release-v4.json " +
  "--include-paper --include-tracing --output data/serving/<new-release>/web. " +
  "See serving/README.md. The exporter supplies the deployment build configuration."
);
process.exit(1);
