#' Describe numeric series
#'
#' Lightweight peek at a series before running heavier analysis tools.
#' Lets the agent decide whether a tool call is worthwhile (e.g. skip
#' catch22 if the series is 90% NA).
#'
#' @param data numeric vector
#' @return list with summary stats + interpretation

run_describe <- function(data) {
  x <- suppressWarnings(as.numeric(data))
  n_total <- length(x)
  finite <- x[is.finite(x)]
  n <- length(finite)
  n_na <- n_total - n

  if (n == 0) {
    return(list(n_total = n_total, n_finite = 0, error = "No finite data"))
  }

  qs <- stats::quantile(finite, c(0, 0.25, 0.5, 0.75, 1), na.rm = TRUE)
  m <- mean(finite); s <- stats::sd(finite)
  skew <- if (s > 0) mean(((finite - m) / s)^3) else 0

  interpretation <- sprintf(
    "N=%d (%.1f%% finite), mean=%.3f, sd=%.3f, range=[%.3f, %.3f]%s%s.",
    n_total, 100 * n / n_total, m, s, qs[1], qs[5],
    if (abs(skew) > 1) sprintf(", skew=%.2f (highly skewed)", skew) else "",
    if (n_na / n_total > 0.2) sprintf(", WARNING: %.0f%% missing", 100 * n_na / n_total) else ""
  )

  list(
    n_total = n_total,
    n_finite = n,
    n_na = n_na,
    mean = m,
    sd = s,
    min = qs[[1]],
    q25 = qs[[2]],
    median = qs[[3]],
    q75 = qs[[4]],
    max = qs[[5]],
    skewness = skew,
    interpretation = interpretation
  )
}
