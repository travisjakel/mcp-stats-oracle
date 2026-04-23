# setup.R — install R dependencies for mcp-stats-oracle
# Usage: Rscript setup.R

required <- c(
  "plumber",
  "jsonlite",
  "Rcatch22",
  "ocp",
  "TSrepr",
  "ggplot2",
  "plotcli"
)

installed <- rownames(installed.packages())
to_install <- setdiff(required, installed)

if (length(to_install) > 0) {
  message(sprintf("Installing: %s", paste(to_install, collapse = ", ")))
  install.packages(to_install, repos = "https://cloud.r-project.org")
} else {
  message("All R dependencies already installed.")
}

for (pkg in required) {
  ok <- suppressWarnings(requireNamespace(pkg, quietly = TRUE))
  message(sprintf("  %s %s", if (ok) "[ok]" else "[FAIL]", pkg))
}

message("\nStart the Plumber server with:")
message('  Rscript -e "plumber::pr_run(plumber::pr(\'r_scripts/plumber_server.R\'), port=8787)"')
