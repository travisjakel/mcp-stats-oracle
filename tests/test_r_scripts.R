# tests/test_r_scripts.R — direct R unit tests (no HTTP)
# Usage: Rscript tests/test_r_scripts.R

here <- function(x) file.path("r_scripts", x)
source(here("describe_tool.R"))
source(here("catch22_tool.R"))
source(here("changepoint_tool.R"))
source(here("mrcd_tool.R"))
source(here("mfi_tool.R"))
source(here("tsrepr_tool.R"))
source(here("nowcast_tool.R"))
source(here("plot_tool.R"))

pass <- 0L; fail <- 0L
check <- function(name, cond) {
  if (isTRUE(cond)) { pass <<- pass + 1L; cat(sprintf("  [ok]   %s\n", name)) }
  else              { fail <<- fail + 1L; cat(sprintf("  [FAIL] %s\n", name)) }
}

set.seed(1)
sine <- sin(seq(0, 20, length.out = 200)) + rnorm(200, sd = 0.1)

cat("describe_tool\n")
d <- run_describe(sine)
check("n_finite == 200", d$n_finite == 200)
check("has interpretation", is.character(d$interpretation))

cat("\ncatch22_tool\n")
if (requireNamespace("Rcatch22", quietly = TRUE)) {
  c22 <- run_catch22(sine)
  check("22 features", length(c22$features) == 22)
  check("has interpretation", is.character(c22$interpretation))
} else cat("  [skip] Rcatch22 not installed\n")

cat("\nchangepoint_tool\n")
if (requireNamespace("ocp", quietly = TRUE)) {
  x <- c(rnorm(100), rnorm(100, mean = 5))
  cp <- run_changepoint(x, hazard_rate = 100)
  check("has n_changepoints", !is.null(cp$n_changepoints))
} else cat("  [skip] ocp not installed\n")

cat("\nmrcd_tool\n")
set.seed(42)
x1 <- rnorm(100); x2 <- rnorm(100)
y <- 2 * x1 + 3 * x2 + rnorm(100, sd = 0.5); y[50] <- 100
m <- run_mrcd(data.frame(y = y, x1 = x1, x2 = x2), target = "y", predictors = c("x1", "x2"))
check("index 50 flagged", m$outlier_flags[50] == 1)

cat("\nmfi_tool\n")
set.seed(0)
close <- 100 + rnorm(50, sd = 2)
high <- close + abs(rnorm(50)); low <- close - abs(rnorm(50))
volume <- 1e6 + rnorm(50, sd = 1e5)
mfi <- run_mfi(high, low, close, volume, window = 14)
check("latest in [0,100]", !is.na(mfi$latest) && mfi$latest >= 0 && mfi$latest <= 100)

cat("\ntsrepr_tool\n")
t <- run_tsrepr(rep(c(1,2,3,4,5,4,3,2,1), 3))
check("8 features", length(t$features) == 8)

cat("\nnowcast_tool\n")
nc <- run_nowcast(
  historical = c(100, 105, 110, 102, 108, 111, 104, 106),
  signals = list(
    google_trends = list(value = 115, weight = 0.4),
    web_signal = list(value = 112, weight = 0.3)
  ),
  day_of_quarter = 45
)
check("ci_95 length 2", length(nc$ci_95) == 2)
check("n_signals == 2", nc$n_signals == 2)

cat("\nplot_tool\n")
if (requireNamespace("plotcli", quietly = TRUE) && requireNamespace("ggplot2", quietly = TRUE)) {
  pl <- run_plot(plot_type = "line", data = cumsum(rnorm(60)), title = "test")
  check("line plot returns text",
        is.character(pl$plot) && nchar(pl$plot) > 100)
  ph <- run_plot(plot_type = "histogram", data = rnorm(300), bins = 25)
  check("histogram plot returns text", nchar(ph$plot) > 100)
  ps <- run_plot(plot_type = "scatter", x = rnorm(50), y = rnorm(50))
  check("scatter plot returns text", nchar(ps$plot) > 100)
} else cat("  [skip] plotcli or ggplot2 not installed\n")

cat(sprintf("\n%d passed, %d failed\n", pass, fail))
if (fail > 0) quit(status = 1)
